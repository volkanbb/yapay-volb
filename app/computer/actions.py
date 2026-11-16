"""Allowlisted computer actions.

The AI may only *propose* actions by name + JSON params. Each proposal is validated against a
pydantic schema, checked against the risk policy and (if needed) approved by the user before the
fixed Python handler runs. Model text is never passed to a shell.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import logging
import os
import shutil
import subprocess
import sys
import webbrowser
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlparse

from pydantic import BaseModel, Field, ValidationError, field_validator

from ..core.config import DATA_DIR
from ..security.policy import Risk, is_sensitive_path, is_within
from . import apps as _apps
from .apps import launch_desktop_entry
from .system_monitor import read_stats, top_processes

log = logging.getLogger(__name__)
HOME = Path.home()


def tr_lower(text: str) -> str:
    return text.replace("I", "ı").replace("İ", "i").lower()


# ----------------------------------------------------------------------------- allowlists
# alias → candidate executables (first one found on PATH wins)
APP_ALLOWLIST: dict[str, list[str]] = {
    "blender": ["blender"],
    "firefox": ["firefox"],
    "chrome": ["google-chrome-stable", "google-chrome", "chromium"],
    "chromium": ["chromium"],
    "terminal": ["konsole", "gnome-terminal", "kitty", "alacritty", "xterm"],
    "youtube music": ["youtube-music-for-desktop", "pear-desktop", "youtube-music"],
    "ayarlar": ["systemsettings", "gnome-control-center"],
    "pear desktop": ["pear-desktop"],
    "dosyalar": ["dolphin", "nautilus", "thunar"],
    "vscode": ["code", "codium", "code-oss"],
    "kate": ["kate"],
    "spotify": ["spotify"],
    "discord": ["discord"],
    "steam": ["steam"],
    "gimp": ["gimp"],
    "krita": ["krita"],
    "obs": ["obs"],
    "vlc": ["vlc"],
    "libreoffice": ["libreoffice"],
    "hesap makinesi": ["kcalc", "gnome-calculator", "galculator"],
    "sistem izleyici": ["plasma-systemmonitor", "gnome-system-monitor"],
    "telegram": ["telegram-desktop"],
    "thunderbird": ["thunderbird"],
}
APP_ALIASES: dict[str, str] = {
    "konsol": "terminal", "uçbirim": "terminal", "dolphin": "dosyalar", "dosya yöneticisi": "dosyalar",
    "files": "dosyalar", "file manager": "dosyalar", "code": "vscode", "vs code": "vscode",
    "visual studio code": "vscode", "google chrome": "chrome", "calculator": "hesap makinesi",
    "hesap makinası": "hesap makinesi", "obs studio": "obs", "system monitor": "sistem izleyici",
    "görev yöneticisi": "sistem izleyici",
    # common speech-recognition spellings of "Pear Desktop" (th-ch YouTube Music)
    "peer desktop": "pear desktop", "pir desktop": "pear desktop", "pr desktop": "pear desktop",
    "per desktop": "pear desktop", "peerdesktop": "pear desktop", "pear desktap": "pear desktop",
    "peer dextop": "pear desktop", "pr dextup": "pear desktop", "prdesktap": "pear desktop",
    "peerdextap": "pear desktop", "pear": "pear desktop", "peer": "pear desktop",
}

SITE_ALLOWLIST: dict[str, str] = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "claude": "https://claude.ai",
    "wikipedia": "https://tr.wikipedia.org",
    "vikipedi": "https://tr.wikipedia.org",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "reddit": "https://www.reddit.com",
    "haritalar": "https://maps.google.com",
    "google maps": "https://maps.google.com",
    "çeviri": "https://translate.google.com",
    "translate": "https://translate.google.com",
    "netflix": "https://www.netflix.com",
    "spotify web": "https://open.spotify.com",
}


def xdg_dir(name: str, fallback: str) -> Path:
    if shutil.which("xdg-user-dir"):
        try:
            out = subprocess.run(["xdg-user-dir", name], capture_output=True, text=True, timeout=2).stdout.strip()
            if out:
                return Path(out)
        except (OSError, subprocess.SubprocessError):
            pass
    return HOME / fallback


KNOWN_DIRS: dict[str, Callable[[], Path]] = {
    "masaüstü": lambda: xdg_dir("DESKTOP", "Desktop"),
    "desktop": lambda: xdg_dir("DESKTOP", "Desktop"),
    "indirilenler": lambda: xdg_dir("DOWNLOAD", "Downloads"),
    "downloads": lambda: xdg_dir("DOWNLOAD", "Downloads"),
    "belgeler": lambda: xdg_dir("DOCUMENTS", "Documents"),
    "documents": lambda: xdg_dir("DOCUMENTS", "Documents"),
    "resimler": lambda: xdg_dir("PICTURES", "Pictures"),
    "pictures": lambda: xdg_dir("PICTURES", "Pictures"),
    "müzik": lambda: xdg_dir("MUSIC", "Music"),
    "videolar": lambda: xdg_dir("VIDEOS", "Videos"),
    "ev": lambda: HOME,
    "home": lambda: HOME,
}


@dataclass
class ResolvedApp:
    label: str
    cmd: list[str]
    sensitive: bool = False
    desktop_id: str = ""


def resolve_app(name: str) -> ResolvedApp | None:
    """Find an installed application by (Turkish/English) name.

    1. curated aliases (e.g. "terminal" → Konsole) pick a preferred app;
    2. otherwise any installed desktop application (XDG .desktop entries, Flatpak, Snap) is matched.
    Apps are started through their desktop entry, never through a model-written command line."""
    key = tr_lower(name).strip().strip("'\"")
    key = APP_ALIASES.get(key, key)
    candidates = APP_ALLOWLIST.get(key, [])
    entries = [e for e in (_apps.CATALOG.find(exe) for exe in candidates) if e]
    running = [e for e in entries if _apps.is_running(e)]
    if running:  # "youtube music" while Pear Desktop is open → use Pear Desktop, not the other client
        e = running[0]
        return ResolvedApp(e.name, launch_desktop_entry(e), e.sensitive, e.desktop_id)
    for exe in candidates:
        entry = _apps.CATALOG.find(exe)
        if entry:
            return ResolvedApp(entry.name, launch_desktop_entry(entry), entry.sensitive, entry.desktop_id)
        path = shutil.which(exe)
        if path:
            return ResolvedApp(key, [path])
    entry = _apps.CATALOG.find(key)
    if entry:
        return ResolvedApp(entry.name, launch_desktop_entry(entry), entry.sensitive, entry.desktop_id)
    if candidates:
        return ResolvedApp(key, [])  # known app, just not installed
    return None


def resolve_user_path(raw: str) -> Path:
    raw = raw.strip()
    low = tr_lower(raw)
    if low in KNOWN_DIRS:
        return KNOWN_DIRS[low]()
    # "Desktop/x", "~/Masaüstü/x", "Downloads" … → the user's real XDG folders (e.g. ~/Masaüstü on Turkish systems)
    rel = raw[2:] if raw.startswith("~/") else raw
    if not os.path.isabs(rel):
        first, _, rest = rel.partition("/")
        key = tr_lower(first)
        if key in KNOWN_DIRS and key not in ("ev", "home"):
            base = KNOWN_DIRS[key]()
            return base / rest if rest else base
    p = Path(os.path.expanduser(raw))
    if not p.is_absolute():
        p = HOME / p
    return p


def known_folders_for_ai() -> str:
    names = {"masaüstü": "Masaüstü/Desktop", "indirilenler": "İndirilenler/Downloads", "belgeler": "Belgeler/Documents",
             "resimler": "Resimler/Pictures"}
    return ", ".join(f"{label} = {KNOWN_DIRS[k]()}" for k, label in names.items())


def _detached(cmd: list[str], extra_env: dict[str, str] | None = None) -> None:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("CLAUDE", "ANTHROPIC_", "VOLB_")) and k not in ("QT_QPA_PLATFORM",)}
    env.update(extra_env or {})
    kwargs: dict[str, Any] = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  env=env)
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x00000008  # DETACHED_PROCESS
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, **kwargs)  # noqa: S603 - cmd built from allowlist only


def _open_with_system(target: str) -> None:
    if sys.platform == "win32":
        os.startfile(target)  # type: ignore[attr-defined]  # noqa: S606
    elif shutil.which("xdg-open"):
        _detached(["xdg-open", target])
    else:
        webbrowser.open(target)


# ----------------------------------------------------------------------------- param schemas
class OpenUrlParams(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def _http_only(cls, v: str) -> str:
        v = v.strip()
        key = tr_lower(v)
        if key in SITE_ALLOWLIST:
            return SITE_ALLOWLIST[key]
        scheme = urlparse(v).scheme.lower()
        rest = v[len(scheme) + 1:] if scheme else ""
        if scheme and scheme not in ("http", "https") and not rest.split("/")[0].isdigit():
            raise ValueError("Sadece http/https adresleri açılabilir.")
        if "://" not in v:
            v = "https://" + v
        u = urlparse(v)
        if u.scheme not in ("http", "https") or not u.netloc:
            raise ValueError("Sadece http/https adresleri açılabilir.")
        return v


class WebSearchParams(BaseModel):
    query: str = Field(min_length=1, max_length=300)


class LaunchAppParams(BaseModel):
    app: str

    @field_validator("app")
    @classmethod
    def _allowed(cls, v: str) -> str:
        if resolve_app(v) is None:
            raise ValueError(f"'{v}' adında kurulu bir uygulama bulamadım.")
        return v


class PathParams(BaseModel):
    path: str = Field(min_length=1, max_length=500)


class SearchFilesParams(BaseModel):
    query: str = Field(min_length=1, max_length=100)
    root: str = "~"
    limit: int = Field(30, ge=1, le=200)


class StatsParams(BaseModel):
    focus: str | None = None


class ResearchParams(BaseModel):
    topic: str = Field(min_length=2, max_length=300)
    max_sources: int = Field(4, ge=1, le=8)


class EmptyParams(BaseModel):
    pass


class MediaParams(BaseModel):
    command: str = Field(pattern="^(play|pause|toggle|next|previous|stop|shuffle_on|shuffle_off|volume_up|"
                                 "volume_down|now_playing|system_volume_up|system_volume_down|system_mute)$")
    player: str = ""


async def _media_control(p: MediaParams) -> ActionResult:
    from . import media
    ok, msg = await asyncio.to_thread(media.control, p.command, p.player)
    return ActionResult(ok, msg)


class AppControlParams(BaseModel):
    app: str = Field(min_length=2, max_length=80)
    goal: str = Field(min_length=2, max_length=400)


class ScheduleParams(BaseModel):
    when: str = Field(description="ISO 8601 local datetime, e.g. 2026-11-06T09:00")
    text: str = Field(min_length=1, max_length=400)
    kind: str = Field("command", pattern="^(command|reminder)$")
    repeat: str = Field("", pattern="^(|hourly|daily|weekdays|weekly)$")

    @field_validator("when")
    @classmethod
    def _iso(cls, v: str) -> str:
        import datetime as _dt
        _dt.datetime.fromisoformat(v)
        return v


# ----------------------------------------------------------------------------- results / specs
@dataclass
class ActionResult:
    ok: bool
    message: str
    data: dict[str, Any] | None = None


Handler = Callable[[BaseModel], Awaitable[ActionResult]]


@dataclass
class ActionSpec:
    name: str
    description: str
    params: type[BaseModel]
    risk: Risk
    handler: Handler
    example: str = ""
    risk_fn: Callable[[Any], Risk] | None = None
    ai_risk: Risk | None = None   # minimum risk when the step was proposed by the AI (not typed by the user)

    def risk_for(self, params: BaseModel, origin: str = "user") -> Risk:
        """Per-call risk (e.g. launching a system-settings app needs approval)."""
        risk = max(self.risk, self.risk_fn(params)) if self.risk_fn else self.risk
        if origin == "ai" and self.ai_risk is not None:
            risk = max(risk, self.ai_risk)
        return risk


class ActionError(ValueError):
    pass


class ActionRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, ActionSpec] = {}

    def register(self, spec: ActionSpec) -> None:
        self._specs[spec.name] = spec

    def get(self, name: str) -> ActionSpec:
        if name not in self._specs:
            raise ActionError(f"Bilinmeyen/izinsiz eylem: {name}")
        return self._specs[name]

    def names(self) -> list[str]:
        return list(self._specs)

    def validate(self, name: str, params: dict[str, Any]) -> tuple[ActionSpec, BaseModel]:
        spec = self.get(name)
        try:
            model = spec.params.model_validate(params or {})
        except ValidationError as exc:
            msgs = "; ".join(e["msg"] for e in exc.errors())
            raise ActionError(f"{name}: geçersiz parametre — {msgs}") from exc
        return spec, model

    def describe_for_ai(self) -> str:
        lines = []
        for s in self._specs.values():
            fields = ", ".join(f"{k}: {v.annotation.__name__ if hasattr(v.annotation, '__name__') else v.annotation}"
                               for k, v in s.params.model_fields.items())
            lines.append(f"- {s.name}({fields}) — {s.description} [risk: {s.risk.label}]")
        return "\n".join(lines)


# ----------------------------------------------------------------------------- handlers
async def _open_url(p: OpenUrlParams) -> ActionResult:
    _open_with_system(p.url)
    return ActionResult(True, f"{urlparse(p.url).netloc} açıldı.", {"url": p.url})


async def _web_search(p: WebSearchParams) -> ActionResult:
    url = f"https://www.google.com/search?q={quote_plus(p.query)}"
    _open_with_system(url)
    return ActionResult(True, f"'{p.query}' için arama açıldı.", {"url": url})


async def _launch_app(p: LaunchAppParams) -> ActionResult:
    app = resolve_app(p.app)
    assert app
    if not app.cmd:
        return ActionResult(False, f"{app.label} bu sistemde kurulu görünmüyor.")
    entry = _apps.CATALOG.get(app.desktop_id) if app.desktop_id else None
    if entry is not None and sys.platform.startswith("linux"):
        from . import ui_control
        argv, env = ui_control.launch_command(entry)   # exposes the UI tree so VOLB can click inside later
        if argv:
            _detached(argv, env)
            return ActionResult(True, f"{app.label} başlatılıyor.", {"app": app.label, "desktop_id": app.desktop_id})
    _detached(app.cmd)
    return ActionResult(True, f"{app.label} başlatılıyor.", {"app": app.label, "desktop_id": app.desktop_id})


def _launch_risk(p: LaunchAppParams) -> Risk:
    app = resolve_app(p.app)
    return Risk.SENSITIVE if app and app.sensitive else Risk.SAFE


async def _open_directory(p: PathParams) -> ActionResult:
    path = resolve_user_path(p.path)
    if not path.is_dir():
        return ActionResult(False, f"Klasör bulunamadı: {path}")
    _open_with_system(str(path))
    return ActionResult(True, f"{path} açıldı.", {"path": str(path)})


async def _create_folder(p: PathParams) -> ActionResult:
    path = resolve_user_path(p.path)
    if not is_within(path, HOME):
        return ActionResult(False, "Sadece ev dizini altında klasör oluşturabilirim.")
    if path.exists():
        return ActionResult(False, f"Zaten var: {path}")
    path.mkdir(parents=True)
    return ActionResult(True, f"Klasör oluşturuldu: {path}", {"path": str(path)})


async def _search_files(p: SearchFilesParams) -> ActionResult:
    root = resolve_user_path(p.root)
    needle = tr_lower(p.query)

    def _walk() -> list[str]:
        hits: list[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in ("node_modules", "__pycache__",
                                                                                    ".venv", "venv")]
            for name in filenames + dirnames:
                if needle in tr_lower(name):
                    hits.append(os.path.join(dirpath, name))
                    if len(hits) >= p.limit:
                        return hits
        return hits

    hits = await asyncio.to_thread(_walk)
    msg = f"'{p.query}' için {len(hits)} sonuç bulundu." if hits else f"'{p.query}' ile eşleşen dosya yok."
    return ActionResult(True, msg, {"files": hits})


TEXT_EXT = {".txt", ".md", ".py", ".json", ".csv", ".log", ".ini", ".toml", ".yaml", ".yml", ".qml", ".js",
            ".ts", ".html", ".css", ".rs", ".c", ".cpp", ".h", ".java", ".sh", ".xml", ".srt", ".tex"}


async def _read_document(p: PathParams) -> ActionResult:
    path = resolve_user_path(p.path)
    if not path.is_file():
        return ActionResult(False, f"Dosya bulunamadı: {path}")
    if is_sensitive_path(path):
        return ActionResult(False, "Bu dosya hassas kabul ediliyor (anahtarlar/parolalar); okunmadı.")
    if path.suffix.lower() == ".pdf" and shutil.which("pdftotext"):
        proc = await asyncio.create_subprocess_exec("pdftotext", "-l", "30", str(path), "-",
                                                    stdout=asyncio.subprocess.PIPE)
        out, _ = await proc.communicate()
        text = out.decode(errors="replace")
    elif path.suffix.lower() in TEXT_EXT or path.stat().st_size < 200_000:
        text = path.read_text(encoding="utf-8", errors="replace")
    else:
        return ActionResult(False, "Bu dosya türünü okuyamıyorum.")
    text = text[:60_000]
    return ActionResult(True, f"{path.name} okundu ({len(text)} karakter).", {"path": str(path), "text": text})


async def _system_stats(p: StatsParams) -> ActionResult:
    s = read_stats()
    focus = (p.focus or "").lower() or None
    return ActionResult(True, s.describe_tr(focus), {"stats": s.as_dict(), "top": top_processes()})


async def _screenshot(p: EmptyParams) -> ActionResult:
    out_dir = DATA_DIR / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"ekran_{dt.datetime.now():%Y%m%d_%H%M%S}.png"
    for cmd in (["spectacle", "-b", "-n", "-f", "-o", str(path)], ["grim", str(path)],
                ["gnome-screenshot", "-f", str(path)], ["scrot", str(path)]):
        if shutil.which(cmd[0]):
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL,
                                                        stderr=asyncio.subprocess.DEVNULL)
            await asyncio.wait_for(proc.wait(), 20)
            if path.exists():
                return ActionResult(True, f"Ekran görüntüsü kaydedildi: {path.name}", {"path": str(path)})
    return ActionResult(False, "Ekran görüntüsü aracı bulunamadı (spectacle/grim).")


async def _current_time(p: EmptyParams) -> ActionResult:
    now = dt.datetime.now()
    days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    return ActionResult(True, f"Saat {now:%H:%M}, {now:%d.%m.%Y} {days[now.weekday()]}.")


def build_default_registry(research_handler: Handler | None = None,
                           extra: list[ActionSpec] | None = None) -> ActionRegistry:
    reg = ActionRegistry()
    reg.register(ActionSpec("open_url", "Varsayılan tarayıcıda bir web sitesi aç", OpenUrlParams, Risk.SAFE, _open_url))
    reg.register(ActionSpec("web_search", "Tarayıcıda Google araması aç", WebSearchParams, Risk.SAFE, _web_search))
    reg.register(ActionSpec("launch_app", "Bilgisayarda kurulu herhangi bir uygulamayı adıyla başlat "
                            "(sistem/ayar araçları onay ister)", LaunchAppParams, Risk.SAFE, _launch_app,
                            risk_fn=_launch_risk))
    reg.register(ActionSpec("open_directory", "Dosya yöneticisinde klasör aç", PathParams, Risk.SAFE, _open_directory))
    reg.register(ActionSpec("create_folder", "Ev dizini altında yeni klasör oluştur", PathParams, Risk.SENSITIVE,
                            _create_folder))
    reg.register(ActionSpec("search_files", "Ev dizininde dosya adına göre ara", SearchFilesParams, Risk.SAFE,
                            _search_files))
    reg.register(ActionSpec("read_document", "Bir belgenin metnini oku (içerik yapay zekâya gider)", PathParams,
                            Risk.SENSITIVE, _read_document))
    reg.register(ActionSpec("system_stats", "CPU/RAM/disk kullanımını göster (focus: cpu|ram|disk)", StatsParams,
                            Risk.SAFE, _system_stats))
    reg.register(ActionSpec("screenshot", "Ekran görüntüsü al", EmptyParams, Risk.SENSITIVE, _screenshot))
    reg.register(ActionSpec("current_time", "Saati ve tarihi söyle", EmptyParams, Risk.SAFE, _current_time))
    reg.register(ActionSpec("media_control", "Müzik/medya oynatıcısını anında kontrol et (MPRIS): play, pause, toggle, "
                            "next, previous, stop, shuffle_on, shuffle_off, volume_up, volume_down, now_playing, system_volume_up, "
                            "system_volume_down, system_mute. "
                            "player: isteğe bağlı uygulama adı. Basit oynat/durdur/geç işlerinde app_control yerine "
                            "BUNU kullan", MediaParams, Risk.SAFE, _media_control))
    if research_handler:
        reg.register(ActionSpec("research", "Web'de kaynaklı araştırma yap ve rapor hazırla", ResearchParams,
                                Risk.SAFE, research_handler))
    for spec in extra or []:
        reg.register(spec)
    return reg
