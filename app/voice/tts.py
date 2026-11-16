"""Text-to-speech engines: Piper (local, default) and Edge TTS (optional, online)."""
from __future__ import annotations

import asyncio
import logging
import re
import shutil
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

from ..core.config import MODELS_DIR

log = logging.getLogger(__name__)


def clean_for_speech(text: str) -> str:
    text = re.sub(r"```.*?```", " kod bloğu ", text, flags=re.S)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[(\d+)\]", "", text)
    text = re.sub(r"https?://\S+", "bağlantı", text)
    text = re.sub(r"[*_#>|]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


class TTSEngine(ABC):
    name = "none"

    @abstractmethod
    async def synthesize(self, text: str) -> tuple[np.ndarray, int]: ...

    def available(self) -> tuple[bool, str]:
        return True, ""


class NullTTS(TTSEngine):
    name = "none"

    async def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        return np.zeros(0, np.float32), 22050


class PiperTTS(TTSEngine):
    name = "piper"

    def __init__(self, voice: str = "tr_TR-dfki-medium", models_dir: Path = MODELS_DIR) -> None:
        self.voice_name = voice
        self.model_path = models_dir / "piper" / f"{voice}.onnx"
        self._voice = None

    def available(self) -> tuple[bool, str]:
        try:
            import piper  # noqa: F401
        except ImportError:
            return False, "piper-tts kurulu değil"
        if not self.model_path.exists():
            return False, f"Piper ses modeli yok: python scripts/download_models.py --piper {self.voice_name}"
        return True, ""

    def _load(self):
        if self._voice is None:
            from piper import PiperVoice
            self._voice = PiperVoice.load(str(self.model_path))
        return self._voice

    def _synth_sync(self, text: str) -> tuple[np.ndarray, int]:
        voice = self._load()
        chunks, sr = [], voice.config.sample_rate
        for chunk in voice.synthesize(text):
            arr = getattr(chunk, "audio_float_array", None)
            if arr is None:
                arr = chunk.audio_int16_array.astype(np.float32) / 32768.0
            chunks.append(arr)
            sr = chunk.sample_rate
        return (np.concatenate(chunks) if chunks else np.zeros(0, np.float32)), sr

    async def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        return await asyncio.to_thread(self._synth_sync, text)


class EdgeTTS(TTSEngine):
    """Microsoft Edge online voices. Sends the text to Microsoft — only used when explicitly allowed."""

    name = "edge"

    def __init__(self, voice: str = "tr-TR-AhmetNeural") -> None:
        self.voice = voice

    def available(self) -> tuple[bool, str]:
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            return False, "edge-tts kurulu değil"
        if not shutil.which("ffmpeg"):
            return False, "ffmpeg gerekli"
        return True, ""

    async def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        import edge_tts

        sr = 24000
        with tempfile.TemporaryDirectory() as tmp:
            mp3 = Path(tmp) / "out.mp3"
            await edge_tts.Communicate(text, self.voice).save(str(mp3))
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-loglevel", "error", "-i", str(mp3), "-f", "f32le", "-ac", "1", "-ar", str(sr), "-",
                stdout=asyncio.subprocess.PIPE)
            raw, _ = await proc.communicate()
        return np.frombuffer(raw, dtype=np.float32).copy(), sr


def create_tts(engine: str, piper_voice: str, edge_voice: str, allow_edge: bool) -> TTSEngine:
    if engine == "piper":
        piper = PiperTTS(piper_voice)
        ok, why = piper.available()
        if ok:
            return piper
        log.warning("Piper unavailable: %s", why)
        if allow_edge:
            return EdgeTTS(edge_voice)
        return NullTTS()
    if engine == "edge" and allow_edge:
        return EdgeTTS(edge_voice)
    return NullTTS()
