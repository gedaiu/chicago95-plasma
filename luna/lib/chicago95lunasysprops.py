"""System Properties in Luna: a 7-tab property sheet in LunaStyle, sized from xpdisplayprop-1x.png.

The reference (404x455) is a whole window: 3px frames and a 29px title bar around the client, which the
window decoration draws. Everything here is in the client's coordinates, those of the reference less (3, 29).
"""

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QTabWidget, QVBoxLayout, QWidget

CLIENT_SIZE = (398, 423)
TABS_RECT = QRect(6, 7, 384, 378)
BUTTON_SIZE = (75, 23)
BUTTONS_TOP = 393
BUTTON_LEFTS = {"OK": 155, "Cancel": 236, "Apply": 317}
PICTURE_SIZE = 96
VALUE_INDENT = 16
PAGE_MARGINS = (16, 20, 16, 12)
GROUP_GAP = 12


def value_label(text):
    label = QLabel(text)
    label.setIndent(VALUE_INDENT)
    label.setWordWrap(True)
    return label


def facts_column(groups):
    column = QVBoxLayout()
    column.setSpacing(2)
    for heading, values in groups:
        column.addSpacing(GROUP_GAP)
        column.addWidget(QLabel(heading))
        for value in values:
            column.addWidget(value_label(value))
    column.addStretch()
    return column


def general_page(groups, picture):
    page = QWidget()
    layout = QHBoxLayout(page)
    layout.setContentsMargins(*PAGE_MARGINS)
    computer = QLabel()
    computer.setPixmap(picture.pixmap(PICTURE_SIZE, PICTURE_SIZE) if picture else QPixmap())
    computer.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
    computer.setFixedWidth(PICTURE_SIZE + 24)
    layout.addWidget(computer)
    layout.addLayout(facts_column(groups))
    return page


def build_buttons(dialog):
    buttons = {}
    for caption, left in BUTTON_LEFTS.items():
        button = QPushButton(caption, dialog)
        button.setGeometry(left, BUTTONS_TOP, *BUTTON_SIZE)
        button.setEnabled(caption != "Apply")
        buttons[caption] = button
    buttons["OK"].setDefault(True)
    buttons["OK"].clicked.connect(dialog.accept)
    buttons["Cancel"].clicked.connect(dialog.reject)
    return buttons


def build_dialog(title, captions, pages):
    dialog = QDialog()
    dialog.setWindowTitle(title)
    dialog.setFixedSize(*CLIENT_SIZE)
    dialog.tabs = QTabWidget(dialog)
    dialog.tabs.setGeometry(TABS_RECT)
    for caption, page in zip(captions, pages, strict=True):
        dialog.tabs.addTab(page, caption)
    dialog.buttons = build_buttons(dialog)
    return dialog
