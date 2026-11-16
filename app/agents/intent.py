"""Fast, deterministic Turkish/English command parser.

Handles common commands locally (no AI round-trip) and maps them to allowlisted actions.
Everything it doesn't understand goes to the AI provider.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..computer.actions import KNOWN_DIRS, SITE_ALLOWLIST, resolve_app, tr_lower

WAKE_RE = re.compile(r"^\s*(hey\s+|hi\s+|selam\s+)?(volb|volp|wolb|vol b|volbe|volbi)\b[\s,.:!-]*", re.I)
_TR_SUFFIX = re.compile(r"(?:'|’)\S*$")
_PLAIN_SUFFIXES = ("nı", "ni", "nu", "nü", "yı", "yi", "yu", "yü", "ı", "i", "u", "ü")
_DOMAIN_RE = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+(/\S*)?$")


@dataclass
class Intent:
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""


def strip_wake_word(text: str, wake_word: str = "volb") -> tuple[bool, str]:
    m = WAKE_RE.match(text)
    if m:
        return True, text[m.end():].strip()
    if tr_lower(text).startswith(tr_lower(wake_word)):
        return True, text[len(wake_word):].lstrip(" ,.:!").strip()
    return False, text.strip()


def _strip_suffix(word: str) -> list[str]:
    """'Google'ı' → ['google'], 'blenderı' → ['blenderı', 'blender']."""
    word = word.strip().strip(".!?")
    if _TR_SUFFIX.search(word):
        return [_TR_SUFFIX.sub("", word)]
    cands = [word]
    for suf in _PLAIN_SUFFIXES:
        if word.endswith(suf) and len(word) > len(suf) + 2:
            cands.append(word[: -len(suf)])
    return cands


def _resolve_open_target(raw: str) -> Intent | None:
    cands = _strip_suffix(raw.strip())
    for cand in cands:  # exact sites, folders and domains first
        key = tr_lower(cand)
        if key in SITE_ALLOWLIST:
            return Intent("open_url", {"url": SITE_ALLOWLIST[key]}, f"{cand.capitalize()} açılıyor")
        if key in KNOWN_DIRS:
            return Intent("open_directory", {"path": key}, f"{cand.capitalize()} klasörü açılıyor")
    for cand in reversed(cands):  # then installed apps; suffix-stripped form first ("blenderı" → "blender")
        app = resolve_app(cand)
        if app:
            return Intent("launch_app", {"app": tr_lower(cand)}, f"{app.label} başlatılıyor")
    for cand in cands:
        key = tr_lower(cand)
        if _DOMAIN_RE.match(key):
            return Intent("open_url", {"url": key}, f"{key} açılıyor")
    return None


_MEDIA = [  # (command, pattern) — order matters
    ("now_playing", r"\b(ne çalıyor|hangi (şarkı|parça)|bu (şarkı|parça) ne|şu an ne çalıyor|what'?s playing)\b"),
    ("shuffle_off", r"\b(karışık çal\w*|karıştır\w*|shuffle)\b.*\b(kapat|durdur|off)\b"),
    ("shuffle_on", r"\b(karışık çal\w*|karıştır|shuffle)\b"),
    ("next", r"\b(sonraki|sıradaki|bir sonraki) (şarkı|parça)\w*\b|\b(şarkıyı|parçayı) (geç|atla)\b|\bnext (song|track)\b|^(geç|atla|next)$"),
    ("previous", r"\b(önceki|bir önceki) (şarkı|parça)\w*\b|\bprevious (song|track)\b"),
    ("pause", r"\b(şarkı|müzi[kğ]|parça|video|yayın|çalan|medya)\w*\s+(durdur|duraklat|kapat|sustur)\w*|^(durdur|duraklat|pause)$|\bpause (the )?(music|song)\b"),
    ("play", r"\b(şarkı|müzi[kğ]|parça)\w*\s+(devam ettir|devam et|kaldığı yerden|başlat|oynat|çal)\w*$|^(devam ettir|devam|resume)$|\bresume (the )?(music|song)\b"),
    ("volume_up", r"\b(müziğin|şarkının|müzik|parçanın)\s+ses\w*\s+(aç|yükselt|artır)\w*"),
    ("volume_down", r"\b(müziğin|şarkının|müzik|parçanın)\s+ses\w*\s+(kıs|azalt|düşür)\w*"),
    ("system_mute", r"\b(sesi|bilgisayarın sesini)\s+(kapat|sustur)\w*|\bmute\b"),
    ("system_volume_up", r"\b(sesi|ses seviyesini|bilgisayarın sesini)\s+(aç|yükselt|artır)\w*|\bvolume up\b"),
    ("system_volume_down", r"\b(sesi|ses seviyesini|bilgisayarın sesini)\s+(kıs|azalt|düşür)\w*|\bvolume down\b"),
]
_MEDIA_HINT = re.compile(r"^(.+?)(?:'|’)?(?:da|de|ta|te)(?:ki)?\s+(.+)$")


def parse_media(text: str) -> Intent | None:
    _, body = strip_wake_word(text)
    t = tr_lower(body).strip().rstrip(".!?").strip()
    hint, rest = "", t
    m = _MEDIA_HINT.match(t)
    if m and resolve_app(m.group(1).strip()):
        hint, rest = m.group(1).strip(), m.group(2)
    for cmd, pat in _MEDIA:
        if re.search(pat, rest):
            if cmd == "play" and not re.search(r"\b(devam|kaldığı|resume)\b", rest) and re.search(r"\blistesi|albüm", rest):
                return None  # "DEEP CODING listesini çal" → needs in-app control, not resume
            label = {"pause": "Müzik durduruluyor", "play": "Müzik devam ediyor", "next": "Sonraki parça",
                     "previous": "Önceki parça", "shuffle_on": "Karışık çalma açılıyor",
                     "shuffle_off": "Karışık çalma kapatılıyor", "volume_up": "Ses açılıyor",
                     "volume_down": "Ses kısılıyor", "now_playing": "Çalan parça",
                     "system_volume_up": "Sistem sesi açılıyor", "system_volume_down": "Sistem sesi kısılıyor",
                     "system_mute": "Ses kapatılıyor"}[cmd]
            return Intent("media_control", {"command": cmd, "player": hint}, label)
    return None


def parse_intent(text: str) -> Intent | None:
    _, body = strip_wake_word(text)
    t = tr_lower(body).strip().rstrip(".!?").strip()
    if not t:
        return None
    media = parse_media(body)
    if media:
        return media

    if re.search(r"\bsaat kaç\b|\bgünlerden ne\b|\btarih(i)? ne\b|\bwhat time\b|\bwhat day\b", t):
        return Intent("current_time", {}, "Saat kontrol ediliyor")

    if re.search(r"ekran görüntüsü|screenshot", t):
        return Intent("screenshot", {}, "Ekran görüntüsü alınıyor")

    m = re.search(r"\b(ram|bellek|hafıza|cpu|işlemci|disk|sistem)\w*\b.*\b(göster|kullanım|durum|ne kadar|nedir|kaç)",
                  t) or re.search(r"\b(?:show|check)\b.*\b(ram|memory|cpu|disk|system)\b", t)
    if m:
        word = m.group(1)
        focus = {"ram": "ram", "bellek": "ram", "hafıza": "ram", "memory": "ram", "cpu": "cpu", "işlemci": "cpu",
                 "disk": "disk"}.get(word)
        return Intent("system_stats", {"focus": focus}, "Sistem kaynakları okunuyor")

    m = re.match(r"^(.+?)\s+(?:hakkında\s+|ile ilgili\s+|konusunda\s+)?(?:araştır\w*|araştırma yap\w*)$", t) \
        or re.match(r"^(?:research|investigate)\s+(.+)$", t)
    if m:
        topic = m.group(1).strip()
        return Intent("research", {"topic": topic}, f"'{topic}' araştırılıyor")

    m = re.match(r"^(?:google'?da|internette|webde|web'de)\s+(.+?)\s+(?:ara|arat)$", t) \
        or re.match(r"^(?:google|search for|search)\s+(.+)$", t)
    if m:
        return Intent("web_search", {"query": m.group(1)}, f"'{m.group(1)}' aranıyor")

    m = re.match(r"^(.+?)\s+(?:adında|isimli|adlı)\s+(?:bir\s+)?(?:klasör|dizin)\s+(?:oluştur|yarat|aç)\w*$", t) \
        or re.match(r"^(?:create|make)\s+(?:a\s+)?folder\s+(?:named\s+|called\s+)?(.+)$", t)
    if m:
        name = m.group(1).strip().strip("'\"")
        desktop = str(KNOWN_DIRS["masaüstü"]())
        return Intent("create_folder", {"path": f"{desktop}/{name}"}, f"'{name}' klasörü oluşturuluyor")

    m = re.match(r"^(.+?)\s+(?:dosyasını|dosyalarını|adlı dosyayı|isimli dosyayı)\s+(?:bul|ara)$", t) \
        or re.match(r"^find\s+(?:the\s+)?files?\s+(?:named\s+)?(.+)$", t)
    if m:
        return Intent("search_files", {"query": m.group(1).strip()}, f"'{m.group(1)}' dosyaları aranıyor")

    m = re.match(r"^(.+?)\s+(?:klasörünü|klasörü|dizinini)?\s*(?:aç|başlat|çalıştır)(?:\s+lütfen)?$", t)
    if m:
        intent = _resolve_open_target(m.group(1))
        if intent:
            return intent
    m = re.match(r"^(?:open|launch|start|run)\s+(.+?)(?:\s+please)?$", t)
    if m:
        intent = _resolve_open_target(m.group(1))
        if intent:
            return intent
    return None


_APP_LOC = re.compile(r"^(.+?)(?:'|’)(?:da|de|ta|te|nda|nde)\s+(.+)$")
_AND_THEN = re.compile(r"^(.+?)\s*(?:,\s*)?(?:\bve\b|\bsonra\b|\bardından\b|\band then\b|\band\b)\s+(.+)$")


def parse_compound(text: str) -> list[Intent] | None:
    if parse_media(text):
        return None  # media commands are handled instantly via MPRIS
    """"YouTube Music'i aç ve DEEP CODING listesini çal" → [launch_app, app_control]
    "Pear Desktop'ta DEEP CODING listesini aç"          → [app_control]"""
    _, body = strip_wake_word(text)
    body = body.strip().rstrip(".!?")
    m = _AND_THEN.match(body)
    if m:
        first = parse_intent(m.group(1))
        if first and first.action == "launch_app":
            goal = m.group(2).strip()
            return [first, Intent("app_control", {"app": first.params["app"], "goal": goal},
                                  f"Uygulamada: {goal}")]
    m = _APP_LOC.match(body)
    if m:
        app_raw = m.group(1).strip()
        if tr_lower(app_raw) not in KNOWN_DIRS and tr_lower(app_raw) not in SITE_ALLOWLIST and resolve_app(app_raw):
            goal = m.group(2).strip()
            return [Intent("app_control", {"app": tr_lower(app_raw), "goal": goal}, f"{app_raw}: {goal}")]
    return None
