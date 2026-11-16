"""ClaudeCodeCLIProvider against a fake `claude` executable speaking the documented stream-json format."""
import json
import os
import stat
import textwrap

import pytest

from app.ai.claude_cli import ClaudeCodeCLIProvider, classify_error

FAKE = textwrap.dedent('''\
    #!/usr/bin/env python3
    import json, os, sys
    args = sys.argv[1:]
    mode = os.environ.get("FAKE_MODE", "ok")
    if args[:1] == ["--version"]:
        print("9.9.9 (Claude Code)"); sys.exit(0)
    if args[:2] == ["auth", "status"]:
        print(json.dumps({"loggedIn": mode != "logged_out", "authMethod": "apiKey" if mode == "apikey" else "claude.ai",
                          "subscriptionType": "pro"})); sys.exit(0)
    prompt = sys.stdin.read()
    def emit(o): print(json.dumps(o), flush=True)
    emit({"type": "system", "subtype": "init", "session_id": "sess-123"})
    if mode == "limit":
        emit({"type": "result", "subtype": "error", "is_error": True, "result": "Claude usage limit reached", "session_id": "sess-123"})
        sys.exit(1)
    info = {"args": args, "api_key_seen": "ANTHROPIC_API_KEY" in os.environ, "prompt": prompt}
    for piece in ["Merhaba", ", ", json.dumps(info)]:
        emit({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": piece}}})
    emit({"type": "assistant", "message": {"content": [{"type": "text", "text": "IGNORED-DUPLICATE"}]}})
    emit({"type": "rate_limit_event", "rate_limit_info": {"status": "allowed_warning", "resetsAt": 1793918400,
          "rateLimitType": "five_hour", "utilization": 0.82, "overageStatus": "rejected", "isUsingOverage": False}})
    emit({"type": "result", "subtype": "success", "is_error": False, "result": "x", "session_id": "sess-123",
          "total_cost_usd": 0.05, "duration_ms": 1200,
          "modelUsage": {"claude-sonnet-5": {"inputTokens": 3, "outputTokens": 40, "cacheReadInputTokens": 3000,
                                             "cacheCreationInputTokens": 500, "costUSD": 0.049},
                         "claude-haiku-4-5": {"inputTokens": 500, "outputTokens": 10, "costUSD": 0.001}}})
''')


@pytest.fixture()
def fake_claude(tmp_path):
    exe = tmp_path / "claude"
    exe.write_text(FAKE)
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    return str(exe)


async def test_status_ok(fake_claude, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "ok")
    st = await ClaudeCodeCLIProvider(executable=fake_claude).status()
    assert st.ready and st.version == "9.9.9"


async def test_status_logged_out(fake_claude, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "logged_out")
    st = await ClaudeCodeCLIProvider(executable=fake_claude).status()
    assert st.available and not st.authenticated and "login" in st.install_hint


async def test_status_api_key_refused(fake_claude, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "apikey")
    st = await ClaudeCodeCLIProvider(executable=fake_claude).status()
    assert not st.ready and "ücretli" in st.detail.lower()


async def test_missing_cli(monkeypatch):
    p = ClaudeCodeCLIProvider(executable=None)
    p.executable = None
    st = await p.status()
    assert not st.available and "install" in st.install_hint


async def test_stream_and_resume(fake_claude, monkeypatch, tmp_path):
    monkeypatch.setenv("FAKE_MODE", "ok")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-not-leak")
    p = ClaudeCodeCLIProvider(executable=fake_claude, workdir=tmp_path)
    text = await p.complete("selam", system="sen volb'sun")
    assert text.startswith("Merhaba, ")
    info = json.loads(text[len("Merhaba, "):])
    assert info["api_key_seen"] is False          # paid API key stripped from env
    assert info["prompt"] == "selam"              # prompt via stdin
    assert "--tools" in info["args"] and info["args"][info["args"].index("--tools") + 1] == ""
    assert "IGNORED-DUPLICATE" not in text        # partial deltas win over the final message
    assert p.session_id == "sess-123"
    text2 = await p.complete("devam")
    info2 = json.loads(text2[len("Merhaba, "):])
    assert info2["args"][info2["args"].index("--resume") + 1] == "sess-123"


async def test_limit(fake_claude, monkeypatch, tmp_path):
    monkeypatch.setenv("FAKE_MODE", "limit")
    p = ClaudeCodeCLIProvider(executable=fake_claude, workdir=tmp_path)
    kinds = [c.kind async for c in p.stream("x")]
    assert kinds[-1] == "limit"


def test_classify():
    assert classify_error("You've hit your usage limit") == "limit"
    assert classify_error("Not logged in · Please run /login") == "auth"
    assert classify_error("boom") == "error"


def test_safe_env_strips_host_session(monkeypatch):
    from app.ai.claude_cli import safe_env
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://proxy")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-x")
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_SCOPES", "user")
    monkeypatch.setenv("HOME_TEST_KEEP", "1")
    env = safe_env()
    assert not any(k.startswith(("ANTHROPIC_", "CLAUDE_CODE_")) or k == "CLAUDECODE" for k in env)
    assert env["HOME_TEST_KEEP"] == "1"


async def test_usage_and_limits_reported(fake_claude, monkeypatch, tmp_path):
    from app.ai.base import usage_purpose
    from app.memory.database import Database
    monkeypatch.setenv("FAKE_MODE", "ok")
    db = Database(tmp_path / "u.db")
    p = ClaudeCodeCLIProvider(executable=fake_claude, workdir=tmp_path)
    p.usage_sink, p.limit_sink = db.log_usage, db.save_rate_limit
    usage_purpose.set("araştırma")
    await p.complete("selam")
    limits = db.rate_limits()
    assert limits[0]["rateLimitType"] == "five_hour" and limits[0]["status"] == "allowed_warning"
    s = db.usage_summary()
    assert s["all"]["calls"] == 1
    assert s["all"]["output"] == 50 and s["all"]["cache_read"] == 3000
    assert s["all"]["total"] == 3 + 40 + 3000 + 500 + 500 + 10
    assert abs(s["all"]["cost"] - 0.05) < 1e-9
    assert s["byPurpose"][0]["purpose"] == "araştırma"
    assert {m["model"] for m in s["byModel"]} == {"claude-sonnet-5", "claude-haiku-4-5"}
    assert s["daily"][-1]["total"] == s["all"]["total"]


async def test_probe_limits_keeps_conversation(fake_claude, monkeypatch, tmp_path):
    monkeypatch.setenv("FAKE_MODE", "ok")
    p = ClaudeCodeCLIProvider(executable=fake_claude, workdir=tmp_path, model="opus")
    p.session_id = "my-chat"
    seen = []
    p.usage_sink = seen.append
    text = await p.probe_limits()
    args = json.loads(text[len("Merhaba, "):])["args"]
    assert "--no-session-persistence" in args and args[args.index("--model") + 1] == "haiku"
    assert "--resume" not in args
    assert p.session_id == "my-chat" and p.model == "opus"
    assert seen[0]["purpose"] == "limit kontrolü"


async def test_parallel_oneshot_does_not_touch_chat_session(fake_claude, monkeypatch, tmp_path):
    import asyncio
    monkeypatch.setenv("FAKE_MODE", "ok")
    p = ClaudeCodeCLIProvider(executable=fake_claude, workdir=tmp_path)
    p.session_id = "chat-1"
    chat, agent = await asyncio.gather(p.complete("sohbet"), p.oneshot("ajan adımı"))
    chat_args = json.loads(chat[len("Merhaba, "):])["args"]
    agent_args = json.loads(agent[len("Merhaba, "):])["args"]
    assert chat_args[chat_args.index("--resume") + 1] == "chat-1"
    assert "--resume" not in agent_args and "--no-session-persistence" in agent_args
    assert "--no-session-persistence" not in chat_args
    assert p.session_id == "sess-123"       # only the chat call updated the session
