import numpy as np

from app.voice.audio_io import resample, rms_level
from app.voice.tts import clean_for_speech
from app.voice.vad import EnergyVAD
from app.voice.wakeword import TranscriptWakeWord


def test_wake_word_variants():
    w = TranscriptWakeWord("volb")
    assert w.detect_text("Volb, Google'ı aç.") == (True, "Google'ı aç.")
    assert w.detect_text("Volp Blender'ı başlat") == (True, "Blender'ı başlat")
    assert w.detect_text("Hey Volb!") == (True, "")
    assert w.detect_text("bugün hava güzel")[0] is False


def test_vad_segments_utterance():
    vad = EnergyVAD(silence_s=0.3, min_speech_s=0.2)
    block = np.zeros(800, np.float32)
    out = None
    for _ in range(5):
        assert vad.feed(block, 0.0) is None
    for level in [0.9] * 10 + [0.0] * 10:
        seg = vad.feed(block, level)
        if seg is not None:
            out = seg
    assert out is not None and out.size > 800 * 10


def test_audio_helpers():
    assert rms_level(np.zeros(100, np.float32)) == 0.0
    assert rms_level(np.ones(100, np.float32) * 0.5) > 0.8
    assert resample(np.ones(48000, np.float32), 48000).size == 16000


def test_clean_for_speech():
    assert clean_for_speech("**Kalın** [1] https://x.com `kod`") == "Kalın bağlantı kod"
