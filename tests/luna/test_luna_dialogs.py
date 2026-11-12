import colorsys
import importlib.util
import sys
from pathlib import Path

import pytest
from conftest import REPO
from PIL import Image
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from reference import qimage_to_pil

from .luna_profile import (
    BLURRED_BUDGET,
    RAW_BUDGET,
    blurred_differing_fraction,
    differing_fraction,
    horizontal_profile,
    profile_excess,
    vertical_profile,
)

sys.path.insert(0, str(REPO / "luna/lib"))
spec = importlib.util.spec_from_file_location("chicago95lunadialogs", REPO / "luna/lib/chicago95lunadialogs.py")
luna_dialogs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(luna_dialogs)

REFERENCES = REPO / "tests/references"
PREVIEW_DIR = Path(
    "/tmp/claude-1000/-home-gedaiu-workspace-chicago95-plasma/6679116e-4ef6-4478-b441-c6cd1dc95f4a/scratchpad/luna-preview"
)
COLOUR_TOLERANCE = 12
TEXT_FREE_COLUMNS = {
    "top band": (range(200, 260), range(1, 44)),
    "middle band": (range(15, 25), range(46, 156)),
    "bottom band": (range(15, 25), range(157, 199)),
}
HORIZONTAL_PROFILES = {"highlight": [44, 45], "middle band": list(range(50, 76))}
TURN_OFF_MASKS = [
    (10, 12, 170, 36),
    (266, 4, 312, 41),
    (54, 80, 89, 115),
    (140, 80, 175, 115),
    (225, 80, 260, 115),
    (40, 119, 270, 136),
    (250, 171, 297, 184),
]
LOG_OFF_MASKS = [
    (10, 12, 170, 36),
    (266, 4, 312, 41),
    (83, 80, 118, 115),
    (198, 80, 233, 115),
    (60, 119, 240, 136),
    (250, 171, 297, 184),
]
BODY_POINTS = {"yellow": (59, 97), "red": (145, 97), "green": (230, 97)}


@pytest.fixture
def calls():
    return []


@pytest.fixture
def commands(calls):
    names = ["stand_by", "hibernate", "turn_off", "restart", "cancel", "log_off", "switch_user"]
    return {name: (lambda name=name: calls.append(name)) for name in names}


@pytest.fixture
def turn_off(qt_app, commands):
    dialog = luna_dialogs.TurnOffDialog(commands)
    dialog.show()
    return dialog


@pytest.fixture
def log_off(qt_app, commands):
    dialog = luna_dialogs.LogOffDialog(commands)
    dialog.show()
    return dialog


def drawn(qt_app, name):
    grab = {"turn off": luna_dialogs.drawn_turn_off_dialog, "log off": luna_dialogs.drawn_log_off_dialog}[name]
    return qimage_to_pil(grab())


def reference(name):
    return Image.open(REFERENCES / name).convert("RGB")


def hue_degrees(pixel):
    return colorsys.rgb_to_hsv(*(channel / 255 for channel in pixel))[0] * 360


def click_button(dialog, key):
    button = dialog.buttons[key]
    QTest.mouseClick(button, Qt.LeftButton, Qt.NoModifier, QPoint(button.width() // 2, 30))


@pytest.mark.parametrize("name", ["turn off", "log off"])
def test_grab_is_314_by_200(qt_app, name):
    assert drawn(qt_app, name).size == (314, 200)


DIALOGS = [("turn off", "xpshutdowndialog.png"), ("log off", "xplogoff.png")]


@pytest.mark.parametrize("name, file", DIALOGS)
@pytest.mark.parametrize("band", TEXT_FREE_COLUMNS)
def test_band_profile_matches_reference_within_12(qt_app, name, file, band):
    columns, rows = TEXT_FREE_COLUMNS[band]
    expected, ours = reference(file), drawn(qt_app, name)
    assert (
        profile_excess(vertical_profile(expected, columns, rows), vertical_profile(ours, columns, rows))
        <= COLOUR_TOLERANCE
    )


@pytest.mark.parametrize("name, file", DIALOGS)
@pytest.mark.parametrize("band", HORIZONTAL_PROFILES)
def test_horizontal_gradient_profile_matches_reference_within_12(qt_app, name, file, band):
    columns, rows = range(1, 313), HORIZONTAL_PROFILES[band]
    expected, ours = reference(file), drawn(qt_app, name)
    assert (
        profile_excess(horizontal_profile(expected, columns, rows), horizontal_profile(ours, columns, rows))
        <= COLOUR_TOLERANCE
    )


@pytest.mark.parametrize("name", ["turn off", "log off"])
def test_outer_border_is_one_black_pixel(qt_app, name):
    ours = drawn(qt_app, name)
    edges = [ours.getpixel(point) for point in [(0, 100), (313, 100), (150, 0), (150, 199)]]
    assert edges == [(0, 0, 0)] * 4


@pytest.mark.parametrize("icon, hue_range", [("yellow", (25, 50)), ("red", (-15, 15)), ("green", (100, 140))])
def test_icon_body_hue_matches_colour(qt_app, icon, hue_range):
    hue = hue_degrees(drawn(qt_app, "turn off").getpixel(BODY_POINTS[icon]))
    assert hue_range[0] <= (hue if hue < 180 else hue - 360) <= hue_range[1]


def test_switch_user_icon_is_green_and_log_off_icon_orange(qt_app):
    ours = drawn(qt_app, "log off")
    switch_hue, log_off_hue = (hue_degrees(ours.getpixel(point)) for point in [(88, 97), (203, 97)])
    assert (100 <= switch_hue <= 140, 25 <= log_off_hue <= 45) == (True, True)


MASKED_DIALOGS = [("turn off", "xpshutdowndialog.png", TURN_OFF_MASKS), ("log off", "xplogoff.png", LOG_OFF_MASKS)]


@pytest.mark.parametrize("name, file, masks", MASKED_DIALOGS)
def test_masked_dialog_matches_reference_within_budget(qt_app, name, file, masks):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    diff_path = PREVIEW_DIR / f"dialog-{name.replace(' ', '-')}-diff.png"
    assert differing_fraction(reference(file), drawn(qt_app, name), masks, diff_path) <= RAW_BUDGET


@pytest.mark.parametrize("name, file, masks", MASKED_DIALOGS)
def test_blurred_masked_dialog_matches_blurred_reference_within_budget(qt_app, name, file, masks):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    diff_path = PREVIEW_DIR / f"dialog-{name.replace(' ', '-')}-blur-diff.png"
    assert blurred_differing_fraction(reference(file), drawn(qt_app, name), masks, diff_path) <= BLURRED_BUDGET


@pytest.mark.parametrize("key", ["stand_by", "turn_off", "restart"])
def test_clicking_turn_off_button_calls_its_command(turn_off, calls, key):
    click_button(turn_off, key)
    assert calls == [key]


@pytest.mark.parametrize("key", ["switch_user", "log_off"])
def test_clicking_log_off_button_calls_its_command(log_off, calls, key):
    click_button(log_off, key)
    assert calls == [key]


@pytest.mark.parametrize("dialog_name", ["turn_off", "log_off"])
def test_clicking_cancel_calls_cancel(request, calls, dialog_name):
    dialog = request.getfixturevalue(dialog_name)
    QTest.mouseClick(dialog.cancel_button, Qt.LeftButton)
    assert calls == ["cancel"]


@pytest.mark.parametrize("dialog_name", ["turn_off", "log_off"])
def test_escape_calls_cancel(request, calls, dialog_name):
    dialog = request.getfixturevalue(dialog_name)
    QTest.keyClick(dialog, Qt.Key_Escape)
    assert calls == ["cancel"]


@pytest.mark.parametrize("key, command", [(Qt.Key_S, "stand_by"), (Qt.Key_U, "turn_off"), (Qt.Key_R, "restart")])
def test_turn_off_mnemonic_calls_command(turn_off, calls, key, command):
    QTest.keyClick(turn_off, key)
    assert calls == [command]


@pytest.mark.parametrize("key, command", [(Qt.Key_S, "switch_user"), (Qt.Key_L, "log_off")])
def test_log_off_mnemonic_calls_command(log_off, calls, key, command):
    QTest.keyClick(log_off, key)
    assert calls == [command]


def test_enter_presses_focused_button(turn_off, calls):
    turn_off.buttons["restart"].setFocus()
    QTest.keyClick(turn_off.buttons["restart"], Qt.Key_Return)
    assert calls == ["restart"]


def test_stand_by_falls_back_to_hibernate(qt_app, calls):
    dialog = luna_dialogs.TurnOffDialog(
        {"hibernate": lambda: calls.append("hibernate"), "turn_off": None, "restart": None, "cancel": None}
    )
    QTest.keyClick(dialog, Qt.Key_S)
    assert calls == ["hibernate"]


@pytest.mark.parametrize(
    "dialog_name,key",
    [
        ("turn_off", "turn_off"),
        ("turn_off", "stand_by"),
        ("turn_off", "restart"),
        ("log_off", "switch_user"),
        ("log_off", "log_off"),
    ],
)
def test_vector_button_states_keep_hover_focus_and_pressed_distinct(request, dialog_name, key):
    dialog = request.getfixturevalue(dialog_name)
    button = dialog.buttons[key]
    dialog.activateWindow()
    luna_dialogs.QApplication.processEvents()
    dialog.cancel_button.setFocus()
    button.setAttribute(Qt.WA_UnderMouse, False)
    idle = button.grab().toImage()
    button.setAttribute(Qt.WA_UnderMouse, True)
    hot = button.grab().toImage()
    button.setAttribute(Qt.WA_UnderMouse, False)
    button.setFocus()
    assert button.hasFocus()
    focused = button.grab().toImage()
    button.setDown(True)
    pressed = button.grab().toImage()
    assert focused == hot
    assert hot.pixelColor(4, 16).lightness() > idle.pixelColor(4, 16).lightness()
    assert pressed.pixelColor(4, 16).lightness() < idle.pixelColor(4, 16).lightness()


@pytest.mark.parametrize("spec", luna_dialogs.TURN_OFF_SPECS + luna_dialogs.LOG_OFF_SPECS)
def test_vector_icons_render_new_detail_at_high_dpi(qt_app, spec):
    images = []
    for scale in (1, 2):
        image = luna_dialogs.QImage(32 * scale, 32 * scale, luna_dialogs.QImage.Format_ARGB32)
        image.setDevicePixelRatio(scale)
        image.fill(Qt.transparent)
        painter = luna_dialogs.QPainter(image)
        luna_dialogs.paint_icon(painter, spec)
        painter.end()
        images.append(image)
    # A native high-DPI render must not repeat each low-resolution pixel in 2x2 blocks.
    assert images[1] != images[0].scaled(64, 64, Qt.IgnoreAspectRatio, Qt.FastTransformation)
    assert len({images[1].pixelColor(8, y).rgb() for y in range(8, 56)}) > 32


def test_highlight_does_not_change_caption_or_background(turn_off):
    button = turn_off.buttons["turn_off"]
    turn_off.cancel_button.setFocus()
    button.setAttribute(Qt.WA_UnderMouse, False)
    idle = qimage_to_pil(turn_off.grab().toImage())
    button.setAttribute(Qt.WA_UnderMouse, True)
    hot = qimage_to_pil(turn_off.grab().toImage())
    assert idle.crop((114, 115, 200, 137)).tobytes() == hot.crop((114, 115, 200, 137)).tobytes()


def test_caption_is_not_a_button(turn_off, calls):
    QTest.mouseClick(turn_off, Qt.LeftButton, Qt.NoModifier, QPoint(157, 126))
    assert calls == []


def test_press_release_outside_does_not_activate(turn_off, calls):
    button = turn_off.buttons["turn_off"]
    QTest.mousePress(button, Qt.LeftButton, Qt.NoModifier, QPoint(16, 16))
    assert button.isDown()
    assert calls == []
    QTest.mouseRelease(button, Qt.LeftButton, Qt.NoModifier, QPoint(-8, -8))
    assert not button.isDown()
    assert calls == []


def test_space_presses_then_activates_on_release(turn_off, calls):
    button = turn_off.buttons["restart"]
    button.setFocus()
    QTest.keyPress(button, Qt.Key_Space)
    assert button.isDown()
    assert calls == []
    QTest.keyRelease(button, Qt.Key_Space)
    assert calls == ["restart"]


def test_disabled_stand_by_uses_disabled_artwork_and_ignores_mnemonic(turn_off, calls):
    button = turn_off.buttons["stand_by"]
    button.setEnabled(False)
    actual = qimage_to_pil(button.grab().toImage()).convert("RGB")
    red, green, blue = actual.getpixel((5, 16))
    assert blue > green > red
    QTest.keyClick(turn_off, Qt.Key_S)
    assert calls == []


def test_preview_compares_dialogs_with_references(qt_app):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    pairs = [
        (drawn(qt_app, "turn off"), reference("xpshutdowndialog.png")),
        (drawn(qt_app, "log off"), reference("xplogoff.png")),
    ]
    sheet = Image.new("RGB", (314 * 4, 200 * 4), "#808080")
    for row, (ours, expected) in enumerate(pairs):
        sheet.paste(ours.resize((628, 400), Image.NEAREST), (0, row * 400))
        sheet.paste(expected.resize((628, 400), Image.NEAREST), (628, row * 400))
    sheet.save(PREVIEW_DIR / "dialogs-compare.png")
    assert sheet.size == (1256, 800)


@pytest.mark.parametrize("dialog_name", ["turn_off", "log_off"])
@pytest.mark.parametrize("state", ["normal", "hover", "focus", "pressed", "disabled"])
@pytest.mark.parametrize("scale", [1, 1.5, 2])
def test_cancel_rounded_corners_leave_blue_background(request, dialog_name, state, scale):
    dialog = request.getfixturevalue(dialog_name)
    button = dialog.cancel_button
    button.setEnabled(state != "disabled")
    button.setAttribute(Qt.WA_UnderMouse, state in ("hover", "pressed"))
    button.setDown(state == "pressed")
    if state == "focus":
        button.setFocus()
    image = luna_dialogs.QImage(round(314 * scale), round(200 * scale), luna_dialogs.QImage.Format_RGB32)
    image.setDevicePixelRatio(scale)
    dialog.render(image)
    rect = button.geometry()
    # The former straight edge overlays painted these pixels past the rounded
    # corners, leaving bright tails at either end of the bottom edge.
    left, top = round(rect.left() * scale), round(rect.top() * scale)
    right, bottom = round((rect.right() + 1) * scale) - 1, round((rect.bottom() + 1) * scale) - 1
    for x in (left + 1, right - 1):
        for y in (top, bottom):
            assert image.pixelColor(x, y).name() == "#003399"


@pytest.mark.parametrize("dialog_name", ["turn_off", "log_off"])
@pytest.mark.parametrize("state", ["normal", "hover", "pressed", "disabled"])
def test_cancel_has_no_line_below_button(request, dialog_name, state):
    dialog = request.getfixturevalue(dialog_name)
    button = dialog.cancel_button
    button.setEnabled(state != "disabled")
    button.setAttribute(Qt.WA_UnderMouse, state == "hover")
    button.setDown(state == "pressed")
    image = dialog.grab().toImage()
    rect = button.geometry()
    assert all(image.pixelColor(x, rect.bottom()).name() == "#003399" for x in range(rect.left(), rect.right() + 1))


@pytest.mark.parametrize("dialog_name", ["turn_off", "log_off"])
@pytest.mark.parametrize("scale", [1.25, 1.5, 2, 3])
def test_flag_renders_native_detail_at_display_scale(request, dialog_name, scale):
    dialog = request.getfixturevalue(dialog_name)
    assert dialog.flag.isValid()
    images = []
    for ratio in (1, scale):
        image = luna_dialogs.QImage(round(314 * ratio), round(200 * ratio), luna_dialogs.QImage.Format_RGB32)
        image.setDevicePixelRatio(ratio)
        dialog.render(image)
        images.append(image.copy(round(270 * ratio), round(7 * ratio), round(38 * ratio), round(32 * ratio)))
    enlarged = images[0].scaled(images[1].size(), Qt.IgnoreAspectRatio, Qt.FastTransformation)
    assert images[1] != enlarged
    colours = {images[1].pixelColor(x, y).rgb() for x in range(images[1].width()) for y in range(images[1].height())}
    assert len(colours) > 500


def test_installed_dialog_resolves_shipped_vector_flag(tmp_path, monkeypatch):
    images = tmp_path / "images"
    images.mkdir()
    source = REPO / "luna/images/windows-xp-flag.svg"
    (images / source.name).write_bytes(source.read_bytes())
    monkeypatch.setattr(luna_dialogs, "__file__", str(tmp_path / "chicago95lunadialogs.py"))
    assert luna_dialogs.flag_picture_path() == images / source.name


LOGO_MIDDLE = (289, 23)  # inside the XP flag's 38x32 slot at (270, 7)


def blue_picture(path):
    Image.new("RGBA", (32, 32), "#0000ff").save(path)
    return str(path)


def drawn_with(dialog_class, **branding):
    commands = luna_dialogs.silent_commands("stand_by", "turn_off", "restart", "log_off", "switch_user")
    return qimage_to_pil(luna_dialogs.grab_image(dialog_class(commands, **branding))).convert("RGB")


def test_a_logo_of_the_users_own_takes_the_xp_flags_place_on_turn_off(qt_app, tmp_path):
    image = drawn_with(luna_dialogs.TurnOffDialog, logo=blue_picture(tmp_path / "fedora-logo-icon.png"))
    assert image.getpixel(LOGO_MIDDLE) == (0, 0, 255)


def test_a_bundled_flag_keeps_the_xp_flag_on_turn_off(qt_app, tmp_path):
    image = drawn_with(luna_dialogs.TurnOffDialog, logo=blue_picture(tmp_path / "logo-xp-16.png"))
    assert image.getpixel(LOGO_MIDDLE) != (0, 0, 255)


def test_log_off_names_the_system_it_is_given(qt_app):
    commands = luna_dialogs.silent_commands("log_off", "switch_user")
    assert luna_dialogs.LogOffDialog(commands, name="Fedora Linux").title == "Log Off Fedora Linux"


def test_log_off_names_windows_without_a_system(qt_app):
    commands = luna_dialogs.silent_commands("log_off", "switch_user")
    assert luna_dialogs.LogOffDialog(commands).title == "Log Off Windows"


@pytest.mark.parametrize(
    "dialog_name,command",
    [
        ("turn_off", "stand_by"),
        ("turn_off", "turn_off"),
        ("turn_off", "restart"),
        ("log_off", "switch_user"),
        ("log_off", "log_off"),
        ("turn_off", "cancel"),
        ("log_off", "cancel"),
    ],
)
def test_button_tooltip_is_displayed_without_running_action(request, dialog_name, command, calls, tmp_path):
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QHelpEvent
    from PySide6.QtWidgets import QApplication, QToolTip

    dialog = request.getfixturevalue(dialog_name)
    button = dialog.cancel_button if command == "cancel" else dialog.buttons[command]
    dialog.activateWindow()
    QTest.qWait(50)
    point = button.rect().center()
    QTest.mouseMove(button, point)
    QToolTip.hideText()
    QApplication.sendEvent(button, QHelpEvent(QEvent.ToolTip, point, button.mapToGlobal(point)))
    QTest.qWait(50)
    assert button.toolTip()
    assert QToolTip.isVisible()
    assert QToolTip.text() == button.toolTip()
    tooltip = next(
        widget for widget in QApplication.topLevelWidgets() if widget.isVisible() and widget.windowType() == Qt.ToolTip
    )
    image = qimage_to_pil(tooltip.grab().toImage()).convert("RGB")
    image.save(tmp_path / f"{dialog_name}-{command}-tooltip.png")
    assert image.width > 50 and image.height > 10
    assert len(image.getcolors(maxcolors=1 << 20)) > 1
    assert calls == []
    QToolTip.hideText()
    dialog.close()
