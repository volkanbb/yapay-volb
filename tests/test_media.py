import pytest

from app.agents.intent import parse_compound, parse_intent
from app.computer.media import Player, pick_player


@pytest.mark.parametrize("text,cmd,player", [
    ("Şarkıyı durdur", "pause", ""),
    ("Volb, Pear Desktop'taki şarkıyı durdur", "pause", "pear desktop"),
    ("müziği devam ettir", "play", ""),
    ("sonraki şarkı", "next", ""),
    ("şarkıyı geç", "next", ""),
    ("önceki şarkıya geç", "previous", ""),
    ("karışık çal", "shuffle_on", ""),
    ("karışık çalmayı kapat", "shuffle_off", ""),
    ("müziğin sesini aç", "volume_up", ""),
    ("sesi kıs", "system_volume_down", ""),
    ("sesi kapat", "system_mute", ""),
    ("şu an ne çalıyor", "now_playing", ""),
])
def test_media_intents(text, cmd, player):
    i = parse_intent(text)
    assert i.action == "media_control" and i.params["command"] == cmd and i.params["player"] == player
    assert parse_compound(text) is None


def test_playlist_is_not_resume():
    assert parse_intent("DEEP CODING listesini çal") is None
    assert parse_compound("Pear Desktop'ta DEEP CODING listesini çal")[0].action == "app_control"


def test_pick_player_prefers_playing_music_then_paused_for_resume():
    brave = Player("org.mpris.MediaPlayer2.brave.instance1", "Brave", "Paused", "video")
    pear = Player("org.mpris.MediaPlayer2.chromium.instance2", "com.github.th-ch.youtube-music", "Playing", "PIRAMIT")
    assert pick_player([brave, pear], "", "pause") is pear
    pear.status = "Paused"
    assert pick_player([brave, pear], "", "play") is pear        # resume a paused music app, not the browser
    assert pick_player([brave, pear], "brave", "play") is brave
