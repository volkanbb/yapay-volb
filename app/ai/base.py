"""Provider-agnostic AI interface."""
from __future__ import annotations

import contextvars
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

ChunkKind = Literal["text", "done", "error", "limit", "auth"]


@dataclass
class ProviderStatus:
    name: str
    available: bool  # binary / service present
    authenticated: bool  # ready to answer
    detail: str = ""
    version: str | None = None
    install_hint: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        return self.available and self.authenticated


@dataclass
class ChatChunk:
    kind: ChunkKind
    text: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


# What the current AI call is for ("sohbet", "araştırma", "belge", …) — recorded with token usage.
usage_purpose: contextvars.ContextVar[str] = contextvars.ContextVar("usage_purpose", default="sohbet")


class AIProviderError(RuntimeError):
    pass


class AIProvider(ABC):
    """Every AI backend implements this. The orchestrator only talks to this interface."""

    name: str = "base"
    display_name: str = "Base"
    is_paid_api: bool = False  # True → must never be used without explicit user opt-in
    usage_sink: Callable[[dict[str, Any]], None] | None = None   # called with one record per AI call
    limit_sink: Callable[[dict[str, Any]], None] | None = None   # called with subscription rate-limit info

    @abstractmethod
    async def status(self) -> ProviderStatus: ...

    @abstractmethod
    def stream(self, prompt: str, system: str | None = None) -> AsyncIterator[ChatChunk]:
        """Yield text chunks, then exactly one terminal chunk (done/error/limit/auth)."""

    async def complete(self, prompt: str, system: str | None = None) -> str:
        parts: list[str] = []
        async for chunk in self.stream(prompt, system):
            if chunk.kind == "text":
                parts.append(chunk.text)
            elif chunk.kind in ("error", "limit", "auth"):
                raise AIProviderError(chunk.text)
        return "".join(parts)

    async def oneshot(self, prompt: str, system: str | None = None, model: str | None = None) -> str:
        """A stand-alone request that must not join or change the chat conversation."""
        return await self.complete(prompt, system)

    async def cancel(self) -> None:  # pragma: no cover - default no-op
        return None

    def reset_conversation(self) -> None:
        return None
