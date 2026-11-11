"""A task button's tooltip (plasmoids/org.chicago95.tasks TaskToolTip.qml): the window's title on the classic pale
yellow inside a 1px black border, and with the Control Panel's preview size a live picture of the window above it.
Rendered offscreen with stubs for the screencast items (a solid blue square), as a real session cannot hover."""

import re

import pytest
from conftest import REPO
from PySide6.QtCore import QUrl
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest
from reference import qimage_to_pil
from test_install import taskbar_script_written
from test_quick_launch_drop import qml_block

UI = REPO / "plasmoids/org.chicago95.tasks/contents/ui"
YELLOW, BLACK, SHADOW, WHITE, PICTURE = (255, 255, 225), (0, 0, 0), (128, 128, 128), (255, 255, 255), (64, 128, 192)
STUBS = {
    "org/kde/pipewire/qmldir": "module org.kde.pipewire\nPipeWireSourceItem 1.0 PipeWireSourceItem.qml\n",
    "org/kde/pipewire/PipeWireSourceItem.qml": "import QtQuick\nRectangle { property var nodeId; color: '#4080c0' }\n",
    "org/kde/taskmanager/qmldir": "module org.kde.taskmanager\nScreencastingRequest 1.0 ScreencastingRequest.qml\n",
    "org/kde/taskmanager/ScreencastingRequest.qml": (
        "import QtQuick\nQtObject { property string uuid; property int nodeId: 1 }\n"
    ),
}


@pytest.fixture(scope="module")
def imports(tmp_path_factory):
    folder = tmp_path_factory.mktemp("qml-stubs")
    for name, text in STUBS.items():
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(text)
    return folder


def render(qt_app, imports, preview_size):
    view = QQuickView()
    view.engine().addImportPath(str(imports))
    view.setSource(QUrl.fromLocalFile(str(UI / "TaskToolTip.qml")))
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


def test_with_a_preview_size_the_window_picture_sits_above_the_title_in_a_sunken_frame(qt_app, imports):
    image = render(qt_app, imports, 160)

    assert (
        image.getpixel((4, 4)),
        image.getpixel((5, 5)),
        image.getpixel((5 + 159, 5 + 119)),
        image.getpixel((4 + 161, 4 + 121)),
        image.width,
        image.getpixel((40, 4 + 122 + 4 + 2)),
    ) == (SHADOW, PICTURE, PICTURE, WHITE, 2 + 6 + 162, YELLOW)


def test_the_task_button_shows_the_tooltip_with_the_windows_id_and_the_configured_preview_size():
    button = qml_block((UI / "main.qml").read_text(), "id: windowButton")

    assert (
        "PlasmaCore.ToolTipArea {" in button,
        re.search(r"windowId: entry\.model\.WinIdList \? entry\.model\.WinIdList\[0\] : null", button) is not None,
        "previewSize: Plasmoid.configuration.previewSize ?? 0" in button,
    ) == (True, True, True)


@pytest.mark.parametrize("saved, written", [("", 0), ("SETUP_PREVIEW_SIZE=240", 240), ("SETUP_PREVIEW_SIZE=7", 0)])
def test_setup_writes_the_preview_size_into_the_task_list(tmp_path, saved, written):
    assert f"widget.writeConfig('previewSize', {written});" in taskbar_script_written(tmp_path, saved)
