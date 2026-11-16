"""YAPAY VOLB — personal AI desktop assistant. Entry point."""
from __future__ import annotations

import argparse
import logging
import os
import signal
import sys

from app.core.config import APP_NAME, APP_VERSION, UI_DIR, ensure_dirs
from app.core.logging_setup import setup_logging


def main() -> int:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--windowed", action="store_true", help="Start in a window instead of maximized")
    parser.add_argument("--screenshot", metavar="PNG", help="Render, save a screenshot after a delay and quit")
    parser.add_argument("--state", default="", help="Force a character state (idle/listening/thinking/...)")
    parser.add_argument("--page", type=int, default=0, help="Start page index")
    parser.add_argument("--send", metavar="TEXT", help="Send a command shortly after start (smoke testing)")
    parser.add_argument("--delay", type=int, default=3500, help="Screenshot delay in ms")
    parser.add_argument("--mute", action="store_true", help="Do not speak replies (testing)")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    ensure_dirs()
    setup_logging(logging.DEBUG if args.debug else logging.INFO)
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

    from PySide6.QtCore import QLockFile, QTimer, QUrl
    from PySide6.QtGui import QFont, QGuiApplication, QIcon
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuick import QQuickWindow  # noqa: F401 - root window maps to QQuickWindow

    from app.services.bridge import Backend
    from app.services.chat_model import ChatModel

    app = QGuiApplication(sys.argv)

    # Only one VOLB per data folder: two instances would answer and speak on top of each other.
    from app.core.config import DATA_DIR
    lock = QLockFile(str(DATA_DIR / "volb.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(200):
        logging.error("YAPAY VOLB zaten çalışıyor (%s). İkinci kopya açılmadı.", DATA_DIR)
        return 2
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("VOLB")
    app.setDesktopFileName("yapay-volb")
    app.setWindowIcon(QIcon(str(UI_DIR / "assets" / "volb_icon.svg")))
    app.setFont(QFont("Fira Sans", 10))

    chat = ChatModel()
    backend = Backend(chat)
    if args.state:
        backend.previewState(args.state)
    if args.mute:
        backend.cfg.speak_responses = False
        backend.orchestrator.speak_responses = False

    engine = QQmlApplicationEngine()
    ctx = engine.rootContext()
    ctx.setContextProperty("backend", backend)
    ctx.setContextProperty("chatModel", chat)
    ctx.setContextProperty("startWindowed", args.windowed or bool(args.screenshot))
    ctx.setContextProperty("startPage", args.page)
    engine.load(QUrl.fromLocalFile(str(UI_DIR / "main.qml")))
    if not engine.rootObjects():
        logging.error("QML yüklenemedi.")
        backend.shutdown()
        return 1

    if args.send:
        QTimer.singleShot(900, lambda: backend.sendText(args.send))

    if args.screenshot:
        window = engine.rootObjects()[0]

        def grab() -> None:
            window.grabWindow().save(args.screenshot)
            app.quit()
        QTimer.singleShot(args.delay, grab)

    app.aboutToQuit.connect(backend.shutdown)
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    keepalive = QTimer()  # lets Python handle Ctrl+C
    keepalive.start(250)
    keepalive.timeout.connect(lambda: None)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
