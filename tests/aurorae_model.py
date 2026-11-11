"""Draws a window frame from a generated Aurorae theme the way KWin's Aurorae does, so tests can compare
our title bars, borders, corners and caption buttons with the originals' screenshots.

It follows KWin's aurorae.qml, AuroraeButtonGroup.qml and AuroraeButton.qml (/usr/share/kwin/aurorae):
the frame is a nine-piece FrameSvg ("decoration" or "decoration-inactive" prefix, see framesvg.py);
the button groups sit TitleEdgeTop + ButtonMarginTop from the
top, the right one TitleEdgeRight in from the right; each button draws its "<state>-center" element
over its whole cell; the caption fills the space between the groups (TitleBorderLeft/Right in),
TitleHeight tall from TitleEdgeTop, vertically centred.
"""

import configparser
import subprocess
import sys
from pathlib import Path

from conftest import REPO
from framesvg import paint_frame
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from reference import qimage_to_pil

GENERATOR = REPO / "aurorae/make_chicago95_aurorae.py"
BUTTON_FILES = {
    "M": None,
    "I": "minimize",
    "A": "maximize",
    "X": "close",
    "H": "help",
    "S": "alldesktops",
    "L": "shade",
}
WIDTH_KEYS = {"M": "ButtonWidthMenu", "X": "ButtonWidthClose"}

# The colours each original's frame uses, as chicago95-sync-colors passes them for the looks.
LOOKS = {
    "1995": dict(
        active="#000080",
        inactive="#808080",
        inactive_text="#C0C0C0",
        face="#C0C0C0",
        light="#DFDFDF",
        shadow="#808080",
        dark="#000000",
    ),
    "1998": dict(
        active="#000080,#1084D0",
        inactive="#808080,#C0C0C0",
        inactive_text="#C0C0C0",
        face="#C0C0C0",
        light="#DFDFDF",
        shadow="#808080",
        dark="#000000",
    ),
    "2000": dict(
        active="#0A246A,#A6CAF0",
        inactive="#808080,#C0C0C0",
        inactive_text="#D4D0C8",
        face="#D4D0C8",
        light="#D4D0C8",
        shadow="#808080",
        dark="#404040",
        gradient_margins="18,52",
    ),
}


def build_theme(out, look):
    """Runs the decoration generator with a look's colours into out; returns out."""
    colours = LOOKS[look]
    arguments = [f"--{key.replace('_', '-')}={value}" for key, value in colours.items()]
    subprocess.run([sys.executable, str(GENERATOR), "--out", str(out), *arguments], check=True, capture_output=True)
    return Path(out)


def title_font():
    """KDE's window title font as Setup sets it: the UI font, bold, 8 points, unsmoothed (Setup's fontconfig rule)."""
    font = QFont("MS W98 UI")
    font.setPointSize(8)
    font.setBold(True)
    font.setStyleStrategy(QFont.NoAntialias)
    return font


class Window:
    def __init__(self, theme, width, height, active=True, caption="", left="M", right="IAX", pressed=(), disabled=()):
        self.theme = Path(theme)
        self.width, self.height, self.active, self.caption = width, height, active, caption
        self.left, self.right, self.pressed, self.disabled = left, right, set(pressed), set(disabled)
        rc = configparser.ConfigParser()
        rc.optionxform = str
        rc.read(self.theme / "Chicago95rc")
        self.layout = {key: int(value) for key, value in rc["Layout"].items()}
        self.general = rc["General"]

    def button_width(self, kind):
        return self.layout.get(WIDTH_KEYS.get(kind, "ButtonWidth"), self.layout["ButtonWidth"])

    def button_rects(self):
        """{kind: QRectF} for every button, menu included."""
        top = self.layout["TitleEdgeTop"] + self.layout["ButtonMarginTop"]
        height = self.layout["ButtonHeight"]
        rects = {}
        x = self.layout["TitleEdgeLeft"]
        for kind in self.left:
            rects[kind] = QRectF(x, top, self.button_width(kind), height)
            x += self.button_width(kind) + self.layout["ButtonSpacing"]
        x = self.width - self.layout["TitleEdgeRight"]
        for kind in reversed(self.right):
            x -= self.button_width(kind)
            rects[kind] = QRectF(x, top, self.button_width(kind), height)
            x -= self.layout["ButtonSpacing"]
        return rects

    def caption_rect(self):
        rects = self.button_rects()
        left_end = max((rects[kind].right() for kind in self.left), default=self.layout["TitleEdgeLeft"])
        right_start = min(
            (rects[kind].left() for kind in self.right), default=self.width - self.layout["TitleEdgeRight"]
        )
        top = self.layout["TitleEdgeTop"]
        height = max(self.layout["TitleHeight"], self.layout["ButtonHeight"])
        return QRectF(
            left_end + self.layout["TitleBorderLeft"],
            top,
            right_start - self.layout["TitleBorderRight"] - left_end - self.layout["TitleBorderLeft"],
            height,
        )

    def paint_frame(self, painter):
        prefix = "decoration" if self.active else "decoration-inactive"
        paint_frame(
            painter, QSvgRenderer(str(self.theme / "decoration.svg")), prefix, QRectF(0, 0, self.width, self.height)
        )

    def paint_buttons(self, painter):
        for kind, rect in self.button_rects().items():
            if BUTTON_FILES.get(kind) is None:
                continue
            state = "pressed" if kind in self.pressed else "deactivated" if kind in self.disabled else ""
            element = "-".join(
                part
                for part in (state or ("active" if self.active else ""), "" if self.active else "inactive", "center")
                if part
            )
            QSvgRenderer(str(self.theme / f"{BUTTON_FILES[kind]}.svg")).render(painter, element, rect)

    def paint_caption(self, painter):
        colour = self.general["ActiveTextColor" if self.active else "InactiveTextColor"].split(",")
        painter.setPen(QColor(*(int(part) for part in colour[:3])))
        painter.setFont(title_font())
        painter.drawText(self.caption_rect(), Qt.AlignLeft | Qt.AlignVCenter, self.caption)

    def render(self):
        """The window's frame as a PIL image (the client area is the frame's centre: plain face)."""
        image = QImage(self.width, self.height, QImage.Format_RGB32)
        image.fill(Qt.white)
        painter = QPainter(image)
        self.paint_frame(painter)
        self.paint_buttons(painter)
        self.paint_caption(painter)
        painter.end()
        return qimage_to_pil(image)
