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
    enabled = state != "disabled"
    widget.setEnabled(enabled)
    widget.setAttribute(Qt.WA_UnderMouse, state == "hovered")
    widget.setFocusPolicy(Qt.NoFocus)
    widget.clearFocus()
    if kind in ("button", "checkbox", "radio"):
        widget.setText("Sample")
        widget.setAutoExclusive(False)
        widget.setCheckable(kind != "button")
        widget.setChecked(state == "selected")
        widget.setDown(state == "pressed")
        if kind == "button":
            widget.setAutoDefault(False)
            widget.setDefault(False)
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
    size = (120, 23)
    if kind == "scroll-vertical":
        size = (16, 160)
    elif kind == "scroll-horizontal":
        size = (160, 16)
    widget.setFixedSize(*size)
    widget.ensurePolished()
    return qimage_to_pil(widget.grab().toImage())


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


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("state", ("normal", "disabled", "hovered", "pressed", "selected"))
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
