"""Keep the computer from going to sleep *by itself* while VOLB needs it (scheduled tasks).

Uses the desktop's standard inhibit API (org.freedesktop.PowerManagement.Inhibit — KDE PowerDevil, also
GNOME/XFCE via portals), the same mechanism video players use:
* only *automatic* idle sleep is blocked — choosing Sleep from the menu or closing the lid still works;
* the inhibition is tied to VOLB's D-Bus connection, so it disappears automatically if VOLB exits or crashes.
Falls back to a logind "idle" inhibitor (fd based, also released when the process dies).
"""
from __future__ import annotations

import logging
import os
import sys

log = logging.getLogger(__name__)
APP = "YAPAY VOLB"


class SleepInhibitor:
    def __init__(self) -> None:
        self._bus = None
        self._cookie: int | None = None
        self._fd: int | None = None
        self.reason = ""

    @property
    def active(self) -> bool:
        return self._cookie is not None or self._fd is not None

    def _session(self):
        if self._bus is None:
            from gi.repository import Gio
            # private connection: if VOLB dies the bus drops it and the inhibition is released
            addr = Gio.dbus_address_get_for_bus_sync(Gio.BusType.SESSION, None)
            self._bus = Gio.DBusConnection.new_for_address_sync(
                addr, Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,
                None, None)
        return self._bus

    def inhibit(self, reason: str) -> bool:
        if not sys.platform.startswith("linux"):
            return False
        if self.active:
            if reason != self.reason:
                self.release()
            else:
                return True
        from gi.repository import Gio, GLib
        try:
            res = self._session().call_sync(
                "org.freedesktop.PowerManagement", "/org/freedesktop/PowerManagement/Inhibit",
                "org.freedesktop.PowerManagement.Inhibit", "Inhibit", GLib.Variant("(ss)", (APP, reason)),
                GLib.VariantType("(u)"), Gio.DBusCallFlags.NONE, 3000, None)
            self._cookie = res.unpack()[0]
            self.reason = reason
            log.info("sleep inhibited (PowerManagement cookie %s): %s", self._cookie, reason)
            return True
        except Exception as exc:  # noqa: BLE001
            log.info("PowerManagement inhibit unavailable (%s), trying logind", exc)
        try:
            sysbus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
            res, fds = sysbus.call_with_unix_fd_list_sync(
                "org.freedesktop.login1", "/org/freedesktop/login1", "org.freedesktop.login1.Manager", "Inhibit",
                GLib.Variant("(ssss)", ("idle", APP, reason, "block")), GLib.VariantType("(h)"),
                Gio.DBusCallFlags.NONE, 3000, None, None)
            self._fd = fds.get(res.unpack()[0])
            self.reason = reason
            log.info("sleep inhibited (logind idle fd %s): %s", self._fd, reason)
            return True
        except Exception as exc:  # noqa: BLE001
            log.warning("could not inhibit sleep: %s", exc)
            return False

    def release(self) -> None:
        if self._cookie is not None:
            from gi.repository import Gio, GLib
            try:
                self._session().call_sync(
                    "org.freedesktop.PowerManagement", "/org/freedesktop/PowerManagement/Inhibit",
                    "org.freedesktop.PowerManagement.Inhibit", "UnInhibit", GLib.Variant("(u)", (self._cookie,)),
                    None, Gio.DBusCallFlags.NONE, 3000, None)
            except Exception as exc:  # noqa: BLE001
                log.warning("UnInhibit failed: %s", exc)
            log.info("sleep inhibition released")
            self._cookie = None
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        self.reason = ""


def desired_reason(mode: str, next_runs: list[float], now: float, window_s: float = 1800) -> str:
    """Why sleep should be blocked right now ("" = don't block).
    mode: off | always (while VOLB runs) | schedules (only when a task is due within `window_s`)."""
    if mode == "always":
        return "VOLB açık — zamanlanmış görevler için uyku engellendi"
    if mode == "schedules":
        soon = [t for t in next_runs if now - 60 <= t <= now + window_s]
        if soon:
            return "Yaklaşan zamanlanmış görev var"
    return ""
