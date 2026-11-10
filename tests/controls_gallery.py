"""Every control our theme draws, rendered one by one at 1x in a look's colours, for the controls
showcase (tests/render_report.py). Each is a Qt widget as the tools make it (chicago95ui's style and
palette), on a patch of the window colour; next to it the report shows the same control cropped from an
original screenshot where one shows it (ORIGINALS), and says so where none does.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMenuBar, QProgressBar,
                               QPushButton, QRadioButton, QScrollBar, QSlider, QSpinBox, QStatusBar, QTabWidget, QToolButton, QVBoxLayout,
                               QWidget)

from reference import qimage_to_pil

PADDING = 8


def row(*widgets, spacing=8):
    holder = QWidget()
    layout = QHBoxLayout(holder)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(spacing)
    for widget in widgets:
        layout.addWidget(widget)
    return holder


def push_buttons():
    import chicago95ui
    plain, default, disabled, pressed = (chicago95ui.dialog_button(caption) for caption in ("Cancel", "OK", "Apply", "Pressed"))
    default.setDefault(True)
    disabled.setEnabled(False)
    pressed.setDown(True)
    return row(default, plain, disabled, pressed, spacing=6)


def check_boxes():
    off, on, disabled = QCheckBox("Off"), QCheckBox("On"), QCheckBox("Disabled")
    on.setChecked(True)
    disabled.setChecked(True)
    disabled.setEnabled(False)
    return row(off, on, disabled)


def radio_buttons():
    off, on, disabled = QRadioButton("Off"), QRadioButton("On"), QRadioButton("Disabled")
    on.setChecked(True)
    disabled.setEnabled(False)
    return row(off, on, disabled)


def text_fields():
    import chicago95ui
    field, disabled = QLineEdit("Some text"), chicago95ui.plain_disabled_text(QLineEdit("Disabled"))
    disabled.setEnabled(False)
    read_only = chicago95ui.read_only_field(QLineEdit("KWOM"))
    read_only.selectAll()
    read_only.setProperty("keepsFocus", True)   # the wizard's field is focused: that is when a field shows its selection
    read_only.setFocus()
    for widget in (field, disabled, read_only):
        widget.setFixedWidth(120)
    return row(field, disabled, read_only)


def drop_down():
    import chicago95ui
    combo = chicago95ui.classic_combo(QComboBox())
    combo.addItems(["Shut down", "Restart", "Stand by"])
    combo.setFixedWidth(160)
    disabled = chicago95ui.classic_combo(QComboBox())
    disabled.addItems(["Disabled"])
    disabled.setEnabled(False)
    disabled.setFixedWidth(100)
    return row(combo, disabled)


def disabled_fields():
    import chicago95ui
    combo = chicago95ui.classic_combo(QComboBox())
    combo.addItem("Modified")
    combo.setFixedWidth(105)
    spin = chicago95ui.plain_disabled_text(QSpinBox())
    spin.setValue(1)
    spin.setFixedWidth(40)
    for widget in (combo, spin):
        widget.setEnabled(False)
    return row(combo, spin)


def spin_box():
    box = QSpinBox()
    box.setRange(0, 100)
    box.setValue(42)
    box.setFixedWidth(60)
    return box


def sliders():
    horizontal, vertical = QSlider(Qt.Horizontal), QSlider(Qt.Vertical)
    horizontal.setFixedWidth(160)
    vertical.setFixedHeight(60)
    for slider in (horizontal, vertical):
        slider.setRange(0, 10)
        slider.setValue(3)
        slider.setTickPosition(QSlider.TicksBelow)
    return row(horizontal, vertical)


def scroll_bar(orientation, length):
    bar = QScrollBar(orientation)
    bar.setRange(0, 100)
    bar.setPageStep(30)
    bar.setValue(20)
    if orientation == Qt.Horizontal:
        bar.setFixedWidth(length)
    else:
        bar.setFixedHeight(length)
    return bar


def progress_bar():
    bar = QProgressBar()
    bar.setRange(0, 100)
    bar.setValue(55)
    bar.setFixedWidth(220)
    return bar


def group_box():
    box = QGroupBox("Group")
    layout = QVBoxLayout(box)
    layout.addWidget(QCheckBox("Inside a group"))
    layout.addWidget(QRadioButton("Another"))
    return box


def tab_widget():
    tabs = QTabWidget()
    for caption in ("General", "Details", "Advanced"):
        page = QWidget()
        QVBoxLayout(page).addWidget(QLabel(caption))
        tabs.addTab(page, caption)
    tabs.setFixedSize(240, 90)
    return tabs


def list_box():
    import chicago95ui
    box = QListWidget()
    box.addItems(["First item", "Second item", "Third item", "Fourth item"])
    box.setItemDelegate(chicago95ui.ListRowDelegate(box))
    box.setCurrentRow(1)
    box.setFixedSize(140, 70)
    return box


def menu_bar():
    bar = QMenuBar()
    for title in ("&File", "&Edit", "&View", "&Help"):
        bar.addMenu(title)
    bar.setFixedWidth(240)
    return bar


def tool_buttons():
    buttons = []
    for caption, state in (("Back", "plain"), ("Forward", "disabled"), ("Up", "pressed")):
        button = QToolButton()
        button.setText(caption)
        button.setAutoRaise(False)
        button.setEnabled(state != "disabled")
        button.setDown(state == "pressed")
        buttons.append(button)
    return row(*buttons, spacing=2)


def status_bar():
    bar = QStatusBar()
    bar.addWidget(QLabel("131 object(s)"), 1)
    bar.addWidget(QLabel("4.90MB"), 2)
    bar.setSizeGripEnabled(True)
    bar.setFixedWidth(300)
    return bar


def labels():
    import chicago95ui
    plain, disabled = QLabel("A label"), QLabel("A disabled (engraved) label")
    disabled.setEnabled(False)
    for label in (plain, disabled):
        label.setFont(chicago95ui.ui_font())
    return row(plain, disabled)


# (control, how to make it): the showcase's rows, in this order.
CONTROLS = [
    ("Push buttons (default, plain, disabled, pressed)", push_buttons),
    ("Check boxes", check_boxes),
    ("Radio buttons", radio_buttons),
    ("Text fields", text_fields),
    ("Drop-down lists", drop_down),
    ("Spin box", spin_box),
    ("Disabled drop-down and spin box", disabled_fields),
    ("Sliders", sliders),
    ("Scroll bar, horizontal", lambda: scroll_bar(Qt.Horizontal, 300)),
    ("Scroll bar, vertical", lambda: scroll_bar(Qt.Vertical, 120)),
    ("Progress bar", progress_bar),
    ("Group box", group_box),
    ("Tabs (Qt's own tab widget)", tab_widget),
    ("List box", list_box),
    ("Menu bar", menu_bar),
    ("Tool bar buttons (plain, disabled, pressed)", tool_buttons),
    ("Status bar", status_bar),
    ("Labels", labels),
]

# look: {control: (screenshot, box)} where an original screenshot shows the control.
ORIGINALS = {
    "1995": {
        "Push buttons (default, plain, disabled, pressed)": ("win95sysprops", (232 + 239, 60 + 409, 232 + 407, 60 + 444)),
        "Radio buttons": ("win95shutdownsm", (90, 84, 246, 136)),
        "Scroll bar, horizontal": ("win95desktop3", (216, 404, 637, 420)),
        "Status bar": ("win95desktop3", (216, 423, 637, 441)),
    },
    "1998": {
        "Push buttons (default, plain, disabled, pressed)": ("win98dialing", (138, 430, 384, 462)),
        "Check boxes": ("win98dialing", (30, 243, 200, 264)),
        "Radio buttons": ("win98dialing", (92, 274, 250, 296)),
        "Text fields": ("win98newconnection", (148, 62, 431, 93)),
        "Drop-down lists": ("win98dialing", (32, 71, 166, 100)),
        "Group box": ("win98dialing", (20, 148, 374, 374)),
        "Disabled drop-down and spin box": ("win98finddate", (110, 100, 225, 182)),
        "Tabs (Qt's own tab widget)": ("win98dialing", (4, 26, 200, 60)),
        "Scroll bar, horizontal": ("win98notepad", (7, 342, 392, 360)),
        "Scroll bar, vertical": ("win98notepad", (389, 47, 406, 188)),   # down to the alert that covers the rest
    },
    "2000": {
        "Push buttons (default, plain, disabled, pressed)": ("w2ksysprops", (434 + 158, 205 + 422, 434 + 407, 205 + 457)),
        "Check boxes": ("w2klogon", (194, 258, 330, 279)),
        "Text fields": ("w2klogon", (196, 202, 443, 226)),
        "Drop-down lists": ("w2kshutdown", (178, 200, 442, 225)),
        "Progress bar": ("w2kboot", (190, 425, 460, 455)),
    },
}
HALF_SIZE = {"win95shutdownsm", "win98shutsm"}   # thumbnails: shown doubled


def render_control(app, make, inspect=None):
    """The control on a patch of the window colour, at 1x; inspect(patch) sees it laid out, before the grab."""
    patch = QWidget()
    patch.setAutoFillBackground(True)
    layout = QHBoxLayout(patch)
    layout.setContentsMargins(PADDING, PADDING, PADDING, PADDING)
    layout.addWidget(make())
    patch.adjustSize()
    patch.show()
    app.processEvents()
    # Focus goes to a widget made to keep it (a field showing its selection) or to a default button, as the
    # originals show them; nothing else gets a focus rectangle.
    keepers = [widget for widget in patch.findChildren(QWidget) if widget.property("keepsFocus")]
    if keepers:
        keepers[0].setFocus()
    for widget in patch.findChildren(QWidget):
        if widget.hasFocus() and not isinstance(widget, QPushButton) and not widget.property("keepsFocus"):
            widget.clearFocus()
    app.processEvents()
    if inspect:
        inspect(patch)
    image = qimage_to_pil(patch.grab().toImage())
    patch.close()
    return image


def controls(app, look):
    """[(control, original crop or None, ours)] for a look, our widgets in the look's colours (the
    caller installs them, see reference.installed_look)."""
    from PIL import Image
    from reference import screenshot
    rows = []
    for name, make in CONTROLS:
        original = None
        if name in ORIGINALS.get(look, {}):
            reference, box = ORIGINALS[look][name]
            original = screenshot(reference).crop(box)
            if reference in HALF_SIZE:
                original = original.resize((original.width * 2, original.height * 2), Image.NEAREST)
        rows.append((name, original, render_control(app, make)))
    return rows
