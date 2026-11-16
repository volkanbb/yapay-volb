"""Installed-application catalog built from XDG .desktop entries (incl. Flatpak / Snap exports).

VOLB can launch *any* installed GUI application, but only through its registered desktop entry
(`gtk-launch <desktop-id>`), never by executing a command string. System/admin tools are flagged so
the orchestrator asks for approval before starting them.
"""
from __future__ import annotations

import configparser
import difflib
import os
import re
import shutil
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path


def _norm(text: str) -> str:
    text = text.replace("I", "ı").replace("İ", "i").lower()
    text = re.sub(r"[^\w\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


SENSITIVE_CATEGORIES = {"settings", "packagemanager", "security", "filesystem", "hardwaresettings",
                        "desktopsettings"}
ROOT_MARKERS = ("pkexec", "sudo ", "kdesu", "gksu", "su -c", "kdesudo")


@dataclass
class AppEntry:
    desktop_id: str
    name: str
    path: str
    generic: str = ""
    keywords: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    exec_line: str = ""

    @property
    def sensitive(self) -> bool:
        cats = {c.lower() for c in self.categories}
        return bool(cats & SENSITIVE_CATEGORIES) or any(m in self.exec_line for m in ROOT_MARKERS)

    def search_terms(self) -> list[tuple[str, float]]:
        """(term, weight): the visible name wins over generic names and desktop-id stems."""
        stem = self.desktop_id.rsplit(".", 1)[-1] if self.desktop_id.count(".") >= 2 else self.desktop_id
        terms = [(_norm(self.name), 1.0), (_norm(self.generic), 0.9), (_norm(stem.replace("-", " ")), 0.85)]
        return [(t, w) for t, w in terms if t]


def application_dirs() -> list[Path]:
    home = Path.home()
    data_home = Path(os.environ.get("XDG_DATA_HOME") or home / ".local/share")
    dirs = [data_home / "applications"]
    for d in (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":"):
        if d:
            dirs.append(Path(d) / "applications")
    dirs += [home / ".local/share/flatpak/exports/share/applications",
             Path("/var/lib/flatpak/exports/share/applications"),
             Path("/var/lib/snapd/desktop/applications")]
    seen, out = set(), []
    for d in dirs:
        r = d.resolve() if d.exists() else d
        if r not in seen and d.is_dir():
            seen.add(r)
            out.append(d)
    return out


def _localized(sec: configparser.SectionProxy, key: str) -> str:
    for k in (f"{key}[tr_TR]", f"{key}[tr]", key):
        if sec.get(k):
            return sec.get(k, "").strip()
    return ""


def parse_desktop_file(path: Path, desktop_id: str) -> AppEntry | None:
    cp = configparser.RawConfigParser(strict=False, interpolation=None)
    cp.optionxform = str  # keep key case (Name[tr])
    try:
        cp.read(path, encoding="utf-8")
    except (configparser.Error, UnicodeDecodeError, OSError):
        return None
    if "Desktop Entry" not in cp:
        return None
    sec = cp["Desktop Entry"]
    if sec.get("Type", "") != "Application":
        return None
    if sec.get("NoDisplay", "").lower() == "true" or sec.get("Hidden", "").lower() == "true":
        return None
    desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "")
    only = sec.get("OnlyShowIn", "")
    if only and desktop_env and not any(d in only.split(";") for d in desktop_env.split(":")):
        return None
    name = _localized(sec, "Name")
    if not name:
        return None
    english = sec.get("Name", "").strip()
    keywords = [k for k in (_localized(sec, "Keywords") + ";" + sec.get("Keywords", "")).split(";") if k]
    if english and english != name:
        keywords.append(english)
    return AppEntry(desktop_id=desktop_id, name=name, path=str(path), generic=_localized(sec, "GenericName"),
                    keywords=keywords, categories=[c for c in sec.get("Categories", "").split(";") if c],
                    exec_line=sec.get("Exec", ""))


class AppCatalog:
    TTL = 60.0

    def __init__(self, dirs: list[Path] | None = None) -> None:
        self._dirs = dirs
        self._apps: dict[str, AppEntry] = {}
        self._stamp = 0.0
        self._lock = threading.Lock()

    def apps(self) -> list[AppEntry]:
        with self._lock:
            if time.monotonic() - self._stamp > self.TTL or not self._apps:
                self._scan()
            return list(self._apps.values())

    def _scan(self) -> None:
        apps: dict[str, AppEntry] = {}
        for base in self._dirs or application_dirs():
            for path in sorted(base.rglob("*.desktop")):
                desktop_id = str(path.relative_to(base))[: -len(".desktop")].replace("/", "-")
                if desktop_id in apps:  # earlier dirs (user) override later ones (system)
                    continue
                entry = parse_desktop_file(path, desktop_id)
                if entry:
                    apps[desktop_id] = entry
        self._apps = apps
        self._stamp = time.monotonic()

    def get(self, desktop_id: str) -> AppEntry | None:
        return next((a for a in self.apps() if a.desktop_id == desktop_id), None)

    def find(self, query: str) -> AppEntry | None:
        ranked = self.rank(query)
        if not ranked:
            return None
        top_score = ranked[0][0]
        # Several apps match about equally well (e.g. two YouTube Music clients) → prefer the one already running.
        close = [a for sc, a in ranked if sc >= top_score - 15]
        if len(close) > 1:
            running = [a for a in close if is_running(a)]
            if running:
                return running[0]
        return ranked[0][1]

    def rank(self, query: str) -> list[tuple[float, AppEntry]]:
        q = _norm(query)
        if len(q) < 2:
            return []
        scored: list[tuple[float, AppEntry]] = []
        q_tokens = set(q.split())
        for app in self.apps():
            score = 0.0
            for term, weight in app.search_terms():
                t_tokens = set(term.split())
                if term == q:
                    s_ = 100.0
                elif term.startswith(q):
                    s_ = 90 - min(len(term) - len(q), 20) * 0.2
                elif q_tokens <= t_tokens:
                    s_ = 80.0 - (len(t_tokens) - len(q_tokens))
                else:
                    ratio = difflib.SequenceMatcher(None, q, term).ratio()
                    s_ = 70 * ratio if ratio >= 0.8 else 0.0
                score = max(score, s_ * weight)
            if score < 60 and any(_norm(k) == q or q in _norm(k) for k in app.keywords):
                score = max(score, 62)
            if score >= 55:
                scored.append((score, app))
        scored.sort(key=lambda x: -x[0])
        return scored

    def names_for_ai(self, limit: int = 220) -> str:
        names = sorted({a.name for a in self.apps()}, key=str.lower)
        return ", ".join(names[:limit])


def _exec_binary(app: AppEntry) -> str:
    import shlex
    try:
        argv = [a for a in shlex.split(app.exec_line) if not a.startswith("%")]
    except ValueError:
        return ""
    while argv and (argv[0] == "env" or "=" in argv[0]):
        argv.pop(0)
    return os.path.basename(argv[0]).lower() if argv else ""


def is_running(app: AppEntry) -> bool:
    """True if a process of this app is alive (matched on its Exec binary / desktop-id stem)."""
    keys = {k for k in (_exec_binary(app), app.desktop_id.rsplit(".", 1)[-1].lower()) if len(k) >= 3}
    if not keys or not Path("/proc").exists():
        return False
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            cmd = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="ignore").lower()
        except OSError:
            continue
        if cmd and "--type=" not in cmd and any(k in cmd for k in keys):
            return True
    return False


def launch_desktop_entry(app: AppEntry) -> list[str]:
    """Command used to start an app through its registered desktop entry (no model text involved)."""
    if shutil.which("gtk-launch"):
        return ["gtk-launch", app.desktop_id]
    if shutil.which("gio"):
        return ["gio", "launch", app.path]
    if shutil.which("kioclient"):
        return ["kioclient", "exec", app.path]
    raise RuntimeError("gtk-launch/gio/kioclient bulunamadı")


CATALOG = AppCatalog()
