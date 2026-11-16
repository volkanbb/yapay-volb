"""Microphone capture and speaker playback (sounddevice / PortAudio) with live level metering."""
from __future__ import annotations

import logging
import threading
from collections.abc import Callable

import numpy as np

log = logging.getLogger(__name__)
TARGET_SR = 16_000

try:
    import sounddevice as sd
except (ImportError, OSError) as _exc:  # pragma: no cover - depends on system
    sd = None
    log.warning("sounddevice unavailable: %s", _exc)


def audio_available() -> bool:
    return sd is not None


def list_input_devices() -> list[dict]:
    if sd is None:
        return []
    out = [{"index": -1, "name": "Sistem varsayılanı"}]
    try:
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0:
                out.append({"index": i, "name": d["name"]})
    except Exception as exc:  # noqa: BLE001
        log.warning("device query failed: %s", exc)
    return out


def default_input_name() -> str:
    if sd is None:
        return "ses sistemi yok"
    try:
        return sd.query_devices(kind="input")["name"]
    except Exception:  # noqa: BLE001
        return "bilinmiyor"


def resample(audio: np.ndarray, src_sr: int, dst_sr: int = TARGET_SR) -> np.ndarray:
    if src_sr == dst_sr or audio.size == 0:
        return audio.astype(np.float32)
    n = int(round(audio.size * dst_sr / src_sr))
    x_old = np.linspace(0.0, 1.0, audio.size, endpoint=False)
    x_new = np.linspace(0.0, 1.0, n, endpoint=False)
    return np.interp(x_new, x_old, audio).astype(np.float32)


def rms_level(block: np.ndarray) -> float:
    """Perceptual 0..1 level from float32 samples."""
    if block.size == 0:
        return 0.0
    rms = float(np.sqrt(np.mean(np.square(block))))
    db = 20 * np.log10(max(rms, 1e-6))
    return float(np.clip((db + 55) / 45, 0.0, 1.0))


class MicrophoneStream:
    """Continuously captures mono float32 audio at 16 kHz and reports blocks + levels."""

    def __init__(self, on_block: Callable[[np.ndarray, float], None], device: int | None = None) -> None:
        self.on_block = on_block
        self.device = None if device is None or device < 0 else device
        self._stream = None
        self._sr = TARGET_SR

    @property
    def active(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        if sd is None:
            raise RuntimeError("Ses sistemi (PortAudio) kullanılamıyor.")
        if self._stream:
            return
        try:
            self._open(TARGET_SR)
        except Exception:  # noqa: BLE001 - device may not support 16k; use its native rate
            info = sd.query_devices(self.device, kind="input")
            self._open(int(info["default_samplerate"]))

    def _open(self, sr: int) -> None:
        self._sr = sr

        def callback(indata, frames, time_info, status) -> None:  # noqa: ARG001
            mono = indata[:, 0].copy() if indata.ndim > 1 else indata.copy()
            block = resample(mono, sr)
            self.on_block(block, rms_level(block))

        self._stream = sd.InputStream(samplerate=sr, channels=1, dtype="float32", device=self.device,
                                      blocksize=int(sr * 0.05), callback=callback)
        self._stream.start()

    def stop(self) -> None:
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None


class AudioPlayer:
    """Plays float32 PCM and reports a smoothed output level (drives VOLB's beak)."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._done = threading.Event()
        self._done.set()

    @property
    def playing(self) -> bool:
        return not self._done.is_set()

    def stop(self) -> None:
        self._stop.set()

    def play_blocking(self, audio: np.ndarray, sr: int, on_level: Callable[[float], None]) -> None:
        if sd is None:
            raise RuntimeError("Ses çıkışı yok.")
        self._stop.clear()
        self._done.clear()
        pos = 0
        finished = threading.Event()
        audio = audio.astype(np.float32)

        def callback(outdata, frames, time_info, status) -> None:  # noqa: ARG001
            nonlocal pos
            if self._stop.is_set():
                outdata.fill(0)
                raise sd.CallbackStop
            chunk = audio[pos:pos + frames]
            outdata[: len(chunk), 0] = chunk
            outdata[len(chunk):, 0] = 0
            pos += frames
            on_level(rms_level(chunk) if len(chunk) else 0.0)
            if pos >= len(audio):
                raise sd.CallbackStop

        try:
            with sd.OutputStream(samplerate=sr, channels=1, dtype="float32", callback=callback,
                                 blocksize=int(sr * 0.03), finished_callback=finished.set):
                finished.wait(timeout=len(audio) / sr + 5)
        finally:
            on_level(0.0)
            self._done.set()
