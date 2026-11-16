"""Render ui/CharacterGallery.qml (or another QML file) to a PNG. Usage: render_gallery.py [out.png] [qml] [delay_ms]"""
import sys
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow  # noqa: F401 - ensures root window maps to QQuickWindow

root = Path(__file__).resolve().parents[1]
out = sys.argv[1] if len(sys.argv) > 1 else str(root / "data" / "gallery.png")
qml = sys.argv[2] if len(sys.argv) > 2 else str(root / "ui" / "CharacterGallery.qml")
delay = int(sys.argv[3]) if len(sys.argv) > 3 else 2500
app = QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
engine.load(QUrl.fromLocalFile(qml))
if not engine.rootObjects():
    sys.exit(1)
win = engine.rootObjects()[0]
QTimer.singleShot(delay, lambda: (win.grabWindow().save(out), print("saved", out), app.quit()))
sys.exit(app.exec())
