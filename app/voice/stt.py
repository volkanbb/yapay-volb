"""Faster-Whisper speech recognition (Turkish + English, auto language detection)."""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

import numpy as np

log = logging.getLogger(__name__)


def preload_cuda_libs() -> None:
    """If the optional `nvidia-cublas-cu12` / `nvidia-cudnn-cu12` wheels are installed, load their
    shared libraries so CTranslate2 can run Whisper on the GPU without touching LD_LIBRARY_PATH."""
    import ctypes
    import glob
    import os

    try:
        import nvidia  # namespace package from the wheels
    except ImportError:
        return
    for base in getattr(nvidia, "__path__", []):
        for pattern in ("cublas/lib/libcublasLt.so.*", "cublas/lib/libcublas.so.*", "cudnn/lib/libcudnn*.so.*"):
            for lib in sorted(glob.glob(os.path.join(base, pattern))):
                try:
                    ctypes.CDLL(lib, mode=ctypes.RTLD_GLOBAL)
                except OSError:
                    pass


@dataclass
class Transcript:
    text: str
    language: str
    probability: float


class WhisperSTT:
    def __init__(self, model_size: str = "small", device: str = "auto") -> None:
        self.model_size = model_size
        self.device = device
        self._model = None
        self._lock = threading.Lock()
        self.loaded_on = ""

    @staticmethod
    def available() -> bool:
        try:
            import faster_whisper  # noqa: F401
            return True
        except ImportError:
            return False

    def _load(self):
        if self._model is not None:
            return self._model
        from faster_whisper import WhisperModel

        attempts: list[tuple[str, str]] = []
        if self.device in ("auto", "cuda"):
            preload_cuda_libs()
            try:
                import ctranslate2
                if ctranslate2.get_cuda_device_count() > 0:
                    attempts.append(("cuda", "float16"))
            except Exception:  # noqa: BLE001
                pass
        attempts.append(("cpu", "int8"))
        last: Exception | None = None
        for dev, ctype in attempts:
            try:
                model = WhisperModel(self.model_size, device=dev, compute_type=ctype)
                # warm-up: catches missing CUDA libraries (cuBLAS/cuDNN) early
                list(model.transcribe(np.zeros(16000, np.float32), beam_size=1)[0])
                self._model, self.loaded_on = model, f"{dev}/{ctype}"
                log.info("Whisper %s loaded on %s", self.model_size, self.loaded_on)
                return model
            except Exception as exc:  # noqa: BLE001
                log.warning("Whisper load failed on %s: %s", dev, exc)
                last = exc
        raise RuntimeError(f"Whisper yüklenemedi: {last}")

    def preload(self) -> None:
        with self._lock:
            self._load()

    @staticmethod
    def vocabulary_prompt() -> str:
        """Whisper 'initial prompt' with installed app names so they are spelled right ("Pear Desktop", not "peerdextap")."""
        base = "Volb, Türkçe sesli asistan. Volb, Google'ı aç. Volb, Blender'ı başlat. Uygulamalar: "
        try:
            from ..computer.apps import CATALOG
            apps = CATALOG.apps()
            media = [a.name for a in apps if {"Audio", "AudioVideo", "Video", "Music", "Player"} & set(a.categories)]
            rest = [a.name for a in apps if a.name not in media]
            names = ", ".join(dict.fromkeys(media + sorted(rest, key=str.lower)))
        except Exception:  # noqa: BLE001
            names = ""
        return (base + names)[:700]

    def transcribe(self, audio: np.ndarray, language: str | None = None) -> Transcript:
        with self._lock:
            model = self._load()
            segments, info = model.transcribe(
                audio.astype(np.float32), language=language, beam_size=5, vad_filter=True,
                initial_prompt=self.vocabulary_prompt())
            text = " ".join(s.text.strip() for s in segments).strip()
        return Transcript(text, info.language, float(info.language_probability))
