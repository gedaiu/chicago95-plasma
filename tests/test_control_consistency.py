"""Pixel-level checks of equivalent controls from different production construction paths.

Failures save reference, candidate and amplified difference images next to the pytest case.
Text, size, value and interaction state are identical; toolkit renderers are not rescaled.
"""

import chicago95ui
import pytest
from conftest import load_script
from PIL import Image, ImageChops, ImageEnhance
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollBar,
    QSlider,
    QSpinBox,
    QTextEdit,
)
from reference import LOOK_2000_KDEGLOBALS, installed_look, qimage_to_pil

LOOKS = ("1995", "1998", "2000", "2001", "luna")
KINDS = ("button", "checkbox", "radio", "input", "combo", "spin", "slider", "scroll-horizontal", "scroll-vertical")


@pytest.fixture(params=LOOKS)
def look(request, qt_app):
    name = request.param
    settings = f"[StartMenu]\nstyle={name}\n[Look]\nwidgetStyle={'luna' if name == 'luna' else 'classic'}\n"
    colours = LOOK_2000_KDEGLOBALS if name in ("2000", "2001") else ""
    with installed_look(qt_app, settings, colours):
        chicago95ui.apply_style(qt_app)
        yield name
    chicago95ui.apply_style(qt_app)


@pytest.fixture(scope="module")
def control_panel():
    return load_script("chicago95-control-panel")


def instances(kind, panel):
    """Native widget vs the real gallery and Control Panel factories / embedded scroll bars."""
    import controls_gallery as gallery

    owners = []
    if kind == "button":
        holder = gallery.push_buttons()
        owners.append(holder)
        widgets = [QPushButton(), holder.findChildren(QPushButton)[0], chicago95ui.dialog_button("")]
    elif kind == "checkbox":
        holder = gallery.check_boxes()
        owners.append(holder)
        widgets = [QCheckBox(), holder.findChildren(QCheckBox)[0], panel.flag("flag", "")]
    elif kind == "radio":
        holder = gallery.radio_buttons()
        owners.append(holder)
        radios = panel.radios("radio", "Options", [("", "a"), ("Other", "b")], "a")
        from PySide6.QtWidgets import QButtonGroup

        for group in radios.findChildren(QButtonGroup):
            group.setExclusive(False)
        widgets = [QRadioButton(), holder.findChildren(QRadioButton)[0], radios.findChildren(QRadioButton)[0]]
    elif kind == "input":
        holder = gallery.text_fields()
        owners.append(holder)
        widgets = [QLineEdit(), holder.findChildren(QLineEdit)[1], panel.text("input", "")]
    elif kind == "combo":
        holder = gallery.drop_down()
        owners.append(holder)
        widgets = [QComboBox(), holder.findChildren(QComboBox)[0], panel.choice("combo", "", [("Sample", "a")], "a")]
    elif kind == "spin":
        widgets = [QSpinBox(), gallery.spin_box(), panel.number("spin", "", 0, 100, 42)]
    elif kind == "slider":
        holder = gallery.sliders()
        owners.append(holder)
        widgets = [QSlider(Qt.Horizontal), holder.findChildren(QSlider)[0], QSlider(Qt.Horizontal, panel)]
    else:
        orientation = Qt.Horizontal if kind == "scroll-horizontal" else Qt.Vertical
        editor = QTextEdit()
        owners.append(editor)
        widgets = [
            QScrollBar(orientation),
            gallery.scroll_bar(orientation, 160),
            editor.horizontalScrollBar() if orientation == Qt.Horizontal else editor.verticalScrollBar(),
        ]
    return widgets, owners


def normalize(widget, kind, state):
    size = (120, 23)
    if kind == "scroll-vertical":
        size = (16, 160)
    elif kind == "scroll-horizontal":
        size = (160, 16)
    widget.setFixedSize(*size)
    widget.ensurePolished()
    widget.grab()  # Settle the enclosing scroll area before setting a controlled range.
    enabled = not state.startswith("disabled")
    widget.setEnabled(enabled)
    widget.setAttribute(Qt.WA_UnderMouse, "hovered" in state)
    widget.setFocusPolicy(Qt.NoFocus)
    widget.clearFocus()
    if kind in ("button", "checkbox", "radio"):
        widget.setText("Sample")
        widget.setAutoExclusive(False)
        widget.setCheckable(kind != "button")
        widget.setChecked("selected" in state)
        if kind == "checkbox":
            widget.setTristate(True)
            widget.setCheckState(
                Qt.PartiallyChecked if "mixed" in state else Qt.Checked if "selected" in state else Qt.Unchecked
            )
        widget.setDown("pressed" in state)
        if kind == "button":
            widget.setAutoDefault(False)
            widget.setDefault("default" in state)
    elif kind == "input":
        widget.setText("Sample")
        widget.setCursorPosition(0)
        widget.deselect()
    elif kind == "combo":
        widget.clear()
        widget.addItems(["Sample", "Other"])
    elif kind in ("spin", "slider", "scroll-horizontal", "scroll-vertical"):
        widget.setRange(0, 100)
        widget.setValue(42)
        if kind != "spin":
            widget.setPageStep(20)
            widget.setSingleStep(1)
        if kind == "slider":
            widget.setTickPosition(QSlider.NoTicks)
    if "hovered" in state or "pressed" in state or state == "focused":
        return paint_interaction(widget, kind, state)
    return qimage_to_pil(widget.grab().toImage())


def paint_interaction(widget, kind, state):
    """Drive precise QStyle subcontrols: setting underMouse alone doesn't hover a scroll thumb."""
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtWidgets import (
        QStyle,
        QStyleOptionButton,
        QStyleOptionComboBox,
        QStyleOptionSlider,
        QStyleOptionSpinBox,
    )

    simple = {
        "button": QStyle.CE_PushButton,
        "checkbox": QStyle.CE_CheckBox,
        "radio": QStyle.CE_RadioButton,
    }
    complex_controls = {
        "combo": (QStyleOptionComboBox, QStyle.CC_ComboBox, QStyle.SC_ComboBoxArrow),
        "spin": (QStyleOptionSpinBox, QStyle.CC_SpinBox, QStyle.SC_SpinBoxUp),
        "slider": (QStyleOptionSlider, QStyle.CC_Slider, QStyle.SC_SliderHandle),
        "scroll-horizontal": (QStyleOptionSlider, QStyle.CC_ScrollBar, QStyle.SC_ScrollBarSlider),
        "scroll-vertical": (QStyleOptionSlider, QStyle.CC_ScrollBar, QStyle.SC_ScrollBarSlider),
    }
    if kind == "input":
        return qimage_to_pil(widget.grab().toImage())
    option = QStyleOptionButton() if kind in simple else complex_controls[kind][0]()
    widget.initStyleOption(option)
    option.state &= ~(QStyle.State_MouseOver | QStyle.State_Sunken | QStyle.State_HasFocus)
    if "hovered" in state:
        option.state |= QStyle.State_MouseOver
    if "pressed" in state:
        option.state |= QStyle.State_Sunken
    if state == "focused":
        option.state |= QStyle.State_HasFocus | QStyle.State_KeyboardFocusChange
    if kind not in simple:
        option.activeSubControls = complex_controls[kind][2]
        if state.endswith("arrow") and kind.startswith("scroll"):
            option.activeSubControls = QStyle.SC_ScrollBarSubLine
        if state.endswith("down") and kind == "spin":
            option.activeSubControls = QStyle.SC_SpinBoxDown
    image = QImage(widget.size(), QImage.Format_RGB32)
    image.fill(widget.palette().window().color())
    painter = QPainter(image)
    painter.setFont(widget.font())
    if kind in simple:
        widget.style().drawControl(simple[kind], option, painter, widget)
    else:
        widget.style().drawComplexControl(complex_controls[kind][1], option, painter, widget)
        if kind == "combo":
            widget.style().drawControl(QStyle.CE_ComboBoxLabel, option, painter, widget)
    painter.end()
    return qimage_to_pil(image)


def assert_same(expected, actual, path):
    if expected.size == actual.size and expected.tobytes() == actual.tobytes():
        return
    expected.save(path.with_suffix(".expected.png"))
    actual.save(path.with_suffix(".actual.png"))
    width, height = max(expected.width, actual.width), max(expected.height, actual.height)
    a, b = Image.new("RGB", (width, height)), Image.new("RGB", (width, height))
    a.paste(expected)
    b.paste(actual)
    diff = ImageChops.difference(a, b)
    ImageEnhance.Contrast(diff).enhance(4).save(path.with_suffix(".diff.png"))
    pixels = sum(pixel != (0, 0, 0) for pixel in diff.getdata())
    pytest.fail(f"{pixels}/{width * height} pixels differ; see {path}.[expected|actual|diff].png")


CASES = [(kind, state) for kind in KINDS for state in ("normal", "disabled")]
CASES += [(kind, state) for kind in KINDS if kind != "input" for state in ("hovered", "pressed", "focused")]
CASES += [(kind, "selected") for kind in ("checkbox", "radio")]
CASES += [("checkbox", "mixed")]
CASES += [
    (kind, state) for kind in ("scroll-horizontal", "scroll-vertical") for state in ("hovered-arrow", "pressed-arrow")
]
CASES += [("spin", state) for state in ("hovered-down", "pressed-down")]
CASES += [
    (kind, state)
    for kind in ("checkbox", "radio")
    for state in ("selected-hovered", "selected-pressed", "disabled-selected")
]
CASES += [("checkbox", "disabled-mixed")]
CASES += [("button", state) for state in ("default", "default-hovered", "default-pressed", "disabled-default")]


@pytest.mark.parametrize("kind,state", CASES)
def test_same_control_across_construction_paths(look, kind, state, qt_app, control_panel, tmp_path):
    panel = control_panel.SettingsTab({}, {})
    widgets, owners = instances(kind, panel)
    try:
        pictures = [normalize(widget, kind, state) for widget in widgets]
        for index, picture in enumerate(pictures[1:], 1):
            assert_same(pictures[0], picture, tmp_path / f"{look}-{kind}-{state}-source{index}")
    finally:
        import shiboken6

        roots = {id(widget.window()): widget.window() for widget in [*widgets, *owners, panel]}
        for root in roots.values():
            if shiboken6.isValid(root):
                shiboken6.delete(root)


def test_checkbox_mixed_state_is_visibly_distinct(look, qt_app):
    box = QCheckBox()
    try:
        images = [normalize(box, "checkbox", state) for state in ("normal", "selected", "mixed")]
        assert len({image.tobytes() for image in images}) == 3
    finally:
        box.close()
