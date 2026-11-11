"""Every control our theme draws, rendered one by one at 1x in a look's colours, for the controls
showcase (tests/render_report.py). Each is a Qt widget as the tools make it (chicago95ui's style and
palette), on a patch of the window colour; next to it the report shows the same control cropped from an
original screenshot where one shows it (ORIGINALS), and omits the reference where none exists.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenuBar,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollBar,
    QSlider,
    QSpinBox,
    QStatusBar,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
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

    plain, default, disabled, pressed = (
        chicago95ui.dialog_button(caption) for caption in ("Cancel", "OK", "Apply", "Pressed")
    )
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
    read_only.setProperty("keepsFocus", True)  # the wizard's field is focused: that is when a field shows its selection
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
    horizontal, disabled, vertical = QSlider(Qt.Horizontal), QSlider(Qt.Horizontal), QSlider(Qt.Vertical)
    horizontal.setFixedWidth(120)
    disabled.setFixedWidth(120)
    disabled.setEnabled(False)
    vertical.setFixedHeight(60)
    for slider in (horizontal, disabled, vertical):
        slider.setRange(0, 10)
        slider.setValue(3)
        slider.setTickPosition(QSlider.TicksBelow)
    return row(horizontal, disabled, vertical)


def scroll_bar(orientation, length, maximum=100, enabled=True):
    bar = QScrollBar(orientation)
    bar.setRange(0, maximum)
    bar.setPageStep(30)
    bar.setValue(20)
    bar.setEnabled(enabled)
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


def explorer_tool_buttons():
    """The Control Panel's Standard Buttons (Internet Explorer 4's): plain in greys, raised and in colour under
    the pointer, sunken while held, and disabled."""
    from conftest import load_script
    from PySide6.QtGui import QAction, QIcon

    control_panel = load_script("chicago95-control-panel")
    buttons = []
    for caption, icon, state in (
        ("Back", "go-previous", "plain"),
        ("Forward", "go-next", "hover"),
        ("Up", "go-up", "pressed"),
        ("Views", "view-list-icons", "disabled"),
    ):
        action = QAction(QIcon.fromTheme(icon), caption)
        action.setEnabled(state != "disabled")
        button = control_panel.ToolbarButton(action, has_menu=caption != "Up")
        button.setAttribute(Qt.WA_UnderMouse, state in ("hover", "pressed"))
        button.setDown(state == "pressed")
        buttons.append(button)
    return row(*buttons, spacing=0)


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


def extra_controls():
    """Native widgets beyond the classic dialogs, shared by every look."""
    from PySide6.QtCore import QDate, QTime
    from PySide6.QtWidgets import (
        QDateEdit,
        QDial,
        QDoubleSpinBox,
        QMenu,
        QPlainTextEdit,
        QSplitter,
        QTableWidget,
        QTableWidgetItem,
        QTimeEdit,
        QTreeWidget,
        QTreeWidgetItem,
    )

    def check_states():
        widgets = []
        for state in (Qt.Unchecked, Qt.PartiallyChecked, Qt.Checked):
            check = QCheckBox(state.name)
            check.setTristate(True)
            check.setCheckState(state)
            widgets.append(check)
        return row(*widgets)

    def button_states():
        widgets = []
        for state in ("Normal", "Hovered", "Focused", "Checked", "Disabled"):
            button = QPushButton(state)
            button.setAttribute(Qt.WA_UnderMouse, state == "Hovered")
            button.setCheckable(state == "Checked")
            button.setChecked(state == "Checked")
            button.setEnabled(state != "Disabled")
            button.setProperty("keepsFocus", state == "Focused")
            widgets.append(button)
        return row(*widgets)

    def editors():
        date = QDateEdit(QDate(2000, 6, 15))
        date.setDisplayFormat("yyyy-MM-dd")
        time = QTimeEdit(QTime(10, 30))
        time.setDisplayFormat("HH:mm")
        number = QDoubleSpinBox()
        number.setValue(12.5)
        return row(date, time, number)

    def multiline():
        text = QPlainTextEdit("Project notes\nReview the controls and their states.\nSelected text")
        text.setFixedSize(350, 95)
        return text

    def tree():
        view = QTreeWidget()
        view.setHeaderLabels(["Name", "Type"])
        parent = QTreeWidgetItem(view, ["Documents", "Folder"])
        QTreeWidgetItem(parent, ["Notes.txt", "Text file"])
        QTreeWidgetItem(view, ["Pictures", "Folder"])
        view.expandAll()
        view.setCurrentItem(parent.child(0))
        view.setFixedSize(350, 120)
        return view

    def table():
        view = QTableWidget(3, 2)
        view.setHorizontalHeaderLabels(["Name", "Size"])
        for r, values in enumerate((("Notes.txt", "2 KB"), ("Photo.png", "24 KB"), ("Archive.zip", "100 KB"))):
            for c, value in enumerate(values):
                view.setItem(r, c, QTableWidgetItem(value))
        view.selectRow(1)
        view.setFixedSize(350, 130)
        return view

    def menu():
        widget = QMenu()
        widget.addAction("Open")
        checked = widget.addAction("Show previews")
        checked.setCheckable(True)
        checked.setChecked(True)
        widget.addAction("Unavailable").setEnabled(False)
        widget.addSeparator()
        widget.addMenu("More").addAction("Details")
        widget.setActiveAction(widget.actions()[0])
        return widget

    def split():
        widget = QSplitter()
        widget.addWidget(QLabel("Folders"))
        widget.addWidget(QLabel("Document preview"))
        widget.setFixedSize(350, 70)
        return widget

    def dial():
        widget = QDial()
        widget.setValue(35)
        widget.setNotchesVisible(True)
        widget.setFixedSize(70, 70)
        return widget

    return [
        ("Push button states (normal, hovered, focused, checked, disabled)", button_states),
        ("Check boxes (unchecked, mixed, checked)", check_states),
        ("Date, time and decimal spin fields", editors),
        ("Text editor, multiline", multiline),
        ("Tree view and header", tree),
        ("Table view and headers", table),
        ("Popup menu: selected, checked, disabled, separator, submenu", menu),
        ("Splitter", split),
        ("Dial", dial),
    ]


# (control, how to make it): the showcase's rows, in this order.
CONTROLS = [
    ("Push buttons (default, plain, disabled, pressed)", push_buttons),
    ("Check boxes", check_boxes),
    ("Radio buttons", radio_buttons),
    ("Text fields", text_fields),
    ("Drop-down lists", drop_down),
    ("Spin box", spin_box),
    ("Disabled drop-down and spin box", disabled_fields),
    ("Sliders (plain, disabled, vertical)", sliders),
    ("Scroll bar, horizontal", lambda: scroll_bar(Qt.Horizontal, 300)),
    ("Scroll bar, vertical", lambda: scroll_bar(Qt.Vertical, 120)),
    ("Scroll bar, disabled", lambda: scroll_bar(Qt.Vertical, 120, enabled=False)),
    ("Scroll bar, nothing to scroll", lambda: scroll_bar(Qt.Vertical, 120, maximum=0, enabled=False)),
    ("Progress bar", progress_bar),
    ("Group box", group_box),
    ("Tabs (Qt's own tab widget)", tab_widget),
    ("List box", list_box),
    ("Menu bar", menu_bar),
    ("Tool bar buttons (plain, disabled, pressed)", tool_buttons),
    ("Explorer toolbar buttons (plain, under the pointer, held, disabled)", explorer_tool_buttons),
    ("Status bar", status_bar),
    ("Labels", labels),
]

# look: {control: (screenshot, box)} where an original screenshot shows the control.
ORIGINALS = {
    "1995": {
        "Push buttons (default, plain, disabled, pressed)": (
            "win95sysprops",
            (232 + 239, 60 + 409, 232 + 407, 60 + 444),
        ),
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
        "Sliders (plain, disabled, vertical)": ("win98mouse", (28, 282, 250, 312)),
        "Disabled drop-down and spin box": ("win98finddate", (110, 100, 225, 182)),
        "Tabs (Qt's own tab widget)": ("win98dialing", (4, 26, 200, 60)),
        "Explorer toolbar buttons (plain, under the pointer, held, disabled)": ("ie4", (10, 49, 320, 91)),
        "Scroll bar, horizontal": ("win98notepad", (7, 342, 392, 360)),
        "Scroll bar, vertical": ("win98notepad", (389, 47, 406, 188)),  # down to the alert that covers the rest
    },
    "luna": {
        "Push buttons (default, plain, disabled, pressed)": ("xpdisplayprop-1x", (150, 415, 404, 452)),
    },
    "2000": {
        "Push buttons (default, plain, disabled, pressed)": ("w2kshutdown", (272, 297, 520, 330)),
        "Check boxes": ("w2klogon", (194, 258, 330, 279)),
        "Text fields": ("w2klogon", (196, 202, 443, 226)),
        "Drop-down lists": ("w2kshutdown", (178, 200, 442, 225)),
        "Progress bar": ("w2kboot", (190, 425, 460, 455)),
    },
}
HALF_SIZE = {"win95shutdownsm", "win98shutsm"}  # thumbnails: shown doubled


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


def original_control(look, name):
    """Only an explicitly mapped crop; absence never prevents native rendering."""
    from PIL import Image
    from reference import screenshot

    counterpart = ORIGINALS.get(look, {}).get(name)
    if counterpart is None:
        return None
    reference, box = counterpart
    try:
        image = screenshot(reference).crop(box)
    except FileNotFoundError:
        return None
    if reference in HALF_SIZE:
        image = image.resize((image.width * 2, image.height * 2), Image.NEAREST)
    return image


def controls(app, look):
    """Every control in the same order for each look; only mapped, available reference crops."""
    return [
        (name, original_control(look, name), render_control(app, make)) for name, make in [*CONTROLS, *extra_controls()]
    ]
