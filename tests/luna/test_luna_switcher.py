import shutil
from pathlib import Path

import pytest
from conftest import REPO
from test_switcher import BOX_WIDTH, CELL, ICON, PER_ROW, STUBS, THUMBNAIL, TITLES, UI, boxes, render

PREVIEW_DIR = Path(
    "/tmp/claude-1000/-home-gedaiu-workspace-chicago95-plasma/6679116e-4ef6-4478-b441-c6cd1dc95f4a/scratchpad/luna-preview"
)
FACE, BLACK, WHITE = (236, 233, 216), (0, 0, 0), (255, 255, 255)
SELECTION = (49, 106, 197)
NAVY, CLASSIC_FACE = (0, 0, 128), (192, 192, 192)
GRID_TOP = 21
ROW_LEFT = (BOX_WIDTH - 3 * CELL) // 2


@pytest.fixture(scope="module")
def stub_imports(tmp_path_factory):
    folder = tmp_path_factory.mktemp("qml-stubs")
    for name, text in STUBS.items():
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(text)
    return folder


@pytest.fixture(scope="module")
def installed_ui(tmp_path_factory):
    folder = tmp_path_factory.mktemp("installed-ui")
    shutil.copytree(UI, folder, dirs_exist_ok=True)
    shutil.copytree(REPO / "luna/kwin-tabbox", folder / "luna")
    return folder


def render_luna(qt_app, stub_imports, installed_ui, current_index=0, **options):
    return render(qt_app, stub_imports, current_index, look="luna", ui=installed_ui, **options)


def test_the_box_is_379_wide_with_a_black_border_a_2px_white_line_and_the_xp_face(qt_app, stub_imports, installed_ui):
    image = render_luna(qt_app, stub_imports, installed_ui)
    right, bottom = image.width - 1, image.height - 1

    assert [image.getpixel(point) for point in ((5, 0), (0, 5), (right, 5), (5, bottom), (5, 1), (5, 2), (5, 3))] == [
        BLACK,
        BLACK,
        BLACK,
        BLACK,
        WHITE,
        WHITE,
        FACE,
    ]
    assert image.width == BOX_WIDTH


def test_the_chosen_window_is_a_flat_selection_blue_square_with_no_frame(qt_app, stub_imports, installed_ui):
    image = render_luna(qt_app, stub_imports, installed_ui, current_index=1)
    left = ROW_LEFT + CELL

    assert [
        image.getpixel(point) for point in ((left, GRID_TOP), (left + 1, GRID_TOP + 1), (left - 3, GRID_TOP + 1))
    ] == [
        SELECTION,
        SELECTION,
        FACE,
    ]


def test_icons_sit_on_a_48px_pitch_32px_wide_seven_to_a_row(qt_app, stub_imports, installed_ui):
    image = render_luna(qt_app, stub_imports, installed_ui, windows=8)
    first_row = boxes(image.crop((0, 0, image.width, GRID_TOP + CELL)), ICON)
    second_row = boxes(image.crop((0, GRID_TOP + CELL, image.width, GRID_TOP + 2 * CELL)), ICON)

    assert (
        [right - left + 1 for left, _top, right, _bottom in first_row],
        [first_row[index + 1][0] - first_row[index][0] for index in range(len(first_row) - 1)],
        len(first_row),
        len(second_row),
    ) == ([32] * PER_ROW, [CELL] * (PER_ROW - 1), PER_ROW, 1)


def test_the_chosen_title_is_black_ink_centred_under_the_icons(qt_app, stub_imports, installed_ui):
    image = render_luna(qt_app, stub_imports, installed_ui)
    caption = image.crop((4, GRID_TOP + CELL + 4, image.width - 4, image.height - 4))
    ink = boxes(caption, BLACK)
    left, right = min(box[0] for box in ink) + 4, max(box[2] for box in ink) + 4

    assert abs((left + right) / 2 - BOX_WIDTH / 2) <= 3


def test_the_box_has_no_classic_navy_frame_or_grey_face(qt_app, stub_imports, installed_ui):
    image = render_luna(qt_app, stub_imports, installed_ui, current_index=1)

    assert (boxes(image, NAVY), image.getpixel((20, 10))) == ([], FACE)


def test_the_flat_1995_look_still_draws_the_classic_grey_box_beside_the_luna_files(qt_app, stub_imports, installed_ui):
    image = render(qt_app, stub_imports, 1, look="1995", ui=installed_ui)

    assert (image.getpixel((20, 10)), len(boxes(image, NAVY))) == (CLASSIC_FACE, 1)


def test_with_a_preview_size_chosen_the_box_stays_the_icon_grid_without_thumbnails(qt_app, stub_imports, installed_ui):
    image = render_luna(qt_app, stub_imports, installed_ui, preview_size=160)

    assert (image.width, boxes(image, THUMBNAIL), len(boxes(image, ICON))) == (BOX_WIDTH, [], 3)


def test_preview_sheet_shows_eight_windows_with_the_second_chosen(qt_app, stub_imports, installed_ui):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    image = render_luna(qt_app, stub_imports, installed_ui, current_index=1, windows=8)
    image.save(PREVIEW_DIR / "switcher.png")

    assert (image.width, len(TITLES)) == (BOX_WIDTH, 8)
