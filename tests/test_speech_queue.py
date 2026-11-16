"""Replies are spoken one after another, never on top of each other; new input interrupts."""
import asyncio
import threading
import time

import numpy as np

from app.core.config import Settings
from app.voice.service import VoiceService


class Ev:
    def __getattr__(self, name):
        return lambda *a, **k: None


class FakeTTS:
    name = "fake"

    def available(self):
        return True, ""

    async def synthesize(self, text):
        return np.ones(100, np.float32), 1000


class FakePlayer:
    def __init__(self):
        self.active = 0
        self.max_active = 0
        self.played: list[float] = []
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def play_blocking(self, audio, sr, on_level):
        self._stop.clear()
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        end = time.monotonic() + 0.15
        while time.monotonic() < end and not self._stop.is_set():
            time.sleep(0.01)
        self.played.append(audio.size)
        self.active -= 1


async def test_speech_is_serialized_and_deduplicated():
    vs = VoiceService(Settings(), Ev(), asyncio.get_running_loop())
    vs.tts, vs.player = FakeTTS(), FakePlayer()
    await vs.speak("birinci cümle")
    await vs.speak("ikinci cümle")
    await vs.speak("ikinci cümle")      # duplicate → spoken once
    await vs._speech_worker
    assert vs.player.max_active == 1 and len(vs.player.played) == 2


async def test_stop_drops_queue():
    vs = VoiceService(Settings(), Ev(), asyncio.get_running_loop())
    vs.tts, vs.player = FakeTTS(), FakePlayer()
    for i in range(4):
        await vs.speak(f"cümle {i}")
    await asyncio.sleep(0.05)
    vs.stop_speaking()
    await vs._speech_worker
    assert len(vs.player.played) == 1
