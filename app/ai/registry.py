from __future__ import annotations

from ..core.config import Settings
from .anthropic_api import AnthropicAPIProvider
from .base import AIProvider
from .claude_cli import ClaudeCodeCLIProvider
from .ollama import OllamaProvider


def create_provider(settings: Settings) -> AIProvider:
    """Create exactly the provider the user selected. There is deliberately no automatic fallback,
    so VOLB can never silently switch from the Pro subscription to paid API usage."""
    match settings.ai_provider:
        case "ollama":
            return OllamaProvider(settings.ollama_model)
        case "anthropic_api":
            return AnthropicAPIProvider(allowed=settings.allow_paid_api)
        case _:
            return ClaudeCodeCLIProvider(model=settings.claude_model)
