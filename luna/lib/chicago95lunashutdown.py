"""Luna logoff/shutdown status screen, sharing the greeter's vector wordmark and backdrop."""

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtQuickWidgets import QQuickWidget

TEXT = "Windows is shutting down..."


def status_source():
    candidates = (
        Path(__file__).resolve().parent.parent / "splash/LunaStatus.qml",
        Path.home() / ".local/share/chicago95/luna/splash/LunaStatus.qml",
        Path.home()
        / ".local/share/plasma/look-and-feel/chicago95.splashscreen/contents/splash/luna/splash/LunaStatus.qml",
    )
    return next(path for path in candidates if path.is_file())


class ShuttingDownScreen(QQuickWidget):
    def __init__(self, geometry, hold_until_input):
        super().__init__()
        self.hold_until_input = hold_until_input
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setCursor(Qt.ArrowCursor)
        self.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.setGeometry(geometry)
        self.setSource(QUrl.fromLocalFile(str(status_source())))
        if self.rootObject() is None:
            raise RuntimeError("Could not load the Luna session status screen")

    def set_status(self, text):
        self.rootObject().setProperty("statusText", text)

    def keyPressEvent(self, event):
        if self.hold_until_input:
            self.close()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if self.hold_until_input:
            self.close()
        else:
            super().mousePressEvent(event)
