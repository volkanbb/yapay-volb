"""Voice round-trip self-test: Piper TTS → resample 16 kHz → Faster-Whisper → wake word → intent.
Also probes the microphone for 1 s (level only, nothing is stored)."""
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np  # noqa: E402

from app.agents.intent import parse_intent  # noqa: E402
from app.voice.audio_io import MicrophoneStream, resample  # noqa: E402
from app.voice.stt import WhisperSTT  # noqa: E402
from app.voice.tts import PiperTTS  # noqa: E402
from app.voice.wakeword import TranscriptWakeWord  # noqa: E402


async def main() -> None:
    tts = PiperTTS()
    print("piper:", tts.available())
    t0 = time.time()
    audio, sr = await tts.synthesize("Volb, Blender'ı başlat.")
    print(f"tts: {audio.size / sr:.2f}s audio @ {sr} Hz in {time.time() - t0:.2f}s")
    stt = WhisperSTT("small", "auto")
    t0 = time.time()
    tr = stt.transcribe(resample(audio, sr), language="tr")
    print(f"stt [{stt.loaded_on}] {time.time() - t0:.2f}s: {tr.text!r}")
    detected, cmd = TranscriptWakeWord().detect_text(tr.text)
    print("wake:", detected, "| command:", cmd, "| intent:", parse_intent(cmd))

    levels = []
    mic = MicrophoneStream(lambda b, lvl: levels.append(lvl))
    try:
        mic.start()
        await asyncio.sleep(1.0)
    finally:
        mic.stop()
    print(f"mic: {len(levels)} blocks, peak level {max(levels, default=0):.2f}")

asyncio.run(main())
