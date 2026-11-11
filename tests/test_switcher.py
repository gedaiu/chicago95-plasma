"""Alt+Tab (kwin-tabbox/chicago95) against the 1995 original (tests/references/win95alttab.png, a smoothed 4.625x
capture, so its rules and positions are measured, not its pixels): a 379px box with a raised 2px frame, 48px cells
seven to a row with 32px icons, a single row centred, the chosen window in a 1px navy frame, and a 27px sunken field
16px in from the sides with the title in bold. Further rows wrap as the classic box did (win8classicalttab.png).
With a preview size chosen in the Control Panel the cells hold window previews instead. The box is rendered offscreen
with stubs for KWin's thumbnail and Kirigami's icon (plain coloured squares)."""

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
NAVY = (0, 0, 128)
BOX_WIDTH, CELL, TOP, PER_ROW = 379, 48, 20, 7  # the box; a cell's pitch; the first row's top; cells per row
FIELD_TOP, FIELD_HEIGHT, FIELD_INSET = 78, 27, 16  # the caption field under one row
ROW_LEFT = (BOX_WIDTH - 3 * CELL) // 2  # three cells centred

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
%s
}
"""
TITLES = [
    "My Computer",
    "Exploring - Windows",
    "Untitled - Notepad",
    "Recycle Bin",
    "Paint",
    "Solitaire",
    "Calculator",
    "Minesweeper",
]


@pytest.fixture(scope="module")
def imports(tmp_path_factory):
    folder = tmp_path_factory.mktemp("qml-stubs")
    for name, text in STUBS.items():
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(text)
    return folder


def render(qt_app, imports, current_index, preview_size=0, look="1995", windows=3):
    view = QQuickView()
    view.engine().addImportPath(str(imports))
    model = QQmlComponent(view.engine())
    elements = "\n".join(
        f'    ListElement {{ caption: "{title}"; icon: "icon{index}"; windowId: "{index}" }}'
        for index, title in enumerate(TITLES[:windows])
    )
    model.setData((WINDOWS % elements).encode(), QUrl())
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


def test_three_windows_sit_in_one_centred_row_of_48px_cells_in_the_379px_box(qt_app, imports):
    image = render(qt_app, imports, 0)

    assert (image.size, boxes(image, ICON)) == (
        (BOX_WIDTH, 116),
        [
            (ROW_LEFT + 8 + CELL * column, TOP + 8, ROW_LEFT + 8 + CELL * column + 31, TOP + 8 + 31)
            for column in range(3)
        ],
    )


def test_the_frame_is_raised_light_and_white_above_and_left_dark_and_shadow_below_and_right(qt_app, imports):
    image = render(qt_app, imports, 0)
    right, bottom = image.width - 1, image.height - 1
    probes = ((5, 0), (0, 5), (5, 1), (1, 5), (5, bottom), (right, 5), (5, bottom - 1), (right - 1, 5), (20, 4))

    assert [image.getpixel(point) for point in probes] == [
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


def test_the_chosen_window_gets_a_1px_navy_frame_on_its_cells_edge(qt_app, imports):
    image = render(qt_app, imports, 1)
    cell_left = ROW_LEFT + CELL

    assert (
        boxes(image.crop((2, 2, image.width - 2, TOP + CELL + 2)), NAVY),
        image.getpixel((cell_left, TOP)),
        image.getpixel((cell_left + 1, TOP + 1)),
    ) == ([(cell_left - 2, TOP - 2, cell_left + CELL - 3, TOP + CELL - 3)], NAVY, FACE)


def test_the_title_field_is_sunken_on_the_face_with_the_title_in_bold_four_pixels_in(qt_app, imports):
    image = render(qt_app, imports, 0)
    left, top, right = FIELD_INSET, FIELD_TOP, BOX_WIDTH - FIELD_INSET - 1
    field = image.crop((left + 2, top + 2, right - 1, top + FIELD_HEIGHT - 2))
    ink = boxes(field, BLACK)

    assert (
        [
            image.getpixel(point)
            for point in (
                (left + 30, top),
                (left, top + 10),
                (left + 30, top + 1),
                (right, top + 10),
                (left + 30, top + FIELD_HEIGHT - 1),
                (left + 30, top + FIELD_HEIGHT - 2),
                (right - 40, top + 5),
            )
        ],
        ink[0][0] + 2,
        ink[0][1] + 2 in range(8, 11),
        max(bottom for _l, _t, _r, bottom in ink) + 2 <= 21,
    ) == ([SHADOW, SHADOW, BLACK, WHITE, WHITE, LIGHT, FACE], 4, True, True)


def test_eight_windows_wrap_into_a_second_row_from_the_left_pad(qt_app, imports):
    image = render(qt_app, imports, 0, windows=8)
    icons = boxes(image.crop((0, 0, image.width, TOP + CELL)), ICON)
    second = boxes(image.crop((0, TOP + CELL, image.width, TOP + 2 * CELL)), ICON)

    assert (image.size, len(icons), icons[0][0], second) == (
        (BOX_WIDTH, 116 + CELL),
        PER_ROW,
        2 + 19 + 8,
        [(2 + 19 + 8, 8, 2 + 19 + 8 + 31, 8 + 31)],
    )


def test_with_previews_each_cell_shows_the_window_at_the_chosen_width_in_a_sunken_frame_with_its_icon(qt_app, imports):
    image = render(qt_app, imports, 0, preview_size=160)
    first = (2 + 19 + 5, TOP + 5)

    assert (
        image.size[0],
        boxes(image, THUMBNAIL)[0],
        image.getpixel(first),
        image.getpixel((first[0] + 159, first[1] + 119)),
        boxes(image.crop((first[0], first[1], first[0] + 160, first[1] + 120)), ICON),
    ) == (
        2 * (2 + 19) + 3 * 170,
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
