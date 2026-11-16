"""Paid Anthropic API provider — disabled unless the user explicitly opts in.

Claude Pro does NOT include API credits; this provider bills a separate API account.
It is never selected automatically and never used as a fallback.
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator

from .base import AIProvider, ChatChunk, ProviderStatus

DEFAULT_MODEL = "claude-opus-5-5"


class AnthropicAPIProvider(AIProvider):
    name = "anthropic_api"
    display_name = "Anthropic API (ücretli)"
    is_paid_api = True

    def __init__(self, allowed: bool, model: str = DEFAULT_MODEL) -> None:
        self.allowed = allowed
        self.model = model
        self._history: list[dict] = []

    async def status(self) -> ProviderStatus:
        if not self.allowed:
            return ProviderStatus(self.name, False, False, "Ücretli API kapalı (Ayarlar → allow_paid_api).")
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return ProviderStatus(self.name, False, False, "pip install anthropic gerekli.")
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return ProviderStatus(self.name, True, False, "ANTHROPIC_API_KEY ortam değişkeni yok.")
        return ProviderStatus(self.name, True, True, f"Hazır • {self.model}")

    def reset_conversation(self) -> None:
        self._history.clear()

    async def stream(self, prompt: str, system: str | None = None) -> AsyncIterator[ChatChunk]:
        st = await self.status()
        if not st.ready:
            yield ChatChunk("error", st.detail)
            return
        import anthropic

        client = anthropic.AsyncAnthropic()
        messages = self._history + [{"role": "user", "content": prompt}]
        parts: list[str] = []
        try:
            async with client.messages.stream(model=self.model, max_tokens=4096, system=system or "",
                                              messages=messages) as s:
                async for text in s.text_stream:
                    parts.append(text)
                    yield ChatChunk("text", text)
        except anthropic.RateLimitError as exc:
            yield ChatChunk("limit", str(exc))
            return
        except anthropic.APIError as exc:
            yield ChatChunk("error", str(exc))
            return
        self._history = (messages + [{"role": "assistant", "content": "".join(parts)}])[-20:]
        yield ChatChunk("done")
