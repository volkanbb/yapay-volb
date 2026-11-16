"""Instant media control through MPRIS (D-Bus): works with Pear/YouTube Music, Spotify, VLC, browsers…

No AI call and no clicking — "şarkıyı durdur" takes milliseconds.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)
ROOT = "/org/mpris/MediaPlayer2"
PLAYER_IF = "org.mpris.MediaPlayer2.Player"
BROWSERS = ("firefox", "brave", "chrom", "vivaldi", "opera", "edge", "plasma-browser-integration")


@dataclass
class Player:
    bus_name: str
    identity: str
    status: str          # Playing | Paused | Stopped
    title: str = ""
    artist: str = ""

    @property
    def is_browser(self) -> bool:
        low = (self.bus_name + " " + self.identity).lower()
        return any(b in low for b in BROWSERS) and "pear" not in low and "music" not in low

    @property
    def label(self) -> str:
        """Friendly name: 'com.github.th-ch.youtube-music' → 'Pear Desktop' via the app catalog."""
        try:
            from .apps import CATALOG
            entry = CATALOG.get(self.identity) or (CATALOG.find(self.identity) if "." not in self.identity else None)
            if entry:
                return entry.name
        except Exception:  # noqa: BLE001
            pass
        return self.identity

    def keys(self) -> str:
        pid = self.bus_name.rsplit("instance", 1)[-1] if "instance" in self.bus_name else ""
        cmd = ""
        if pid.isdigit():
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as f:
                    cmd = f.read().replace(b"\0", b" ").decode(errors="ignore")
            except OSError:
                pass
        return f"{self.bus_name} {self.identity} {self.label} {cmd}".lower()

    def describe(self) -> str:
        now = f"{self.title}" + (f" — {self.artist}" if self.artist else "")
        return f"{self.label}: {now}" if now else self.label


def loc(word: str) -> str:
    """Turkish locative suffix with vowel harmony: Pear Desktop'ta, Spotify'da, Brave'de, VLC'de."""
    last = word.split()[-1] if word.split() else word
    if last.isupper() and len(last) <= 5:          # acronyms are read letter by letter: VLC'de, OBS'de, KDE'de
        return f"{word}'{'da' if last[-1] in 'AIOUK' else 'de'}"
    low = last.replace("I", "ı").replace("İ", "i").lower()
    vowels = [c for c in low if c in "aıoueiöü"]
    back = not vowels or vowels[-1] in "aıou"
    hard = low[-1:] in "çfhkpsştxc"                 # Firefox'ta, Music'te
    return f"{word}'{'t' if hard else 'd'}{'a' if back else 'e'}"


def _bus():
    from gi.repository import Gio
    return Gio.bus_get_sync(Gio.BusType.SESSION, None)


def _get(bus, name: str, iface: str, prop: str):
    from gi.repository import Gio, GLib
    try:
        res = bus.call_sync(name, ROOT, "org.freedesktop.DBus.Properties", "Get", GLib.Variant("(ss)", (iface, prop)),
                            None, Gio.DBusCallFlags.NONE, 1500, None)
        return res.unpack()[0]
    except Exception:  # noqa: BLE001
        return None


def list_players() -> list[Player]:
    from gi.repository import Gio
    bus = _bus()
    names = bus.call_sync("org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", "ListNames",
                          None, None, Gio.DBusCallFlags.NONE, 1500, None).unpack()[0]
    players = []
    for n in names:
        if not n.startswith("org.mpris.MediaPlayer2."):
            continue
        meta = _get(bus, n, PLAYER_IF, "Metadata") or {}
        artist = meta.get("xesam:artist") or []
        players.append(Player(n, _get(bus, n, "org.mpris.MediaPlayer2", "Identity") or n.rsplit(".", 1)[-1],
                              _get(bus, n, PLAYER_IF, "PlaybackStatus") or "Stopped",
                              meta.get("xesam:title") or "", ", ".join(artist) if isinstance(artist, list) else str(artist)))
    return players


def pick_player(players: list[Player], hint: str = "", command: str = "") -> Player | None:
    if not players:
        return None
    if hint:
        terms = {hint.lower()}
        try:
            from .actions import resolve_app
            app = resolve_app(hint)
            if app:
                terms |= {app.label.lower(), app.desktop_id.lower()}
                terms |= {t for t in app.desktop_id.lower().replace("-", ".").split(".") if len(t) >= 5}
        except Exception:  # noqa: BLE001
            pass
        terms |= {t for t in hint.lower().split() if len(t) >= 4}
        matched = [p for p in players if any(t in p.keys() for t in terms)]
        if matched:
            players = matched

    def score(p: Player) -> tuple:
        # resuming → prefer a paused music app; otherwise → whatever is playing now
        active = p.status == ("Paused" if command in ("play",) else "Playing")
        return (active, p.status == "Playing", not p.is_browser, bool(p.title))
    return max(players, key=score)


def _call(name: str, method: str) -> None:
    from gi.repository import Gio
    _bus().call_sync(name, ROOT, PLAYER_IF, method, None, None, Gio.DBusCallFlags.NONE, 2000, None)


def _set(name: str, prop: str, value) -> None:
    from gi.repository import Gio, GLib
    _bus().call_sync(name, ROOT, "org.freedesktop.DBus.Properties", "Set",
                     GLib.Variant("(ssv)", (PLAYER_IF, prop, value)), None, Gio.DBusCallFlags.NONE, 2000, None)


COMMANDS = ("play", "pause", "toggle", "next", "previous", "stop", "shuffle_on", "shuffle_off",
            "volume_up", "volume_down", "now_playing")


def system_volume(command: str) -> tuple[bool, str]:
    """Default output volume via PipeWire (wpctl) or PulseAudio (pactl)."""
    import re
    import shutil
    import subprocess
    if shutil.which("wpctl"):
        arg = {"system_volume_up": ["set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", "10%+"],
               "system_volume_down": ["set-volume", "@DEFAULT_AUDIO_SINK@", "10%-"],
               "system_mute": ["set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"]}[command]
        subprocess.run(["wpctl", *arg], check=False, timeout=3)  # noqa: S603,S607
        out = subprocess.run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], capture_output=True, text=True,
                             timeout=3).stdout  # noqa: S603,S607
        m = re.search(r"([\d.]+)", out)
        muted = "MUTED" in out
        return True, "Ses kapatıldı." if muted else f"Sistem sesi %{round(float(m.group(1)) * 100)}." if m else "Tamam."
    if shutil.which("pactl"):
        arg = {"system_volume_up": ["set-sink-volume", "@DEFAULT_SINK@", "+10%"],
               "system_volume_down": ["set-sink-volume", "@DEFAULT_SINK@", "-10%"],
               "system_mute": ["set-sink-mute", "@DEFAULT_SINK@", "toggle"]}[command]
        subprocess.run(["pactl", *arg], check=False, timeout=3)  # noqa: S603,S607
        return True, "Tamam."
    return False, "Ses ayarı için wpctl/pactl bulunamadı."


def control(command: str, hint: str = "") -> tuple[bool, str]:
    from gi.repository import GLib
    if command.startswith("system_"):
        return system_volume(command)
    try:
        players = list_players()
    except Exception as exc:  # noqa: BLE001
        return False, f"Medya oynatıcılarına ulaşamadım: {exc}"
    p = pick_player(players, hint, command)
    if p is None:
        return False, "Açık bir müzik/medya oynatıcısı bulamadım."
    try:
        if command == "now_playing":
            if not p.title:
                return True, f"{p.label} şu an bir şey çalmıyor."
            return True, f"{loc(p.label)} şu an {p.title}" + (f", {p.artist}" if p.artist else "") + \
                (" çalıyor." if p.status == "Playing" else " duraklatılmış.")
        if command in ("pause", "stop"):
            _call(p.bus_name, "Pause" if command == "pause" else "Stop")
            return True, f"{p.label} durduruldu."
        if command == "play":
            _call(p.bus_name, "Play")
            return True, f"{p.label} çalmaya devam ediyor" + (f": {p.title}." if p.title else ".")
        if command == "toggle":
            _call(p.bus_name, "PlayPause")
            return True, f"{p.label}: oynat/duraklat."
        if command in ("next", "previous"):
            _call(p.bus_name, "Next" if command == "next" else "Previous")
            return True, f"{p.label}: {'sonraki' if command == 'next' else 'önceki'} parça."
        if command in ("shuffle_on", "shuffle_off"):
            _set(p.bus_name, "Shuffle", GLib.Variant("b", command == "shuffle_on"))
            return True, f"{p.label}: karışık çalma {'açık' if command == 'shuffle_on' else 'kapalı'}."
        if command in ("volume_up", "volume_down"):
            vol = _get(_bus(), p.bus_name, PLAYER_IF, "Volume")
            vol = 0.5 if vol is None else float(vol)
            vol = max(0.0, min(1.0, vol + (0.15 if command == "volume_up" else -0.15)))
            _set(p.bus_name, "Volume", GLib.Variant("d", vol))
            return True, f"{p.label} ses seviyesi %{round(vol * 100)}."
    except Exception as exc:  # noqa: BLE001
        log.warning("mpris %s failed: %s", command, exc)
        return False, f"{p.label} bu komutu desteklemiyor ({command})."
    return False, f"Bilinmeyen medya komutu: {command}"
