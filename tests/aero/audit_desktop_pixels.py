"""Exact 96-DPI comparisons. Run explicitly with run_visuals.py --exact-originals."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from aero_model import REFERENCE_DESKTOP
from conftest import REPO
from original_pixels import compare
from PIL import Image
from plasma_session import missing_programs
from reference import screenshot
from test_aero_greeter_visuals import greeter  # noqa: F401
from test_aero_gtk import aero_gtk_home, gtk4_pixels, gtk_captures, scroll_thumb_image  # noqa: F401
from test_aero_session import desktop, hidden_tray_icons  # noqa: F401
from test_aero_thunar import aero_icons, thunar_window  # noqa: F401
from test_switcher import imports  # noqa: F401


@pytest.fixture(scope="module")
def menu_renders(tmp_path_factory):
    folder = tmp_path_factory.mktemp("original-menu")
    config = folder / "config"
    config.mkdir()
    subprocess.run(
        [sys.executable, str(Path(__file__).with_name("render_aero_dialogs.py")), str(folder), "1"],
        env={**os.environ, "XDG_CONFIG_HOME": str(config)},
        check=True,
        timeout=45,
    )
    return folder


@pytest.mark.parametrize(
    ("scene", "reference", "box"),
    [
        ("programs", "win7allprograms", (365, 305, 400, 620)),  # clear glass beyond the labels
        ("programs", "win7allprograms", (8, 675, 260, 720)),  # search well and lens
        ("programs", "win7allprograms", (266, 684, 362, 711)),  # power split button
        ("start", "win7shutdown", (8, 675, 260, 720)),
        ("power-options", "win7shutdown", (362, 573, 473, 630)),  # first three commands, clear of hover and tooltip
    ],
    ids=["places-glass", "programs-search-box", "shut-down-button", "start-search-box", "power-menu"],
)
def test_menu_chrome(menu_renders, scene, reference, box, tmp_path):
    with Image.open(menu_renders / f"{scene}.png") as render:
        screen = Image.new("RGBA", (1024, 768), REFERENCE_DESKTOP)
        # Align to the actual shell anchors, preserving every source pixel and the widget's natural size.
        origin = (362, 573) if scene == "power-options" else (0, 728 - render.height)
        screen.alpha_composite(render.convert("RGBA"), origin)
    compare(screenshot(reference).crop(box), screen.crop(box), tmp_path / "windows7-comparison.png")


@pytest.mark.parametrize(
    ("name", "box"),
    [
        ("background", (500, 20, 620, 80)),
        ("empty-panel", (320, 728, 800, 768)),
        ("orb-ring", (0, 728, 58, 768)),
        ("running-button", (245, 728, 305, 768)),
        ("show-desktop", (1009, 728, 1024, 768)),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
@pytest.mark.skipif(bool(missing_programs()), reason=f"needs {', '.join(missing_programs())}")
def test_desktop_region(desktop, name, box, tmp_path):  # noqa: F811
    original = screenshot("win7screenres").crop(box)
    mask = None
    if name == "orb-ring":
        y, x = np.indices((40, 58))
        radius_squared = (x + 0.5 - 27) ** 2 + (y + 0.5 - 20) ** 2
        mask = (radius_squared >= 14**2) & (radius_squared <= 20**2)
    elif name == "running-button":
        mask = np.ones((40, 60), dtype=bool)
        mask[:, 10:50] = False  # different application icons
    compare(original, desktop.crop(box), tmp_path / "windows7-comparison.png", mask)


@pytest.mark.parametrize("box", [(840, 739, 861, 759), (770, 731, 838, 766)], ids=["hidden-arrow", "tray-shade"])
@pytest.mark.skipif(bool(missing_programs()), reason=f"needs {', '.join(missing_programs())}")
def test_notification_area(hidden_tray_icons, box, tmp_path):  # noqa: F811
    compare(screenshot("win7peek").crop(box), hidden_tray_icons.crop(box), tmp_path / "windows7-comparison.png")


def test_notification_close_and_options(menu_renders, tmp_path):
    # Both bodies have a 1px outline. Anchor on the upper-right body corner
    # and omit the variable title, sender icon, desktop and shadow.
    original = screenshot("win7-update-balloon").crop((279, 18, 323, 41))
    with Image.open(menu_renders / "balloon.png") as actual:
        box = (actual.width - 46, 5, actual.width - 2, 28)
        compare(original, actual.crop(box), tmp_path / "windows7-comparison.png")


def test_control_panel_navigation(tmp_path, aero_icons):  # noqa: F811
    from test_aero_control_panel import control_panel_config

    config = control_panel_config(tmp_path, aero_icons)
    output = tmp_path / "control-panel.png"
    subprocess.run(
        [sys.executable, str(REPO / "bin/chicago95-control-panel"), "--screenshot", str(output)],
        env={**os.environ, "HOME": str(tmp_path), "XDG_CONFIG_HOME": str(config), "QT_QPA_PLATFORM": "offscreen"},
        check=True,
        timeout=45,
    )
    # Navigation row from the back arrow through the breadcrumb, directly
    # below the caption. No category or installed-applet content in this crop.
    with Image.open(output) as actual:
        compare(
            screenshot("win7controlpanel").crop((9, 41, 229, 75)),
            actual.crop((0, 0, 220, 34)),
            tmp_path / "windows7-comparison.png",
        )


def test_explorer_navigation(tmp_path, thunar_window):  # noqa: F811
    compare(
        screenshot("win7explorer1").crop((7, 31, 227, 63)),
        thunar_window.crop((0, 0, 220, 32)),
        tmp_path / "windows7-comparison.png",
    )


@pytest.mark.skipif(not shutil.which("firefox"), reason="requires Firefox")
def test_firefox_button_face(tmp_path):
    from test_firefox_chrome import render_aero_dialog_buttons

    # The original Cancel button spans x=680..753 and y=558..578. Exclude
    # text and compare the left ten columns through the complete height.
    original = screenshot("win7screenres").crop((680, 558, 690, 579))
    with Image.open(render_aero_dialog_buttons(tmp_path, 74, 21)) as actual:
        # Firefox baseline-aligns the inline button, so its top depends on font metrics.
        y, x = np.nonzero(np.asarray(actual.convert("RGB"))[:, :100].min(axis=2) < 200)
        left, top = int(x.min()), int(y.min())
        compare(original, actual.crop((left, top, left + 10, top + 21)), tmp_path / "windows7-comparison.png")


def test_switcher_space_below_thumbnails(qt_app, imports, tmp_path):  # noqa: F811
    from test_switcher import THUMBNAIL, boxes, render

    original = screenshot("win7-flip-guide")
    actual = render(qt_app, imports, 0, preview_size=160, look="aero", windows=6)
    thumbnails = boxes(actual, THUMBNAIL)
    assert len(thumbnails) == 6
    # On the reduced reference the desktop thumbnail at right ends at row 32.
    # Compare the bottom inset as a fraction of panel height, allowing one source pixel.
    original_margin = original.height - 33
    actual_margin = actual.height - thumbnails[-1][3] - 1
    actual.save(tmp_path / "switcher.png")
    assert actual_margin / actual.height == pytest.approx(original_margin / original.height, abs=1 / original.height)


@pytest.mark.parametrize(
    ("control", "theme_class", "part_name", "state"),
    [
        ("palette button", "BUTTON", "PUSHBUTTON", 0),
        ("palette disabled-button", "BUTTON", "PUSHBUTTON", 3),
        ("palette entry", "EDIT", "EDITBORDER_NOSCROLL", 0),
        ("palette disabled-entry", "EDIT", "EDITBORDER_NOSCROLL", 3),
        ("progress empty-horizontal", "PROGRESS", "BAR", 0),
        ("scrollbar normal-horizontal", "SCROLLBAR", "THUMBBTNHORZ", 0),
        ("scrollbar normal-vertical", "SCROLLBAR", "THUMBBTNVERT", 0),
    ],
    ids=lambda value: value if isinstance(value, str) else str(value),
)
def test_gtk_fixed_corner(gtk4_pixels, control, theme_class, part_name, state, tmp_path):  # noqa: F811
    from aero_sprites import fixed_corner, sprites_available

    if not sprites_available():
        pytest.skip("requires the extracted Windows 7 control artwork")
    original = fixed_corner(theme_class, part_name, state)
    width, top = original.size
    captured = gtk4_pixels[control]
    if theme_class == "SCROLLBAR":
        captured = scroll_thumb_image(captured, control.split("-")[-1])
    actual = Image.fromarray(captured[:top, :width].astype("uint8"))
    compare(original, actual, tmp_path / "windows7-comparison.png")


def button_outlines(image):
    """Long horizontal border runs in a tight crop of the action row, independent of JPEG colour noise."""
    rows = np.asarray(image.convert("L")) < 212
    candidates = []
    for row in rows:
        edges = np.diff(np.pad(row.astype(int), (1, 1)))
        spans = [
            (a, b)
            for a, b in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1), strict=True)
            if image.width * 0.1 < b - a < image.width * 0.3
        ]
        candidates.append(spans)
    return max(candidates, key=len)


def test_advanced_system_properties_actions(menu_renders):
    with Image.open(REPO / "tests/references/win7-system-advanced-guide.jpg") as original:
        expected = button_outlines(original.crop((0, 590, original.width, 625)))
    with Image.open(menu_renders / "system-advanced.png") as actual:
        observed = button_outlines(actual.crop((0, actual.height - 36, actual.width, actual.height - 6)))
    assert len(expected) == 3, "original OK, Cancel and Apply buttons"
    assert len(observed) == len(expected)


def test_run_button_placement(menu_renders):
    native = screenshot("themes/win7/run")
    expected = button_outlines(native.crop((0, 214, native.width, 265)))
    with Image.open(menu_renders / "run.png") as actual:
        observed = button_outlines(actual.crop((0, actual.height - 50, actual.width, actual.height - 5)))
    assert len(observed) == len(expected) == 3
    # Compare the 96-DPI render against the native 144-DPI positions.
    assert [a / actual.width for a, _ in observed] == pytest.approx(
        [a / native.width for a, _ in expected], abs=2 / native.width
    )


def test_login_password_field_position(qt_app, greeter, tmp_path):  # noqa: F811
    from PySide6.QtCore import QUrl
    from PySide6.QtQuick import QQuickView
    from PySide6.QtTest import QTest
    from reference import qimage_to_pil

    folder, _ = greeter
    scene = folder / "guide-login.qml"
    scene.write_text("""import QtQuick
AeroLogin {
    width: 1024; height: 768; users: ["Demo"]; lastUser: "Demo"; sessions: []; lastSession: 0
    brandText: "Windows 7"; greeter: QtObject { signal loginFailed() }
}""")
    view = QQuickView()
    view.setSource(QUrl.fromLocalFile(str(scene)))
    assert not view.errors()
    view.show()
    try:
        QTest.qWait(100)
        actual = qimage_to_pil(view.grabWindow())
    finally:
        view.close()
    actual.save(tmp_path / "login.png")
    original = screenshot("win7-login-guide")

    def input_center_y(image):
        # The long contiguous white fill inside the password field remains visible at print scale.
        pixels = np.asarray(image.convert("RGB"))
        x0, x1 = round(0.47 * image.width), round(0.57 * image.width)
        rows = np.flatnonzero((pixels[:, x0:x1].min(axis=2) > 205).mean(axis=1) > 0.9)
        rows = rows[(rows > image.height * 0.55) & (rows < image.height * 0.8)]
        assert len(rows) >= 2
        return rows.mean() / image.height

    assert input_center_y(actual) == pytest.approx(input_center_y(original), abs=2 / original.height)


@pytest.fixture(scope="module")
def native_login_view(qt_app, greeter):  # noqa: F811
    from PySide6.QtCore import QUrl
    from PySide6.QtQuick import QQuickView
    from PySide6.QtTest import QTest
    from reference import qimage_to_pil

    folder, _ = greeter
    scene = folder / "native-login.qml"
    scene.write_text("""import QtQuick
AeroLogin {
    width: 800; height: 600; users: ["Reference"]; lastUser: "Reference"; sessions: []; lastSession: 0
    brandText: "Windows 7 Professional"
    greeter: QtObject {
        signal loginFailed()
        property bool canPowerOff: true
        property bool canReboot: true
    }
}""")
    view = QQuickView()
    view.setSource(QUrl.fromLocalFile(str(scene)))
    assert not view.errors()
    view.show()
    try:
        QTest.qWait(100)
        actual = qimage_to_pil(view.grabWindow())
    finally:
        view.close()
    return screenshot("themes/win7/sign-in"), actual


def test_login_compares_to_the_800_by_600_vm(native_login_view, tmp_path):
    expected, actual = native_login_view
    mask = np.ones((expected.height, expected.width), dtype=bool)
    # The login account's picture is personal. The rest of the frame, controls and captions stays in the test.
    mask[212:338, 336:462] = False
    compare(expected, actual, tmp_path / "login-comparison.png", mask)


def test_login_password_fill_matches_the_vm(native_login_view, tmp_path):
    expected, actual = native_login_view
    empty_field = (390, 414, 503, 430)
    compare(expected.crop(empty_field), actual.crop(empty_field), tmp_path / "password-comparison.png")
