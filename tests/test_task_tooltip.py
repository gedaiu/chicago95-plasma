"""A task button's tooltip (plasmoids/org.chicago95.tasks TaskToolTip.qml): the window's title on the classic pale
yellow inside a 1px black border; with the Control Panel's preview size, a raised grey panel with the title along the
top and a live picture of the window in a sunken frame under it, as Windows 7 laid its previews out.
Rendered offscreen with stubs for the screencast items (a solid blue square), as a real session cannot hover."""

import re

import pytest
from conftest import REPO
from PySide6.QtCore import QUrl
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest
from reference import qimage_to_pil
from screencast_stubs import PICTURE, write_stubs
from test_install import taskbar_script_written
from test_quick_launch_drop import qml_block

UI = REPO / "plasmoids/org.chicago95.tasks/contents/ui"
LUNA_UI = REPO / "luna/plasmoids/org.chicago95.tasks/contents/ui/luna"
YELLOW, BLACK, SHADOW, WHITE = (255, 255, 225), (0, 0, 0), (128, 128, 128), (255, 255, 255)
FACE, LIGHT = (192, 192, 192), (223, 223, 223)


@pytest.fixture(scope="module")
def imports(tmp_path_factory):
    return write_stubs(tmp_path_factory.mktemp("qml-stubs"))


def render(qt_app, imports, preview_size, source=UI / "TaskToolTip.qml"):
    view = QQuickView()
    view.engine().addImportPath(str(imports))
    view.setSource(QUrl.fromLocalFile(str(source)))
    tip = view.rootObject()
    assert tip is not None, [error.toString() for error in view.errors()]
    tip.setProperty("title", "Untitled - Notepad")
    tip.setProperty("windowId", "window-1")
    tip.setProperty("previewSize", preview_size)
    view.resize(int(tip.width()), int(tip.height()))
    view.show()
    QTest.qWaitForWindowExposed(view)
    qt_app.processEvents()
    image = qimage_to_pil(view.grabWindow())
    view.close()
    return image


def test_the_tooltip_is_the_title_on_pale_yellow_inside_a_1px_black_border(qt_app, imports):
    image = render(qt_app, imports, 0)
    ink = [
        x for x in range(1, image.width - 1) if any(image.getpixel((x, y)) == BLACK for y in range(2, image.height - 2))
    ]

    assert (
        image.getpixel((0, 0)),
        image.getpixel((image.width - 1, image.height - 1)),
        image.getpixel((1, 1)),
        image.getpixel((2, 2)),
        ink[0] >= 4,
        image.height < 24,
    ) == (BLACK, BLACK, YELLOW, YELLOW, True, True)


def test_with_a_preview_size_the_panel_is_raised_grey_with_the_title_above_the_picture_in_a_sunken_frame(
    qt_app, imports
):
    image = render(qt_app, imports, 160)
    right, bottom = image.width - 1, image.height - 1
    title_rows = [y for y in range(2, 30) if any(image.getpixel((x, y)) == BLACK for x in range(8, 60))]
    picture_top = next(y for y in range(8, image.height) if image.getpixel((9, y)) == PICTURE)

    assert (
        [
            image.getpixel(point)
            for point in ((5, 0), (5, 1), (5, bottom), (5, bottom - 1), (right, 5), (right - 1, 5), (20, 4))
        ],
        image.width,
        title_rows[0] >= 8 and title_rows[-1] < picture_top - 4,
        image.getpixel((9, picture_top - 1)),
        image.getpixel((8, picture_top)),
        image.getpixel((9, picture_top)),
        image.getpixel((9 + 159, picture_top + 119)),
        image.getpixel((8 + 161, picture_top + 120)),
        bottom - (picture_top + 120),
    ) == (
        [LIGHT, WHITE, BLACK, SHADOW, BLACK, SHADOW, FACE],
        2 * 8 + 162,
        True,
        SHADOW,
        SHADOW,
        PICTURE,
        PICTURE,
        WHITE,
        8,
    )


def test_the_luna_tooltip_with_a_preview_size_keeps_its_yellow_box_and_shows_the_picture_under_the_title(
    qt_app, imports
):
    image = render(qt_app, imports, 160, LUNA_UI / "TaskToolTip.qml")
    picture_top = next(y for y in range(4, image.height) if image.getpixel((5, y)) == PICTURE)
    title_rows = [y for y in range(2, picture_top - 1) if any(image.getpixel((x, y)) == BLACK for x in range(6, 60))]

    assert (
        image.getpixel((0, 0)),
        image.getpixel((1, 1)),
        image.width,
        title_rows[0] >= 4 and title_rows[-1] < picture_top - 2,
        image.getpixel((5, picture_top - 1)),
        image.getpixel((4, picture_top)),
        image.getpixel((5 + 159, picture_top + 119)),
        image.getpixel((5 + 160, picture_top + 120)),
        image.height - (picture_top + 120),
    ) == (BLACK, YELLOW, 2 * 4 + 162, True, BLACK, BLACK, PICTURE, BLACK, 5)


def test_the_task_button_shows_the_tooltip_over_its_drag_area_with_the_windows_id_and_the_preview_size():
    button = qml_block((UI / "main.qml").read_text(), "id: windowButton")

    tooltip_area = qml_block(button, "PlasmaCore.ToolTipArea {")

    assert (
        "DragSortArea {" in tooltip_area,
        re.search(r"windowId: entry\.model\.WinIdList \? entry\.model\.WinIdList\[0\] : null", button) is not None,
        "previewSize: Plasmoid.configuration.previewSize ?? 0" in button,
    ) == (True, True, True)


@pytest.mark.parametrize("saved, written", [("", 0), ("SETUP_PREVIEW_SIZE=240", 240), ("SETUP_PREVIEW_SIZE=7", 0)])
def test_setup_writes_the_preview_size_into_the_task_list(tmp_path, saved, written):
    assert f"widget.writeConfig('previewSize', {written});" in taskbar_script_written(tmp_path, saved)
