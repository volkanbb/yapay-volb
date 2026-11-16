"""Application configuration.

Precedence (lowest → highest): defaults < .env / environment < values stored in SQLite.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("VOLB_DATA_DIR") or ROOT_DIR / "data")
LOG_DIR = ROOT_DIR / "logs"
MODELS_DIR = ROOT_DIR / "models"
UI_DIR = ROOT_DIR / "ui"

APP_NAME = "YAPAY VOLB"
APP_VERSION = "0.1.0"


class Settings(BaseModel):
    """User-adjustable settings. Every field here is editable from the Settings page."""

    language: str = Field("tr", description="Primary language: tr | en")
    wake_word: str = "volb"
    ai_provider: str = Field("claude_cli", description="claude_cli | ollama | anthropic_api")
    claude_model: str = Field("", description="Optional Claude Code model alias (empty = CLI default)")
    ollama_model: str = "llama3.1"
    allow_paid_api: bool = Field(False, description="Must be explicitly enabled to use the paid Anthropic API")

    stt_model: str = "small"
    stt_device: str = Field("auto", description="auto | cuda | cpu")
    tts_engine: str = Field("piper", description="piper | edge | none")
    piper_voice: str = "tr_TR-dfki-medium"
    edge_voice: str = "tr-TR-AhmetNeural"
    allow_edge_tts: bool = Field(False, description="Edge TTS sends text to Microsoft servers")
    mic_device: int = Field(-1, description="-1 = system default")
    continuous_listening: bool = False
    speak_responses: bool = True

    sleep_inhibit: str = Field("always", pattern="^(off|always|schedules)$", description="off | always (VOLB açıkken) | schedules (yaklaşan görev varken)")
    semantic_memory: bool = False
    browser_headless: bool = False
    search_engine: str = "duckduckgo"

    def public_dict(self) -> dict[str, Any]:
        return self.model_dump()


_ENV_MAP = {
    "VOLB_LANGUAGE": "language",
    "VOLB_WAKE_WORD": "wake_word",
    "VOLB_AI_PROVIDER": "ai_provider",
    "VOLB_CLAUDE_MODEL": "claude_model",
    "VOLB_OLLAMA_MODEL": "ollama_model",
    "VOLB_STT_MODEL": "stt_model",
    "VOLB_STT_DEVICE": "stt_device",
    "VOLB_TTS_ENGINE": "tts_engine",
    "VOLB_PIPER_VOICE": "piper_voice",
    "VOLB_EDGE_VOICE": "edge_voice",
    "VOLB_ALLOW_EDGE_TTS": "allow_edge_tts",
    "VOLB_BROWSER_HEADLESS": "browser_headless",
    "VOLB_SEMANTIC_MEMORY": "semantic_memory",
    "VOLB_SLEEP_INHIBIT": "sleep_inhibit",
}


def load_dotenv(path: Path | None = None) -> dict[str, str]:
    """Tiny .env parser (no external dependency). Does not override real env vars."""
    path = path or ROOT_DIR / ".env"
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def load_settings(stored: dict[str, Any] | None = None) -> Settings:
    data: dict[str, Any] = {}
    env = {**load_dotenv(), **os.environ}
    for env_key, field in _ENV_MAP.items():
        if env_key in env:
            data[field] = env[env_key]
    if stored:
        data.update({k: v for k, v in stored.items() if k in Settings.model_fields})
    return Settings.model_validate(data)


def ensure_dirs() -> None:
    for d in (DATA_DIR, LOG_DIR, MODELS_DIR):
        d.mkdir(parents=True, exist_ok=True)
