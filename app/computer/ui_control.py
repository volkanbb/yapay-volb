"""In-app control through the accessibility tree (AT-SPI on Linux).

Works on Wayland because nothing is clicked by screen coordinates: VOLB reads the app's accessibility
tree (buttons, links, list items, text fields with their names) and invokes their accessibility actions.
Electron/Chromium apps only expose their page content when started with `--force-renderer-accessibility`;
`launch_command()` adds that flag when VOLB starts such an app itself.
"""
from __future__ import annotations

import logging
import os
import re
import shlex
import shutil
import signal
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .apps import AppEntry

log = logging.getLogger(__name__)

INTERACTIVE = {"button", "push button", "toggle button", "menu button", "link", "list item", "menu item", "check menu item",
               "radio menu item", "page tab", "check box", "radio button", "combo box", "entry", "text",
               "password text", "spin button", "tree item", "table cell", "menu", "slider", "search box"}
CONTEXT_ROLES = {"heading"}
ACTION_PREFERENCE = ("click", "press", "activate", "jump", "toggle", "select", "open", "expand or contract")
DANGEROUS = re.compile(
    r"\b(sil|silin|kaldır|delete|remove|trash|çöp|satın al|buy|purchase|order|sipariş|öde|pay|checkout|"
    r"gönder|send|paylaş|share|yayınla|publish|post|tweet|abonelikten çık|unsubscribe|aboneliği iptal|"
    r"çıkış yap|log ?out|sign ?out|oturumu kapat|hesabı|account|format|reset|sıfırla|uninstall|"
    r"kaldırmak|onayla|confirm|transfer|bağış|donate|engelle|block|report|şikayet)\b", re.I)
FIELD_CODES = re.compile(r"\s%[fFuUdDnNickvm]\b")


def available() -> tuple[bool, str]:
    if not sys.platform.startswith("linux"):
        return False, "Uygulama içi kontrol şimdilik yalnızca Linux'ta (AT-SPI) destekleniyor."
    try:
        import gi
        gi.require_version("Atspi", "2.0")
        from gi.repository import Atspi  # noqa: F401
    except (ImportError, ValueError) as exc:
        return False, f"AT-SPI kullanılamıyor (python-gobject + at-spi2-core gerekli): {exc}"
    return True, ""


def _atspi():
    import gi
    gi.require_version("Atspi", "2.0")
    from gi.repository import Atspi
    return Atspi


def ensure_accessibility_bus() -> bool:
    """Turn on the session accessibility switch so toolkits expose their UI (org.a11y.Status.IsEnabled)."""
    try:
        from gi.repository import Gio, GLib
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        current = bus.call_sync("org.a11y.Bus", "/org/a11y/bus", "org.freedesktop.DBus.Properties", "Get",
                                GLib.Variant("(ss)", ("org.a11y.Status", "IsEnabled")), None,
                                Gio.DBusCallFlags.NONE, 2000, None).unpack()[0]
        if not current:
            bus.call_sync("org.a11y.Bus", "/org/a11y/bus", "org.freedesktop.DBus.Properties", "Set",
                          GLib.Variant("(ssv)", ("org.a11y.Status", "IsEnabled", GLib.Variant("b", True))), None,
                          Gio.DBusCallFlags.NONE, 2000, None)
            log.info("accessibility bus enabled")
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("could not enable accessibility bus: %s", exc)
        return False


# ----------------------------------------------------------------------------- launching
def _exec_argv(entry: AppEntry) -> list[str]:
    line = FIELD_CODES.sub("", " " + entry.exec_line).strip()
    try:
        argv = shlex.split(line)
    except ValueError:
        return []
    while argv and (argv[0] == "env" or "=" in argv[0]):
        argv.pop(0)
    return argv


def is_chromium_based(entry: AppEntry) -> bool:
    argv = _exec_argv(entry)
    if not argv:
        return False
    exe = shutil.which(argv[0]) or argv[0]
    path = Path(exe)
    try:
        real = path.resolve()
        if any(k in str(real).lower() for k in ("electron", "chrom", "brave", "vivaldi", "opera", "edge")):
            return True
        head = real.read_bytes()[:8192] if real.stat().st_size < 2_000_000 else b""
        if b"electron" in head.lower() or b"app.asar" in head:
            return True
        for d in (real.parent, real.parent / "resources"):
            if (d / "app.asar").exists() or (d / "resources" / "app.asar").exists() or (d / "chrome_100_percent.pak").exists():
                return True
    except OSError:
        pass
    return False


def launch_command(entry: AppEntry) -> tuple[list[str], dict[str, str]]:
    """argv + extra env to start an app with its accessibility tree exposed.
    The argv comes from the system .desktop file (never from model text)."""
    env = {"ACCESSIBILITY_ENABLED": "1", "QT_LINUX_ACCESSIBILITY_ALWAYS_ON": "1", "GTK_A11Y": "atspi"}
    argv = _exec_argv(entry)
    if argv and is_chromium_based(entry):
        return argv + ["--force-renderer-accessibility"], env
    if shutil.which("gtk-launch"):
        return ["gtk-launch", entry.desktop_id], env
    return argv, env


# ----------------------------------------------------------------------------- tree access
@dataclass
class UIElement:
    id: int
    role: str
    name: str
    states: list[str] = field(default_factory=list)
    obj: Any = None

    def line(self) -> str:
        st = f" ({', '.join(self.states)})" if self.states else ""
        return f"[{self.id}] {self.role}: {self.name}{st}"


def _cmdline(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="ignore").lower()
    except OSError:
        return ""


def app_keys(entry: AppEntry | None, name: str) -> list[str]:
    keys = [name.lower()]
    if entry:
        argv = _exec_argv(entry)
        if argv:
            keys.append(Path(argv[0]).name.lower())
        keys += [entry.name.lower(), entry.desktop_id.lower().rsplit(".", 1)[-1]]
    return [k for k in dict.fromkeys(keys) if len(k) >= 3]


def find_app(entry: AppEntry | None, name: str):
    Atspi = _atspi()
    desktop = Atspi.get_desktop(0)
    keys = app_keys(entry, name)
    best = None
    for i in range(desktop.get_child_count()):
        acc = desktop.get_child_at_index(i)
        if acc is None:
            continue
        try:
            pid = acc.get_process_id()
            app_name = (acc.get_name() or "").lower()
            titles = " ".join((acc.get_child_at_index(j).get_name() or "").lower()
                              for j in range(min(acc.get_child_count(), 4)) if acc.get_child_at_index(j))
        except Exception:  # noqa: BLE001
            continue
        if pid == os.getpid():
            continue
        hay = f"{app_name} {titles} {_cmdline(pid)}"
        if any(k in hay for k in keys):
            if best is None or acc.get_child_count() > best.get_child_count():
                best = acc
    return best


def app_pids(entry: AppEntry | None, name: str) -> list[int]:
    keys = app_keys(entry, name)
    pids = []
    for p in Path("/proc").iterdir():
        if p.name.isdigit() and int(p.name) != os.getpid():
            cmd = _cmdline(int(p.name))
            if cmd and "--type=" not in cmd and any(k in cmd for k in keys[1:] or keys):
                pids.append(int(p.name))
    return pids


def terminate(pids: list[int], timeout: float = 15.0) -> None:
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    end = time.monotonic() + timeout
    while time.monotonic() < end and any(Path(f"/proc/{p}").exists() for p in pids):
        time.sleep(0.3)


def snapshot(app, limit: int = 140) -> list[UIElement]:
    Atspi = _atspi()
    out: list[UIElement] = []
    seen: set[tuple[str, str]] = set()

    def walk(node, depth: int) -> None:
        if node is None or depth > 90 or len(out) >= limit:
            return
        try:
            role = node.get_role_name()
            name = re.sub(r"\s+", " ", (node.get_name() or "")).strip()
            ss = node.get_state_set()
            showing = ss.contains(Atspi.StateType.SHOWING)
        except Exception:  # noqa: BLE001
            return
        if depth > 1 and not showing:
            return
        if role in INTERACTIVE or role in CONTEXT_ROLES:
            if not name and role in ("entry", "text", "search box"):
                name = "(boş metin alanı)"
            key = (role, name)
            if name and key not in seen:
                seen.add(key)
                states = [s for s, t in (("seçili", Atspi.StateType.SELECTED), ("işaretli", Atspi.StateType.CHECKED),
                                         ("odakta", Atspi.StateType.FOCUSED), ("basılı", Atspi.StateType.PRESSED))
                          if ss.contains(t)]
                if not ss.contains(Atspi.StateType.ENABLED) and role != "heading":
                    states.append("devre dışı")
                out.append(UIElement(len(out) + 1, role, name[:120], states, node))
        try:
            n = node.get_child_count()
        except Exception:  # noqa: BLE001
            return
        for i in range(n):
            try:
                walk(node.get_child_at_index(i), depth + 1)
            except Exception:  # noqa: BLE001
                continue

    walk(app, 0)
    return out


def window_title(app) -> str:
    if app is None:
        return ""
    try:
        for i in range(app.get_child_count()):
            child = app.get_child_at_index(i)
            if child is not None and child.get_name():
                return child.get_name()
    except Exception:  # noqa: BLE001
        pass
    return ""


class StaleElement(RuntimeError):
    """The UI changed and this accessible object no longer exists (common in Chromium/Electron)."""


def _is_stale(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "does not exist" in msg or "unknownobject" in msg or "no such object" in msg or "disposed" in msg


def _do_click(obj) -> bool:
    action = obj.get_action_iface()
    if action is not None:
        n = action.get_n_actions()
        names = [(action.get_action_name(i) or "").lower() for i in range(n)]
        for pref in ACTION_PREFERENCE:
            if pref in names:
                return bool(action.do_action(names.index(pref)))
        if n:
            return bool(action.do_action(0))
    comp = obj.get_component_iface()
    return bool(comp.grab_focus()) if comp is not None else False


def click(el: UIElement) -> bool:
    """Click via the element's accessibility action. Raises StaleElement if the UI re-rendered it."""
    try:
        return _do_click(el.obj)
    except Exception as exc:  # noqa: BLE001 - GLib.GError from D-Bus
        if _is_stale(exc):
            raise StaleElement(el.name) from exc
        log.warning("click failed on %s: %s", el.name, exc)
        return False


def refind(app, el: UIElement) -> UIElement | None:
    """Locate the same element (role + name) in a fresh snapshot after the UI re-rendered."""
    fresh = snapshot(app, 400)
    same = [e for e in fresh if e.role == el.role and e.name == el.name]
    if not same:
        same = [e for e in fresh if e.name == el.name]
    return same[0] if same else None


def type_text(el: UIElement, text: str, submit: bool = False) -> bool:
    Atspi = _atspi()
    obj = el.obj
    if el.role == "password text":
        raise PermissionError("Parola alanlarına yazmam.")
    try:
        comp = obj.get_component_iface()
        if comp is not None:
            comp.grab_focus()
        editable = obj.get_editable_text_iface()
        ok = bool(editable and editable.set_text_contents(text))
    except Exception as exc:  # noqa: BLE001
        if _is_stale(exc):
            raise StaleElement(el.name) from exc
        log.warning("type failed: %s", exc)
        ok = False
    if ok and submit:
        try:
            Atspi.generate_keyboard_event(0xFF0D, None, Atspi.KeySynthType.SYM)  # Return
        except Exception:  # noqa: BLE001
            pass
    return ok


def is_dangerous(el: UIElement) -> bool:
    return bool(DANGEROUS.search(el.name))
