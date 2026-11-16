"""Wake word architecture.

`WakeWordDetector` is the interface. The default implementation matches the wake word in
Whisper transcripts (robust to common mis-hearings of "Volb"). A dedicated always-on audio
model (e.g. openWakeWord) can be dropped in later by implementing `detect_audio`.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod

import numpy as np

VARIANTS = ["volb", "volp", "wolb", "volbe", "volbi", "vol b", "vold", "volv", "wolf", "bolb", "volup", "vulb"]


class WakeWordDetector(ABC):
    @abstractmethod
    def detect_text(self, transcript: str) -> tuple[bool, str]:
        """Return (detected, command_after_wake_word)."""

    def detect_audio(self, audio: np.ndarray) -> bool:  # noqa: ARG002
        """Optional fast audio-level detector. Default: unsupported → rely on transcript."""
        return True


class TranscriptWakeWord(WakeWordDetector):
    def __init__(self, wake_word: str = "volb", extra_variants: list[str] | None = None) -> None:
        words = {wake_word.lower(), *VARIANTS, *(extra_variants or [])}
        alt = "|".join(sorted((re.escape(w) for w in words), key=len, reverse=True))
        self._re = re.compile(rf"^\W*(?:hey\s+|selam\s+)?(?:{alt})\b[\s,.:!?-]*", re.IGNORECASE)

    def detect_text(self, transcript: str) -> tuple[bool, str]:
        m = self._re.match(transcript.strip())
        if not m:
            return False, transcript
        return True, transcript.strip()[m.end():].strip()
