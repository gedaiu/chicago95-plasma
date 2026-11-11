"""Alt+Tab (kwin-tabbox/chicago95): the classic grey box with the windows' icons in a row and the chosen window's
title under them, or window previews at the size chosen in the Control Panel. The box is rendered offscreen with
stubs for KWin's thumbnail and Kirigami's icon (plain coloured squares), so every frame and cell is measured.
No screenshot of the original box has been found: the metrics are the classic ones (43px cells, 32px icons,
a 1px black frame around the chosen one) and are pinned here until an original can be compared."""

import pytest
from conftest import REPO, run_bash_with_steps
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest
from reference import qimage_to_pil
from test_install import dry_run_log, kwriteconfig

UI = REPO / "kwin-tabbox/chicago95/contents/ui"
ICON, THUMBNAIL = (0, 200, 0), (64, 128, 192)
FACE, LIGHT, SHADOW, WHITE, BLACK = (192, 192, 192), (223, 223, 223), (128, 128, 128), (255, 255, 255), (0, 0, 0)
CELL, INSET = 43, 9  # a cell's pitch; the grid's offset from the box's corner (2px frame, 7px in)

STUBS = {
    "org/kde/kwin/qmldir": "module org.kde.kwin\nWindowThumbnail 1.0 WindowThumbnail.qml\n",
    "org/kde/kwin/WindowThumbnail.qml": "import QtQuick\nRectangle { property var wId; color: '#4080c0' }\n",
    "org/kde/kirigami/qmldir": "module org.kde.kirigami\nIcon 1.0 Icon.qml\n",
    "org/kde/kirigami/Icon.qml": (
        "import QtQuick\nRectangle { property var source; property bool roundToIconSize; color: '#00c800' }\n"
    ),
}
WINDOWS = """
import QtQuick
ListModel {
    ListElement { caption: "My Computer"; icon: "computer"; windowId: "1" }
    ListElement { caption: "Untitled - Notepad"; icon: "text"; windowId: "2" }
    ListElement { caption: "Recycle Bin"; icon: "trash"; windowId: "3" }
}
"""


@pytest.fixture(scope="module")
def imports(tmp_path_factory):
    folder = tmp_path_factory.mktemp("qml-stubs")
    for name, text in STUBS.items():
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(text)
    return folder


def render(qt_app, imports, current_index, preview_size=0, look="1995"):
    view = QQuickView()
    view.engine().addImportPath(str(imports))
    model = QQmlComponent(view.engine())
    model.setData(WINDOWS.encode(), QUrl())
    windows = model.create()
    assert windows is not None, model.errorString()
    view.setSource(QUrl.fromLocalFile(str(UI / "SwitcherBox.qml")))
    box = view.rootObject()
    assert box is not None, [error.toString() for error in view.errors()]
    box.setProperty("model", windows)
    box.setProperty("currentIndex", current_index)
    box.setProperty("previewSize", preview_size)
    box.setProperty("look", look)
    view.resize(int(box.width()), int(box.height()))
    view.show()
    QTest.qWaitForWindowExposed(view)
    qt_app.processEvents()
    image = qimage_to_pil(view.grabWindow())
    view.close()
    return image


def boxes(image, colour):
    """(left, top, right, bottom) of each block of a colour, left to right."""
    columns = [x for x in range(image.width) if any(image.getpixel((x, y)) == colour for y in range(image.height))]
    blocks = []
    for x in columns:
        if blocks and x == blocks[-1][-1] + 1:
            blocks[-1].append(x)
        else:
            blocks.append([x])
    found = []
    for block in blocks:
        rows = [y for y in range(image.height) if any(image.getpixel((x, y)) == colour for x in block)]
        found.append((block[0], rows[0], block[-1], rows[-1]))
    return found


def test_the_box_holds_three_43px_cells_with_32px_icons_and_the_title_field_under_them(qt_app, imports):
    image = render(qt_app, imports, 0)

    assert (image.size, boxes(image, ICON)) == (
        (2 * INSET + 3 * CELL, 2 * INSET + CELL + 4 + 21),
        [(INSET + 5 + CELL * column, INSET + 5, INSET + 5 + CELL * column + 31, INSET + 5 + 31) for column in range(3)],
    )


def test_the_frame_is_raised_light_and_white_above_and_left_dark_and_shadow_below_and_right(qt_app, imports):
    image = render(qt_app, imports, 0)
    right, bottom = image.width - 1, image.height - 1

    assert [
        image.getpixel(point)
        for point in ((5, 0), (0, 5), (5, 1), (1, 5), (5, bottom), (right, 5), (5, bottom - 1), (right - 1, 5), (20, 4))
    ] == [
        LIGHT,
        LIGHT,
        WHITE,
        WHITE,
        BLACK,
        BLACK,
        SHADOW,
        SHADOW,
        FACE,
    ]


def test_the_chosen_window_gets_a_1px_black_frame_a_pixel_inside_its_cell(qt_app, imports):
    image = render(qt_app, imports, 1)
    cell_left, cell_top = INSET + CELL, INSET

    assert (
        boxes(image.crop((2, 2, image.width - 2, INSET + CELL)), BLACK),
        image.getpixel((cell_left + 1, cell_top + 1)),
        image.getpixel((cell_left + 2, cell_top + 2)),
    ) == ([(cell_left - 1, cell_top - 1, cell_left + CELL - 4, cell_top + CELL - 4)], BLACK, FACE)


def test_the_title_field_is_sunken_and_white_under_the_grid(qt_app, imports):
    image = render(qt_app, imports, 0)
    top = INSET + CELL + 4
    left = INSET

    assert [
        image.getpixel(point)
        for point in (
            (left + 30, top),
            (left, top + 10),
            (left + 30, top + 1),
            (left + 30, top + 20),
            (left + 30, top + 19),
            (left + 30, top + 10),
        )
    ] == [
        SHADOW,
        SHADOW,
        BLACK,
        LIGHT,
        WHITE,
        WHITE,
    ]


def test_with_previews_each_cell_shows_the_window_at_the_chosen_width_in_a_sunken_frame_with_its_icon(qt_app, imports):
    image = render(qt_app, imports, 0, preview_size=160)
    first = (INSET + 5, INSET + 5)

    assert (
        image.size[0],
        boxes(image, THUMBNAIL)[0],
        image.getpixel(first),
        image.getpixel((first[0] + 159, first[1] + 119)),
        boxes(image.crop((first[0], first[1], first[0] + 160, first[1] + 120)), ICON),
    ) == (
        2 * INSET + 3 * 170,
        (first[0] + 1, first[1] + 1, first[0] + 158, first[1] + 118),
        SHADOW,
        WHITE,
        [(160 - 19, 120 - 19, 160 - 4, 120 - 4)],
    )


def test_the_2000_look_bevels_with_the_face_and_dark_grey(qt_app, imports):
    image = render(qt_app, imports, 0, look="2000")

    assert (image.getpixel((5, 0)), image.getpixel((5, image.height - 1))) == (FACE, (64, 64, 64))


def test_setup_installs_the_layout_writes_its_settings_and_chooses_it_in_kwinrc(tmp_path):
    saved = tmp_path / "setup.conf"
    saved.write_text("PREVIEW_SIZE=240\n")
    log = dry_run_log(tmp_path, "--components=switcher", "--look=2000", f"--settings={saved}").replace(
        str(tmp_path), "~"
    )

    assert (
        "contents/ui/SwitcherBox.qml -> ~/.local/share/kwin/tabbox/chicago95/contents/ui/SwitcherBox.qml" in log,
        "would: tee ~/.local/share/kwin/tabbox/chicago95/contents/ui/settings.js" in log,
        "(Alt+Tab: previews 240, look 2000)" in log,
        kwriteconfig("kwinrc", "TabBox", "LayoutName", "chicago95") in log,
        kwriteconfig("kwinrc", "TabBox", "ShowTabBox", "true") in log,
        kwriteconfig("kwinrc", "TabBox", "HighlightWindows", "false") in log,
    ) == (True, True, True, True, True, True)


@pytest.mark.parametrize(
    "saved, size",
    [
        ("", "0"),
        ("SETUP_PREVIEW_SIZE=240", "240"),
        ("SETUP_PREVIEW_SIZE=999", "0"),
        ("SETUP_PREVIEW_SIZE='1; evil'", "0"),
    ],
)
def test_the_preview_size_is_one_of_the_offered_sizes_or_off(tmp_path, saved, size):
    assert run_bash_with_steps(tmp_path, f"{saved} preview_size") == [size]


def test_the_switcher_settings_carry_the_2000_face_as_hex(tmp_path):
    run_bash_with_steps(
        tmp_path,
        f"SETUP_DRY_RUN=0 SETUP_MENU_STYLE=2000 SETUP_FACE=212,208,200 SETUP_PREVIEW_SIZE=160;"
        f" write_switcher_settings {tmp_path}",
    )

    assert (
        tmp_path / "settings.js"
    ).read_text() == '.pragma library\nvar previewSize = 160;\nvar look = "2000";\nvar face = "#D4D0C8";\n'
