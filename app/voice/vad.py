"""Energy-based voice activity segmentation for continuous listening."""
from __future__ import annotations

import numpy as np

from .audio_io import TARGET_SR


class EnergyVAD:
    def __init__(self, start_level: float = 0.38, stop_level: float = 0.28, silence_s: float = 0.9,
                 min_speech_s: float = 0.45, max_speech_s: float = 15.0, preroll_s: float = 0.3) -> None:
        self.start_level = start_level
        self.stop_level = stop_level
        self.silence_s = silence_s
        self.min_speech_s = min_speech_s
        self.max_speech_s = max_speech_s
        self.preroll_s = preroll_s
        self.reset()

    def reset(self) -> None:
        self._buf: list[np.ndarray] = []
        self._pre: list[np.ndarray] = []
        self._in_speech = False
        self._silence = 0.0
        self._speech = 0.0

    @property
    def in_speech(self) -> bool:
        return self._in_speech

    def feed(self, block: np.ndarray, level: float) -> np.ndarray | None:
        """Feed a block; returns a finished utterance (16 kHz float32) or None."""
        dur = block.size / TARGET_SR
        if not self._in_speech:
            self._pre.append(block)
            while sum(b.size for b in self._pre) / TARGET_SR > self.preroll_s:
                self._pre.pop(0)
            if level >= self.start_level:
                self._in_speech = True
                self._buf = list(self._pre)
                self._pre = []
                self._speech = 0.0
                self._silence = 0.0
            return None
        self._buf.append(block)
        self._speech += dur
        self._silence = self._silence + dur if level < self.stop_level else 0.0
        if self._silence >= self.silence_s or self._speech >= self.max_speech_s:
            audio = np.concatenate(self._buf) if self._buf else np.zeros(0, np.float32)
            long_enough = self._speech - self._silence >= self.min_speech_s
            self.reset()
            return audio if long_enough else None
        return None
