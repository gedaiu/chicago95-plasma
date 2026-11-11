import colorsys
import shutil
import sys
from pathlib import Path

import pytest
from conftest import REPO
from PIL import Image
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtQuick import QQuickItem, QQuickView
from reference import close, qimage_to_pil, screenshot
from screencast_stubs import write_stubs

sys.path.insert(0, str(REPO / "luna"))
from palette import PALETTE  # noqa: E402

PANEL_HEIGHT = 30
BACKGROUND = (255, 0, 255)
PIXEL_BUDGET = 0.03
START_PIXEL_BUDGET = 0.02
OFF_POINTER = 40
QML_ROOTS = [Path("/usr/lib64/qt6/qml"), Path("/usr/lib/qt6/qml"), Path("/usr/lib/x86_64-linux-gnu/qt6/qml")]
PACKAGES = ["org.chicago95.start", "org.chicago95.tasks", "org.chicago95.trayframe"]
STRIP = """import QtQuick
import org.kde.ksvg as KSvg
import "%(folder)s"
Rectangle {
    width: %(width)d; height: %(height)d
    color: "#ff00ff"
    Component.onCompleted: {
        KSvg.ImageSet.basePath = "%(themes)s"
        KSvg.ImageSet.imageSetName = "Chicago95Luna"
    }
    Column {
        Repeater {
            model: %(rows)s
            Rectangle { required property string modelData; width: %(width)d; height: 1; color: modelData }
        }
    }
    %(component)s { objectName: "item"; x: %(x)d; width: %(item_width)d; height: %(height)d }
}
"""


@pytest.fixture(scope="module")
def qml_root():
    found = next((root for root in QML_ROOTS if (root / "org/kde/ksvg").is_dir()), None)
    return found or pytest.skip("KSvg's QML module is not installed")


@pytest.fixture(scope="module")
def installed(tmp_path_factory):
    """The plasmoid packages with the Luna files laid over them, as step_taskbar installs them."""
    root = tmp_path_factory.mktemp("plasmoids")
    for package in PACKAGES:
        shutil.copytree(REPO / "plasmoids" / package / "contents", root / package / "contents")
        shutil.copytree(REPO / "luna/plasmoids" / package / "contents", root / package / "contents", dirs_exist_ok=True)
        shutil.copy(REPO / "luna/plasmoids/family.js", root / package / "contents/ui/luna/family.js")
    themes = tmp_path_factory.mktemp("themes")
    shutil.copytree(REPO / "luna/plasma-style/theme", themes / "Chicago95Luna")
    return root, themes


def panel_colour(row):
    return tuple(int(PALETTE["taskbar"][row][index : index + 2], 16) for index in (1, 3, 5))


def hex_rows(rows):
    return "[" + ", ".join(f'"{row}"' for row in rows) + "]"


def render(qt_app, qml_root, installed, tmp_path, package, component, width, properties=None, panel=True):
    packages, themes = installed
    rows = PALETTE["taskbar"] if panel else ["#ff00ff"] * PANEL_HEIGHT
    (tmp_path / "strip.qml").write_text(
        STRIP
        % {
            "folder": (packages / package / "contents/ui/luna").as_uri(),
            "themes": themes,
            "width": OFF_POINTER + width,
            "height": PANEL_HEIGHT,
            "rows": hex_rows(rows),
            "component": component,
            "x": OFF_POINTER,
            "item_width": width,
        }
    )
    view = QQuickView()
    view.engine().addImportPath(str(qml_root))
    view.engine().addImportPath(str(write_stubs(tmp_path / "qml-stubs")))  # prepended: searched before qml_root
    view.setSource(QUrl.fromLocalFile(str(tmp_path / "strip.qml")))
    assert [error.toString() for error in view.errors()] == []
    item = view.rootObject().findChild(QQuickItem, "item")
    for key, value in (properties or {}).items():
        item.setProperty(key, value)
    view.show()
    QTimer.singleShot(300, qt_app.quit)
    qt_app.exec()
    image = qimage_to_pil(view.grabWindow())
    view.close()
    return image.crop((OFF_POINTER, 0, OFF_POINTER + width, PANEL_HEIGHT))


def render_start(qt_app, qml_root, installed, tmp_path, **properties):
    return render(qt_app, qml_root, installed, tmp_path, "org.chicago95.start", "StartButton", 98, properties)


def render_task(qt_app, qml_root, installed, tmp_path, **properties):
    return render(qt_app, qml_root, installed, tmp_path, "org.chicago95.tasks", "TaskButton", 160, properties)


def test_task_button_draws_the_pill_from_the_luna_plasma_theme(qt_app, qml_root, installed, tmp_path):
    """KSvg finds an image set by name in the data directories alone: a basePath of its own never reached the
    frame items, and the buttons were bare text on the panel."""
    image = render_task(qt_app, qml_root, installed, tmp_path, text="Document - Notepad", pressed=False)

    assert image.getpixel((80, 15)) != panel_colour(15) and image.getpixel((80, 1)) == panel_colour(1)


def column(image, x, rows):
    return [image.getpixel((x, row)) for row in rows]


def columns_close(ours, expected):
    return all(close(a, b) for a, b in zip(ours, expected, strict=True))


def brightness(colour):
    return sum(colour)


def pixels_outside_masks_not_close(ours, original, masks):
    count = 0
    for x in range(ours.width):
        for y in range(ours.height):
            if any(left <= x < right and top <= y < bottom for left, top, right, bottom in masks):
                continue
            count += not close(ours.getpixel((x, y)), original.getpixel((x, y)))
    return count


@pytest.fixture(scope="module")
def running():
    return screenshot("xprunning")


@pytest.fixture(scope="module")
def taskbar():
    return screenshot("xptaskbar-1x")


def test_start_button_is_98_by_30_with_a_transparent_top_right_corner(qt_app, qml_root, installed, tmp_path):
    image = render_start(qt_app, qml_root, installed, tmp_path, text="")
    assert (image.size, image.getpixel((97, 0))) == ((98, 30), panel_colour(0))


def test_start_button_centre_column_x_30_equals_the_xptaskbar_pill_within_12(
    qt_app, qml_root, installed, tmp_path, taskbar
):
    image = render_start(qt_app, qml_root, installed, tmp_path, text="")
    assert columns_close(column(image, 30, range(30)), column(taskbar, 30, range(30)))


def test_start_button_pressed_is_darker_than_normal_at_mid_height(qt_app, qml_root, installed, tmp_path):
    normal = render_start(qt_app, qml_root, installed, tmp_path, text="")
    pressed = render_start(qt_app, qml_root, installed, tmp_path, text="", held=True)
    assert brightness(pressed.getpixel((30, 15))) < brightness(normal.getpixel((30, 15)))


def test_start_button_body_rows_6_to_24_masked_against_xprunning_stay_in_the_start_pixel_budget(
    qt_app, qml_root, installed, tmp_path, running
):
    image = render_start(qt_app, qml_root, installed, tmp_path, text="")
    pill = running.crop((0, 0, 98, PANEL_HEIGHT))
    masks = [(0, 0, 98, 6), (0, 25, 98, 30), (6, 4, 34, 27), (33, 6, 78, 25)]
    assert pixels_outside_masks_not_close(image, pill, masks) <= START_PIXEL_BUDGET * 98 * PANEL_HEIGHT


def test_start_button_letters_and_flag_put_ink_where_the_xp_pill_has_it(qt_app, qml_root, installed, tmp_path, taskbar):
    with_ink = render_start(qt_app, qml_root, installed, tmp_path, text="Start")
    without = render_start(qt_app, qml_root, installed, tmp_path, text="")
    ink = [(x, y) for x in range(98) for y in range(30) if with_ink.getpixel((x, y)) != without.getpixel((x, y))]
    xs, ys = [x for x, _ in ink], [y for _, y in ink]
    assert (min(xs) >= 30, max(xs) <= 80, min(ys) >= 6, max(ys) <= 24) == (True, True, True, True)


def test_flag_images_are_24_by_22_and_48_by_44():
    images = REPO / "luna/plasmoids/org.chicago95.start/contents/images"
    assert [Image.open(images / name).size for name in ("logo-flag-xp.png", "logo-flag-xp@2x.png")] == [
        (24, 22),
        (48, 44),
    ]


def hue_degrees(colour):
    return round(colorsys.rgb_to_hsv(*(channel / 255 for channel in colour))[0] * 360)


def test_flag_has_an_orange_green_blue_and_yellow_pane():
    flag = Image.open(REPO / "luna/plasmoids/org.chicago95.start/contents/images/logo-flag-xp.png").convert("RGB")
    panes = [flag.getpixel(point) for point in ((9, 6), (18, 7), (6, 14), (16, 16))]
    assert [hue_degrees(pane) for pane in panes] == pytest.approx([20, 75, 205, 49], abs=12)


TOOLTIP_FILL, BORDER = (255, 255, 225), (0, 0, 0)
TOOLTIP_WIDTH = 100


def render_tooltip(qt_app, qml_root, installed, tmp_path, title="My Computer"):
    return render(
        qt_app,
        qml_root,
        installed,
        tmp_path,
        "org.chicago95.tasks",
        "TaskToolTip",
        TOOLTIP_WIDTH,
        {"title": title},
        panel=False,
    )


def test_tooltip_is_fffe1_inside_a_1px_black_border_with_square_corners(qt_app, qml_root, installed, tmp_path):
    image = render_tooltip(qt_app, qml_root, installed, tmp_path)
    corners = [image.getpixel(point) for point in ((0, 0), (TOOLTIP_WIDTH - 1, 0), (0, 29), (TOOLTIP_WIDTH - 1, 29))]
    assert (corners, image.getpixel((1, 1)), image.getpixel((TOOLTIP_WIDTH - 2, 28))) == (
        [BORDER] * 4,
        TOOLTIP_FILL,
        TOOLTIP_FILL,
    )


def test_tooltip_title_is_black_ink_inside_3px_of_padding(qt_app, qml_root, installed, tmp_path):
    image = render_tooltip(qt_app, qml_root, installed, tmp_path)
    ink = [(x, y) for x in range(1, TOOLTIP_WIDTH - 1) for y in range(1, 29) if sum(image.getpixel((x, y))) < 200]
    assert (min(x for x, _ in ink) >= 4, min(y for _, y in ink) >= 4, len(ink) > 20) == (True, True, True)


def test_tooltip_streams_the_window_preview_through_the_same_screencast_as_the_classic_one(qt_app, qml_root, installed):
    packages, _themes = installed
    text = (packages / "org.chicago95.tasks/contents/ui/luna/TaskToolTip.qml").read_text()
    assert ("PipeWire.PipeWireSourceItem" in text, "TaskManager.ScreencastingRequest" in text) == (True, True)
