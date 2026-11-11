from PySide6.QtCore import QRect
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QTreeWidget,
    QWidget,
)

GALLERY_SIZE = (400, 300)
BUTTON_ROW_TOP = 12
BUTTON_LEFT = 12
BUTTON_SPACING = 82
BUTTON_SIZE = (75, 23)
CONTROL_BOXES = {
    "line_edit": QRect(12, 48, 120, 21),
    "combo": QRect(140, 48, 120, 21),
    "spin": QRect(268, 48, 80, 21),
    "check_on": QRect(12, 80, 100, 18),
    "check_off": QRect(12, 100, 100, 18),
    "check_disabled": QRect(12, 120, 100, 18),
    "radio_on": QRect(120, 80, 100, 18),
    "radio_off": QRect(120, 100, 100, 18),
    "progress": QRect(228, 84, 160, 16),
    "group": QRect(12, 148, 160, 60),
    "tabs": QRect(184, 112, 204, 96),
    "header": QRect(12, 224, 376, 60),
}


def place(widget, box):
    widget.setGeometry(box)
    return widget


def push_buttons(parent):
    captions = ("OK", "Cancel", "Apply")
    buttons = [
        place(QPushButton(caption, parent), QRect(BUTTON_LEFT + index * BUTTON_SPACING, BUTTON_ROW_TOP, *BUTTON_SIZE))
        for index, caption in enumerate(captions)
    ]
    buttons[0].setDefault(True)
    buttons[2].setEnabled(False)
    return buttons


def check_boxes_and_radios(parent):
    checked = place(QCheckBox("Checked", parent), CONTROL_BOXES["check_on"])
    checked.setChecked(True)
    place(QCheckBox("Unchecked", parent), CONTROL_BOXES["check_off"])
    place(QCheckBox("Disabled", parent), CONTROL_BOXES["check_disabled"]).setEnabled(False)
    selected = place(QRadioButton("Selected", parent), CONTROL_BOXES["radio_on"])
    selected.setChecked(True)
    place(QRadioButton("Other", parent), CONTROL_BOXES["radio_off"])


def fields(parent):
    place(QLineEdit("Line edit", parent), CONTROL_BOXES["line_edit"])
    combo = place(QComboBox(parent), CONTROL_BOXES["combo"])
    combo.addItems(["Highest (32 bit)", "Medium (16 bit)"])
    spin = place(QSpinBox(parent), CONTROL_BOXES["spin"])
    spin.setRange(1980, 2099)
    spin.setValue(2003)
    progress = place(QProgressBar(parent), CONTROL_BOXES["progress"])
    progress.setRange(0, 100)
    progress.setValue(60)
    progress.setTextVisible(False)


def containers(parent):
    place(QGroupBox("Screen resolution", parent), CONTROL_BOXES["group"])
    tabs = place(QTabWidget(parent), CONTROL_BOXES["tabs"])
    for caption in ("Themes", "Desktop", "Settings"):
        tabs.addTab(QWidget(), caption)
    tabs.setCurrentIndex(2)
    listing = place(QTreeWidget(parent), CONTROL_BOXES["header"])
    listing.setHeaderLabels(["Name", "Size", "Type"])


def luna_gallery(parent=None):
    gallery = QWidget(parent)
    gallery.setFixedSize(*GALLERY_SIZE)
    gallery.setAutoFillBackground(True)
    push_buttons(gallery)
    fields(gallery)
    check_boxes_and_radios(gallery)
    containers(gallery)
    return gallery


def style_tree(root, style):
    for widget in [root, *root.findChildren(QWidget)]:
        widget.setStyle(style)
