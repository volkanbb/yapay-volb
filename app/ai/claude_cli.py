"""Claude Code CLI provider — uses the user's own Claude Pro/Max subscription.

Only the documented, non-interactive CLI interface is used:

    claude -p --output-format stream-json --verbose --include-partial-messages ...

Security / billing guarantees:
* No passwords are handled and no auth tokens are read — the CLI manages its own login.
* ANTHROPIC_API_KEY and similar variables are *removed* from the child environment so the
  CLI cannot silently fall back to pay-per-use API billing.
* If `claude auth status` reports API-key authentication, the provider refuses to run.
* All Claude Code tools are disabled (`--tools ""`): VOLB executes actions itself through
  its allowlisted action system, never through model-generated shell commands.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from ..core.config import DATA_DIR
from .base import AIProvider, ChatChunk, ProviderStatus, usage_purpose

log = logging.getLogger(__name__)

INSTALL_HINT = (
    "Claude Code CLI bulunamadı. Kurulum:\n"
    "  curl -fsSL https://claude.ai/install.sh | bash\n"
    "veya: npm install -g @anthropic-ai/claude-code\n"
    "Ardından terminalde `claude auth login` ile Claude Pro hesabınla giriş yap."
)
LOGIN_HINT = "Terminalde `claude auth login` çalıştırıp Claude Pro hesabınla giriş yap, sonra 'Yenile'ye bas."

# Environment variables that would make the CLI bill a paid API account instead of the subscription.
_BLOCKED_ENV = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDECODE",  # avoid nested-session detection when VOLB itself is launched from Claude Code
    "CLAUDE_CODE_ENTRYPOINT",
)

_LIMIT_MARKERS = ("usage limit", "rate limit", "limit reached", "rate_limit", "overloaded", "429")
_AUTH_MARKERS = ("not logged in", "please run /login", "invalid api key", "authentication", "oauth", "401")


def find_claude_executable() -> str | None:
    found = shutil.which("claude")
    if found:
        return found
    for candidate in (
        Path.home() / ".local/bin/claude",
        Path.home() / ".claude/local/claude",
        Path.home() / ".npm-global/bin/claude",
        Path("/usr/local/bin/claude"),
    ):
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def safe_env() -> dict[str, str]:
    """Child environment for the CLI: the user's own login only.

    * every ANTHROPIC_* variable is removed (API keys, auth tokens, custom base URLs/proxies);
    * if VOLB itself was started from inside a Claude Code / Claude desktop session, that host
      session's CLAUDE_* variables are removed too, so requests can't ride on the host session."""
    env = os.environ.copy()
    nested = "CLAUDECODE" in env or "CLAUDE_CODE_SESSION_ID" in env
    for key in list(env):
        if key in _BLOCKED_ENV or key.startswith("ANTHROPIC_"):
            env.pop(key)
        elif nested and key.startswith(("CLAUDE_CODE_", "CLAUDE_AGENT_SDK", "CLAUDE_PID", "CLAUDE_EFFORT",
                                         "CLAUDE_PREVIEW")):
            env.pop(key)
    return env


@dataclass(frozen=True)
class _Call:
    """Per-request options. Kept off `self` so parallel requests (chat + app agent) can't affect each other."""
    model: str = ""
    resume: str | None = None
    isolated: bool = False      # stand-alone request: no --resume, not persisted, doesn't touch the chat session
    purpose: str | None = None


def classify_error(text: str) -> str:
    low = text.lower()
    if any(m in low for m in _LIMIT_MARKERS):
        return "limit"
    if any(m in low for m in _AUTH_MARKERS):
        return "auth"
    return "error"


class ClaudeCodeCLIProvider(AIProvider):
    name = "claude_cli"
    display_name = "Claude Code (Pro)"
    is_paid_api = False

    def __init__(self, executable: str | None = None, model: str = "", timeout: float = 600.0,
                 workdir: Path | None = None) -> None:
        self.executable = executable or find_claude_executable()
        self.model = model
        self.timeout = timeout
        self.workdir = workdir or DATA_DIR / "claude_workspace"
        self.session_id: str | None = None
        self._procs: set[asyncio.subprocess.Process] = set()

    # ------------------------------------------------------------------ status
    async def _run_simple(self, *args: str, timeout: float = 20.0) -> tuple[int, str, str]:
        assert self.executable
        proc = await asyncio.create_subprocess_exec(
            self.executable, *args,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL, env=safe_env(),
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout)
        except TimeoutError:
            proc.kill()
            return -1, "", "timeout"
        return proc.returncode or 0, out.decode(errors="replace"), err.decode(errors="replace")

    async def status(self) -> ProviderStatus:
        if not self.executable:
            return ProviderStatus(self.name, False, False, "Claude Code CLI kurulu değil.", install_hint=INSTALL_HINT)
        code, out, err = await self._run_simple("--version")
        version = out.strip().split(" ")[0] if code == 0 else None
        if code != 0:
            return ProviderStatus(self.name, False, False, f"CLI çalıştırılamadı: {err.strip()[:200]}",
                                  install_hint=INSTALL_HINT)
        code, out, err = await self._run_simple("auth", "status")
        try:
            info = json.loads(out)
        except json.JSONDecodeError:
            info = {}
        logged_in = bool(info.get("loggedIn"))
        method = str(info.get("authMethod", "")).lower()
        if not logged_in:
            return ProviderStatus(self.name, True, False, "Claude hesabına giriş yapılmamış.", version=version,
                                  install_hint=LOGIN_HINT, extra=info)
        if "api" in method and "key" in method:
            return ProviderStatus(
                self.name, True, False,
                "CLI API anahtarıyla giriş yapmış. Ücretli API kullanımı engellendi — Pro aboneliğinle giriş yap.",
                version=version, install_hint=LOGIN_HINT, extra=info)
        sub = info.get("subscriptionType") or info.get("subscription") or ""
        detail = f"Bağlı • {method or 'oauth'}" + (f" • {sub}" if sub else "")
        return ProviderStatus(self.name, True, True, detail, version=version, extra=info)

    # ------------------------------------------------------------------ chat
    def build_command(self, system: str | None, call: _Call | None = None) -> list[str]:
        call = call or _Call(self.model, self.session_id)
        assert self.executable
        cmd = [
            self.executable, "-p",
            "--output-format", "stream-json",
            "--verbose",
            "--include-partial-messages",
            "--tools", "",
        ]
        if system:
            cmd += ["--system-prompt", system]
        if call.model:
            cmd += ["--model", call.model]
        if call.resume and not call.isolated:
            cmd += ["--resume", call.resume]
        if call.isolated:
            cmd += ["--no-session-persistence"]
        return cmd

    def reset_conversation(self) -> None:
        self.session_id = None

    def stream(self, prompt: str, system: str | None = None) -> AsyncIterator[ChatChunk]:
        return self._stream(prompt, system, _Call(self.model, self.session_id))

    async def _stream(self, prompt: str, system: str | None, call: _Call) -> AsyncIterator[ChatChunk]:
        if not self.executable:
            yield ChatChunk("error", INSTALL_HINT)
            return
        self.workdir.mkdir(parents=True, exist_ok=True)
        cmd = self.build_command(system, call)
        log.info("claude cli: %s", " ".join(a if len(a) < 60 else a[:57] + "..." for a in cmd))
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE, env=safe_env(), cwd=str(self.workdir),
                limit=8 * 1024 * 1024,
            )
        except OSError as exc:
            yield ChatChunk("error", f"Claude CLI başlatılamadı: {exc}")
            return

        self._procs.add(proc)
        assert proc.stdin and proc.stdout and proc.stderr
        proc.stdin.write(prompt.encode("utf-8"))
        await proc.stdin.drain()
        proc.stdin.close()

        saw_partial = False
        terminal: ChatChunk | None = None
        stderr_task = asyncio.create_task(proc.stderr.read())
        try:
            while True:
                try:
                    line = await asyncio.wait_for(proc.stdout.readline(), self.timeout)
                except TimeoutError:
                    proc.kill()
                    terminal = ChatChunk("error", "Claude yanıt vermedi (zaman aşımı).")
                    break
                if not line:
                    break
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for chunk in self._handle_event(event, saw_partial, call):
                    if chunk.kind == "text":
                        if chunk.meta.get("partial"):
                            saw_partial = True
                        yield chunk
                    else:
                        terminal = chunk
        except asyncio.CancelledError:
            proc.kill()
            raise
        finally:
            rc = await proc.wait()
            err = (await stderr_task).decode(errors="replace").strip()
            self._procs.discard(proc)

        if terminal is None:
            if rc != 0:
                kind = classify_error(err)
                msg = {"limit": "Claude kullanım limitine ulaşıldı. Biraz sonra tekrar dene.",
                       "auth": "Claude oturumu yok. " + LOGIN_HINT}.get(kind, f"Claude CLI hata verdi: {err[:300]}")
                terminal = ChatChunk(kind, msg)  # type: ignore[arg-type]
            else:
                terminal = ChatChunk("done")
        yield terminal

    def _handle_event(self, event: dict, saw_partial: bool, call: _Call | None = None) -> list[ChatChunk]:
        call = call or _Call()
        etype = event.get("type")
        if event.get("session_id") and not call.isolated:
            self.session_id = event["session_id"]
        if etype == "rate_limit_event":
            info = dict(event.get("rate_limit_info") or {})
            if info and self.limit_sink:
                self.limit_sink(info)
            return []
        if etype == "result":
            self._report_usage(event, call)
        if etype == "stream_event":
            ev = event.get("event", {})
            if ev.get("type") == "content_block_delta":
                delta = ev.get("delta", {})
                if delta.get("type") == "text_delta" and delta.get("text"):
                    return [ChatChunk("text", delta["text"], {"partial": True})]
            return []
        if etype == "assistant" and not saw_partial:
            content = event.get("message", {}).get("content", [])
            text = "".join(c.get("text", "") for c in content if c.get("type") == "text")
            return [ChatChunk("text", text)] if text else []
        if etype == "result":
            if event.get("is_error") or event.get("subtype", "success") != "success":
                msg = str(event.get("result") or event.get("error") or event.get("subtype"))
                kind = classify_error(msg)
                if kind == "auth" and not call.isolated:
                    self.session_id = None
                    return [ChatChunk("auth", "Claude oturumu yok. " + LOGIN_HINT)]
                if kind == "limit":
                    return [ChatChunk("limit", "Claude Pro kullanım limitine ulaşıldı: " + msg[:200])]
                return [ChatChunk("error", msg[:500])]
            return [ChatChunk("done", meta={
                "duration_ms": event.get("duration_ms"),
                "session_id": event.get("session_id"),
                "num_turns": event.get("num_turns"),
            })]
        return []

    def _report_usage(self, event: dict, call: _Call) -> None:
        if not self.usage_sink:
            return
        models: dict[str, dict] = {}
        for name, mu in (event.get("modelUsage") or {}).items():
            models[name] = {
                "input": int(mu.get("inputTokens", 0)), "output": int(mu.get("outputTokens", 0)),
                "cache_read": int(mu.get("cacheReadInputTokens", 0)),
                "cache_write": int(mu.get("cacheCreationInputTokens", 0)), "cost": float(mu.get("costUSD", 0.0)),
            }
        if not models and event.get("usage"):
            u = event["usage"]
            models["?"] = {"input": int(u.get("input_tokens", 0)), "output": int(u.get("output_tokens", 0)),
                           "cache_read": int(u.get("cache_read_input_tokens", 0)),
                           "cache_write": int(u.get("cache_creation_input_tokens", 0)),
                           "cost": float(event.get("total_cost_usd") or 0.0)}
        self.usage_sink({
            "provider": self.name,
            "purpose": call.purpose or usage_purpose.get(),
            "models": models,
            "cost_usd": float(event.get("total_cost_usd") or sum(m["cost"] for m in models.values())),
            "duration_ms": int(event.get("duration_ms") or 0),
            "is_error": bool(event.get("is_error")),
        })

    async def oneshot(self, prompt: str, system: str | None = None, model: str | None = None,
                      purpose: str | None = None) -> str:
        """Independent request (research, document summary, app control): no --resume, not persisted,
        and the chat session is left untouched — safe to run in parallel with a chat."""
        parts: list[str] = []
        async for chunk in self._stream(prompt, system, _Call(model or self.model, None, True, purpose)):
            if chunk.kind == "text":
                parts.append(chunk.text)
            elif chunk.kind in ("error", "limit", "auth"):
                from .base import AIProviderError
                raise AIProviderError(chunk.text)
        return "".join(parts)

    async def probe_limits(self) -> str:
        """Send one tiny Haiku request so the CLI reports the current subscription rate-limit status.
        Uses a little of the user's quota, so it only runs when the user asks for it."""
        return await self.oneshot("ok", system="Reply with exactly: ok", model="haiku", purpose="limit kontrolü")

    async def cancel(self) -> None:
        for proc in list(self._procs):
            if proc.returncode is None:
                proc.terminate()
