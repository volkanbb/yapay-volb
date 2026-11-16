"""VoiceService: push-to-talk, continuous listening with wake word, STT and TTS playback."""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from ..core.config import Settings
from .audio_io import AudioPlayer, MicrophoneStream, audio_available, default_input_name
from .stt import WhisperSTT
from .tts import TTSEngine, clean_for_speech, create_tts
from .vad import EnergyVAD
from .wakeword import TranscriptWakeWord, WakeWordDetector

log = logging.getLogger(__name__)
FOLLOW_UP_WINDOW_S = 7.0


class VoiceEvents(Protocol):
    def on_mic_level(self, level: float) -> None: ...
    def on_speech_level(self, level: float) -> None: ...
    def on_voice_state(self, listening: bool, speaking: bool, status: str) -> None: ...
    def on_voice_command(self, text: str, language: str) -> None: ...
    def on_voice_error(self, message: str) -> None: ...


@dataclass
class VoiceStatus:
    mic: str = ""
    stt: str = ""
    tts: str = ""


class VoiceService:
    def __init__(self, settings: Settings, events: VoiceEvents, loop: asyncio.AbstractEventLoop) -> None:
        self.settings = settings
        self.events = events
        self.loop = loop
        self.stt = WhisperSTT(settings.stt_model, settings.stt_device)
        self.tts: TTSEngine = create_tts(settings.tts_engine, settings.piper_voice, settings.edge_voice,
                                         settings.allow_edge_tts)
        self.wake: WakeWordDetector = TranscriptWakeWord(settings.wake_word)
        self.vad = EnergyVAD()
        self.player = AudioPlayer()
        self._mic: MicrophoneStream | None = None
        self._ptt = False
        self._ptt_buf: list[np.ndarray] = []
        self._continuous = False
        self._speaking = False
        self._armed_until = 0.0
        self._lock = threading.Lock()
        self._busy = False
        self._speech_q: asyncio.Queue | None = None
        self._speech_worker: asyncio.Task | None = None
        self._speech_gen = 0
        self._last_spoken: tuple[str, float] = ("", 0.0)

    # ------------------------------------------------------------ status
    def status(self) -> VoiceStatus:
        mic = default_input_name() if audio_available() else "ses sistemi yok"
        stt = f"Whisper {self.stt.model_size}" + (f" • {self.stt.loaded_on}" if self.stt.loaded_on else "") \
            if WhisperSTT.available() else "faster-whisper yok"
        ok, why = self.tts.available()
        tts = self.tts.name if ok and self.tts.name != "none" else (why or "kapalı")
        return VoiceStatus(mic, stt, tts)

    def reload_tts(self, settings: Settings) -> None:
        self.settings = settings
        self.tts = create_tts(settings.tts_engine, settings.piper_voice, settings.edge_voice, settings.allow_edge_tts)

    # ------------------------------------------------------------ microphone
    def _ensure_mic(self) -> None:
        if self._mic is None:
            dev = self.settings.mic_device
            self._mic = MicrophoneStream(self._on_block, None if dev < 0 else dev)
        if not self._mic.active:
            self._mic.start()

    def _release_mic(self) -> None:
        if self._mic and not self._ptt and not self._continuous:
            self._mic.stop()
            self.events.on_mic_level(0.0)

    def set_device(self, index: int) -> None:
        was = self._mic.active if self._mic else False
        if self._mic:
            self._mic.stop()
        self._mic = None
        self.settings.mic_device = index
        if was:
            self._ensure_mic()

    def _on_block(self, block: np.ndarray, level: float) -> None:
        self.events.on_mic_level(level)
        if self._ptt:
            self._ptt_buf.append(block)
            return
        if self._continuous and not self._speaking and not self._busy:
            utterance = self.vad.feed(block, level)
            if utterance is not None:
                asyncio.run_coroutine_threadsafe(self._process(utterance, require_wake=True), self.loop)

    # ------------------------------------------------------------ push to talk
    def start_push_to_talk(self) -> None:
        try:
            self.stop_speaking()
            self._ptt_buf = []
            self._ptt = True
            self._ensure_mic()
            self.events.on_voice_state(True, False, "Dinliyorum…")
        except Exception as exc:  # noqa: BLE001
            self._ptt = False
            self.events.on_voice_error(f"Mikrofon açılamadı: {exc}")

    def stop_push_to_talk(self) -> None:
        if not self._ptt:
            return
        self._ptt = False
        audio = np.concatenate(self._ptt_buf) if self._ptt_buf else np.zeros(0, np.float32)
        self._ptt_buf = []
        self._release_mic()
        if audio.size < 16000 * 0.3:
            self.events.on_voice_state(False, False, "Ses kaydı çok kısa")
            return
        asyncio.run_coroutine_threadsafe(self._process(audio, require_wake=False), self.loop)

    # ------------------------------------------------------------ continuous
    def set_continuous(self, enabled: bool) -> None:
        self._continuous = enabled
        self.vad.reset()
        try:
            if enabled:
                self._ensure_mic()
                self.events.on_voice_state(False, False, f"Sürekli dinleme açık — '{self.settings.wake_word}' de")
                asyncio.run_coroutine_threadsafe(asyncio.to_thread(self._safe_preload), self.loop)
            else:
                self._release_mic()
                self.events.on_voice_state(False, False, "Sürekli dinleme kapalı")
        except Exception as exc:  # noqa: BLE001
            self._continuous = False
            self.events.on_voice_error(f"Mikrofon açılamadı: {exc}")

    def _safe_preload(self) -> None:
        try:
            self.stt.preload()
        except Exception as exc:  # noqa: BLE001
            self.events.on_voice_error(str(exc))

    async def _process(self, audio: np.ndarray, require_wake: bool) -> None:
        if not WhisperSTT.available():
            self.events.on_voice_error("faster-whisper kurulu değil.")
            return
        self._busy = True
        try:
            self.events.on_voice_state(False, False, "Ses çözümleniyor…")
            lang = None if self.settings.language == "auto" else self.settings.language
            tr = await asyncio.to_thread(self.stt.transcribe, audio, lang)
            text = tr.text.strip()
            log.info("STT [%s %.2f]: %s", tr.language, tr.probability, text)
            if not text:
                self.events.on_voice_state(False, False, "Bir şey duyamadım")
                return
            if require_wake:
                detected, command = self.wake.detect_text(text)
                if not detected:
                    if time.monotonic() < self._armed_until:
                        command = text
                    else:
                        self.events.on_voice_state(False, False, "")
                        return
                if not command:
                    self._armed_until = time.monotonic() + FOLLOW_UP_WINDOW_S
                    self.events.on_voice_state(True, False, "Efendim? Dinliyorum…")
                    return
                self._armed_until = 0.0
                text = command
            self.events.on_voice_command(text, tr.language)
        except Exception as exc:  # noqa: BLE001
            log.exception("transcription failed")
            self.events.on_voice_error(f"Ses tanıma hatası: {exc}")
        finally:
            self._busy = False

    # ------------------------------------------------------------ speaking
    # All speech goes through ONE queue + worker, so two replies can never play on top of each other.
    async def speak(self, text: str) -> None:
        text = clean_for_speech(text)
        if not text or self.tts.name == "none":
            return
        now = time.monotonic()
        if text == self._last_spoken[0] and now - self._last_spoken[1] < 5:
            return  # same sentence requested twice in a row → say it once
        self._last_spoken = (text, now)
        if self._speech_q is None:
            self._speech_q = asyncio.Queue()
        await self._speech_q.put((self._speech_gen, text))
        if self._speech_worker is None or self._speech_worker.done():
            self._speech_worker = asyncio.create_task(self._speech_loop())

    async def _speech_loop(self) -> None:
        assert self._speech_q is not None
        while not self._speech_q.empty():
            gen, text = await self._speech_q.get()
            if gen != self._speech_gen:
                continue  # interrupted while waiting
            try:
                audio, sr = await self.tts.synthesize(text[:1500])
            except Exception as exc:  # noqa: BLE001
                log.warning("TTS failed: %s", exc)
                self.events.on_voice_error(f"Seslendirme hatası: {exc}")
                continue
            if audio.size == 0 or gen != self._speech_gen:
                continue
            self._speaking = True
            self.events.on_voice_state(False, True, "Konuşuyor")
            try:
                await asyncio.to_thread(self.player.play_blocking, audio, sr, self.events.on_speech_level)
            except Exception as exc:  # noqa: BLE001
                self.events.on_voice_error(f"Ses çalınamadı: {exc}")
            finally:
                self._speaking = False
                self.vad.reset()
        self.events.on_voice_state(False, False, "")

    def stop_speaking(self) -> None:
        """Stop the current sentence and drop everything still queued."""
        self._speech_gen += 1
        self.player.stop()

    @property
    def speaking(self) -> bool:
        return self._speaking

    def shutdown(self) -> None:
        self._continuous = False
        self._ptt = False
        self.player.stop()
        if self._mic:
            self._mic.stop()
