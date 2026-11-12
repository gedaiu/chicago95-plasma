import importlib.util
import sys
from pathlib import Path

import pytest
from conftest import REPO
from PIL import Image
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QFontMetrics, QIcon, QImage, QMouseEvent, QPainter, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu, QWidget
from reference import qimage_to_pil, screenshot

from . import luna_sprites
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
spec = importlib.util.spec_from_file_location("chicago95lunamenu", REPO / "luna/lib/chicago95lunamenu.py")
lunamenu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lunamenu)

PALETTE = lunamenu.START_MENU_PALETTE
REFERENCE_BOX = (0, 93, 380, 570)
TOLERANCE = 12
PREVIEW_DIR = Path(
    "/tmp/claude-1000/-home-gedaiu-workspace-chicago95-plasma/6679116e-4ef6-4478-b441-c6cd1dc95f4a/scratchpad/luna-preview"
)
MENU_MASKS = [
    (4, 4, 130, 62),
    (4, 66, 190, 154),
    (4, 158, 190, 399),
    (4, 401, 190, 436),
    (192, 66, 372, 234),
    (192, 237, 372, 306),
    (192, 309, 372, 436),
    (170, 440, 376, 472),
]
TEXT_FREE_HEADER_COLUMNS = range(140, 340)
TEXT_FREE_FOOTER_COLUMNS = range(4, 150)
EMPTY_RIGHT_ROWS = range(70, 100)
LEFT_ROW_FIRST_APP = 0
RIGHT_ROW_MY_COMPUTER_POINT = QPoint(350, 214)
SPRITE_HEADER_BUDGET, SPRITE_FOOTER_BUDGET, SPRITE_STRIP_BUDGET = 0.03, 0.01, 0.01
PLACES_LIST_LEFT = 190


def solid_icon(colour):
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor(colour))
    return QIcon(pixmap)


def fake_apps():
    apps = [
        {
            "name": "Firefox",
            "icon": "firefox",
            "categories": ["Network", "WebBrowser"],
            "path": "/apps/firefox.desktop",
        },
        {
            "name": "Thunderbird",
            "icon": "mail",
            "categories": ["Network", "Email"],
            "path": "/apps/thunderbird.desktop",
        },
    ]
    apps += [
        {
            "name": f"Tool {index}",
            "icon": f"tool{index}",
            "categories": ["Utility"],
            "path": f"/apps/tool{index}.desktop",
        }
        for index in range(8)
    ]
    return apps


def fake_icon(name_or_item):
    return solid_icon("#808080")


class FakeShield(QWidget):
    def __init__(self, on_click):
        super().__init__()
        self.on_click = on_click


def make_menu(launched, commands_run=None, recent_path=None, programs_filler=None):
    commands = {name: (lambda name=name: commands_run.append(name)) for name in lunamenu.COMMAND_NAMES}
    return lunamenu.LunaMenu(
        fake_apps(),
        ["/home/user/a.txt", "/home/user/b.txt"],
        launched.append,
        fake_icon,
        QMenu,
        FakeShield,
        user_name="Nathan",
        commands=commands if commands_run is not None else None,
        recent_path=recent_path,
        programs_filler=programs_filler,
    )


@pytest.fixture(autouse=True)
def menus_closed(qt_app):
    """Each test's menus are top-level windows: they go when it ends. Left open, they piled up until a later test's
    window crashed Qt while it attached to the screen."""
    yield
    for widget in QApplication.topLevelWidgets():
        if isinstance(widget, lunamenu.LunaMenu):
            widget.close()
            widget.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)


@pytest.fixture
def menu(qt_app):
    launched = []
    widget = make_menu(launched)
    widget.launched = launched
    yield widget
    widget.close()


@pytest.fixture
def grab(menu):
    return qimage_to_pil(menu.grab().toImage()), menu.grab().toImage()


@pytest.fixture(scope="module")
def reference():
    return screenshot("xpdesktop").crop(REFERENCE_BOX)


def hover(widget, point):
    position = QPointF(point)
    move = QMouseEvent(QEvent.MouseMove, position, position, Qt.NoButton, Qt.NoButton, Qt.NoModifier)
    QApplication.sendEvent(widget, move)


def tolerated(reference_profile, our_profile):
    return profile_excess(reference_profile, our_profile) <= TOLERANCE


def hex_colour(text):
    return tuple(int(text[index : index + 2], 16) for index in (1, 3, 5))


def near(a, b, tolerance=TOLERANCE):
    return all(abs(x - y) <= tolerance for x, y in zip(a, b, strict=True))


def test_menu_is_380_wide(grab):
    assert grab[0].width == 380


def test_menu_height_is_header_rule_columns_and_footer(menu):
    assert menu.height() == lunamenu.root_menu_height(menu.apps, menu.recent) == 64 + 2 + 370 + 41


def test_left_column_is_white_at_100_120(grab):
    assert grab[0].getpixel((100, 120)) == (255, 255, 255)


def test_right_column_is_d3e5fa_at_300_200(grab):
    assert near(grab[0].getpixel((300, 200)), hex_colour(PALETTE["right_column"]))


def test_divider_column_190_is_95bdee_between_the_columns(grab):
    assert [near(grab[0].getpixel((190, row)), hex_colour("#95BDEE")) for row in (70, 200, 430)] == [True] * 3


def test_top_corner_pixel_is_transparent_and_inside_pixel_opaque(grab):
    image = grab[1]
    assert (image.pixelColor(0, 0).alpha(), image.pixelColor(8, 8).alpha()) == (0, 255)


def test_bottom_corners_are_square(grab):
    image = grab[1]
    assert (image.pixelColor(0, image.height() - 1).alpha(), image.pixelColor(379, image.height() - 1).alpha()) == (
        255,
        255,
    )


def test_clicking_the_first_pinned_row_launches_the_browser(menu):
    menu.show()
    QTest.mouseClick(menu, Qt.LeftButton, Qt.NoModifier, QPoint(100, 90))
    assert menu.launched == [fake_apps()[0]]


def test_clicking_the_second_pinned_row_launches_the_mail_client(menu):
    menu.show()
    QTest.mouseClick(menu, Qt.LeftButton, Qt.NoModifier, QPoint(100, 130))
    assert menu.launched == [fake_apps()[1]]


def test_clicking_my_computer_runs_its_command(qt_app):
    commands_run = []
    widget = make_menu([], commands_run)
    widget.show()
    QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, RIGHT_ROW_MY_COMPUTER_POINT)
    assert commands_run == ["my_computer"]


def test_clicking_turn_off_computer_runs_shut_down(qt_app):
    commands_run = []
    widget = make_menu([], commands_run)
    widget.show()
    QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, QPoint(330, 456))
    assert commands_run == ["shut_down"]


def test_hovering_my_computer_paints_the_selection_blue_beside_its_text(menu):
    menu.show()
    hover(menu, RIGHT_ROW_MY_COMPUTER_POINT)
    image = qimage_to_pil(menu.grab().toImage())
    assert near(image.getpixel((360, 205)), hex_colour("#316AC5"))


def test_hover_leaves_other_right_rows_unpainted(menu):
    menu.show()
    hover(menu, RIGHT_ROW_MY_COMPUTER_POINT)
    image = qimage_to_pil(menu.grab().toImage())
    assert near(image.getpixel((360, 110)), hex_colour(PALETTE["right_column"]))


def test_down_arrow_hovers_the_first_row_and_enter_launches_it(menu):
    menu.show()
    QTest.keyClick(menu, Qt.Key_Down)
    QTest.keyClick(menu, Qt.Key_Return)
    assert menu.launched == [fake_apps()[0]]


def test_up_arrow_wraps_to_the_last_highlightable_row(menu):
    menu.show()
    QTest.keyClick(menu, Qt.Key_Up)
    assert menu.hovered.text == "Run..."


def test_escape_hides_the_menu(menu):
    menu.show()
    QTest.keyClick(menu, Qt.Key_Escape)
    assert not menu.isVisible()


def test_showing_the_menu_shows_the_click_shield_and_hiding_hides_it(menu):
    menu.show()
    shield = menu.shield
    shown = shield.isVisible()
    menu.hide()
    assert (shown, shield.isVisible()) == (True, False)


def test_most_used_rows_follow_the_usage_counter_file(qt_app, tmp_path):
    usage_file = tmp_path / "usage.json"
    usage_file.write_text('{"/apps/tool5.desktop": 9}')
    widget = make_menu([], recent_path=usage_file)
    assert [row.text for row in widget.rows if row.look is lunamenu.LEFT_LOOK][:1] == ["Tool 5"]


def test_launching_an_app_counts_it_in_the_usage_file(qt_app, tmp_path):
    usage_file = tmp_path / "usage.json"
    widget = make_menu([], recent_path=usage_file)
    widget.show()
    QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, QPoint(100, 90))
    assert usage_file.read_text() == '{"/apps/firefox.desktop": 1}'


def test_without_a_usage_file_the_first_apps_fill_the_most_used_rows(menu):
    assert [row.text for row in menu.rows if row.look is lunamenu.LEFT_LOOK] == [f"Tool {index}" for index in range(6)]


def test_pinned_rows_take_their_subtitle_from_the_default_apps(menu):
    assert [(row.text, row.subtitle) for row in menu.rows[:2]] == [("Internet", "Firefox"), ("E-mail", "Thunderbird")]


def test_all_programs_row_lists_the_apps_in_the_submenu(menu):
    submenu = QMenu()
    menu.rows[[row.text for row in menu.rows].index("All Programs")].submenu(submenu)
    assert [action.text() for action in submenu.actions()][:2] == ["Firefox", "Thunderbird"]


def test_my_recent_documents_row_lists_the_recent_files_in_the_submenu(menu):
    submenu = QMenu()
    menu.rows[[row.text for row in menu.rows].index("My Recent Documents")].submenu(submenu)
    assert [action.text() for action in submenu.actions()] == ["a.txt", "b.txt"]


def test_drawn_root_menu_returns_a_380_wide_image(qt_app):
    assert lunamenu.drawn_root_menu(fake_apps(), [], fake_icon, user_name="Nathan").width() == 380


def test_header_profile_over_text_free_columns_matches_the_reference_within_12(grab, reference):
    rows = range(64)
    assert tolerated(
        vertical_profile(reference, TEXT_FREE_HEADER_COLUMNS, rows),
        vertical_profile(grab[0], TEXT_FREE_HEADER_COLUMNS, rows),
    )


def test_footer_profile_left_of_the_buttons_matches_the_reference_within_12(grab, reference):
    rows = range(437, 477)
    assert tolerated(
        vertical_profile(reference, TEXT_FREE_FOOTER_COLUMNS, rows),
        vertical_profile(grab[0], TEXT_FREE_FOOTER_COLUMNS, rows),
    )


def test_orange_rule_profile_across_the_width_matches_the_reference_within_12(grab, reference):
    columns = range(4, 376)
    assert tolerated(horizontal_profile(reference, columns, [64, 65]), horizontal_profile(grab[0], columns, [64, 65]))


def test_right_column_fade_profile_matches_the_reference_within_12(grab, reference):
    columns = range(360, 379)
    assert tolerated(
        horizontal_profile(reference, columns, EMPTY_RIGHT_ROWS), horizontal_profile(grab[0], columns, EMPTY_RIGHT_ROWS)
    )


@pytest.mark.parametrize("columns", [range(2, 35), range(360, 379)], ids=["left side", "right side"])
def test_footer_side_shading_profile_matches_the_reference_within_12(grab, reference, columns):
    rows = [437, 438, 439, 440, 441, 442, 470, 472, 474, 476]
    assert tolerated(horizontal_profile(reference, columns, rows), horizontal_profile(grab[0], columns, rows))


def test_top_corner_edge_is_anti_aliased(grab):
    alphas = [grab[1].pixelColor(x, 1).alpha() for x in range(5)]
    assert alphas[0] == 0 and any(0 < alpha < 255 for alpha in alphas) and alphas[4] == 255


def test_top_corners_cut_the_reference_stair_of_3_2_1_1_pixels_within_one_pixel_per_row(grab):
    cut = [sum(grab[1].pixelColor(x, row).alpha() < 128 for x in range(8)) for row in range(4)]
    assert max(abs(ours - expected) for ours, expected in zip(cut, [3, 2, 1, 1], strict=True)) <= 1


def test_masked_menu_matches_the_reference_within_budget(grab, reference):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    assert differing_fraction(reference, grab[0], MENU_MASKS, PREVIEW_DIR / "startmenu-diff.png") <= RAW_BUDGET


def test_blurred_masked_menu_matches_the_blurred_reference_within_budget(grab, reference):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    assert (
        blurred_differing_fraction(reference, grab[0], MENU_MASKS, PREVIEW_DIR / "startmenu-blur-diff.png")
        <= BLURRED_BUDGET
    )


def test_preview_compares_the_menu_with_the_reference(grab, reference):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGB", (reference.width * 4, reference.height * 2), "#808080")
    sheet.paste(grab[0].resize((reference.width * 2, reference.height * 2), Image.NEAREST), (0, 0))
    sheet.paste(reference.resize((reference.width * 2, reference.height * 2), Image.NEAREST), (reference.width * 2, 0))
    sheet.save(PREVIEW_DIR / "startmenu-compare.png")
    assert sheet.size == (reference.width * 4, reference.height * 2)


@pytest.fixture(scope="module")
def painted_panels(qt_app):
    image = QImage(lunamenu.WIDTH, lunamenu.HEIGHT, QImage.Format_RGB32)
    image.fill(QColor("#FFFFFF"))
    painter = QPainter(image)
    lunamenu.paint_header(painter)
    lunamenu.paint_body(painter)
    lunamenu.paint_footer(painter)
    painter.end()
    return qimage_to_pil(image)


def places_and_programs_rule():
    rule = Image.new("RGBA", (lunamenu.WIDTH, lunamenu.RULE_HEIGHT))
    rule.paste(luna_sprites.stretched("StartPanel.ProgList", 0, 188, 4).crop((0, 1, 188, 3)), (2, 0))
    places = luna_sprites.stretched("StartPanel.PlacesList", 0, lunamenu.WIDTH - PLACES_LIST_LEFT, 6)
    rule.paste(places.crop((0, 1, places.width, 3)), (PLACES_LIST_LEFT, 0))
    return rule


@luna_sprites.requires_sprites
def test_header_gradient_matches_the_user_pane_bitmap_within_tolerance_12_and_3_percent(painted_panels):
    expected = luna_sprites.stretched("StartPanel.UserPane", 0, lunamenu.WIDTH, 63).crop((0, 1, lunamenu.WIDTH, 63))
    ours = painted_panels.crop((0, 0, lunamenu.WIDTH, 62))
    assert luna_sprites.differing_fraction(ours, expected) <= SPRITE_HEADER_BUDGET


@luna_sprites.requires_sprites
def test_footer_gradient_matches_the_logoff_bitmap_within_tolerance_12_and_1_percent(painted_panels):
    expected = luna_sprites.stretched("StartPanel.Logoff", 0, lunamenu.WIDTH, 39)
    ours = painted_panels.crop((0, lunamenu.FOOTER_TOP + 1, lunamenu.WIDTH, lunamenu.FOOTER_TOP + 40))
    assert luna_sprites.differing_fraction(ours, expected) <= SPRITE_FOOTER_BUDGET


@luna_sprites.requires_sprites
def test_orange_rule_matches_the_programs_and_places_bitmaps_within_tolerance_12_and_1_percent(painted_panels):
    box = (4, 0, 376, lunamenu.RULE_HEIGHT)
    ours = painted_panels.crop((0, lunamenu.HEADER_HEIGHT, lunamenu.WIDTH, lunamenu.BODY_TOP)).crop(box)
    assert luna_sprites.differing_fraction(ours, places_and_programs_rule().crop(box)) <= SPRITE_STRIP_BUDGET


@luna_sprites.requires_sprites
def test_right_column_fade_matches_the_places_bitmap_within_tolerance_12(painted_panels):
    places = luna_sprites.stretched("StartPanel.PlacesList", 0, lunamenu.WIDTH - PLACES_LIST_LEFT, 6)
    expected = places.crop((360 - PLACES_LIST_LEFT, 3, 379 - PLACES_LIST_LEFT, 4)).resize((19, 30), Image.NEAREST)
    ours = painted_panels.crop((360, 70, 379, 100))
    assert luna_sprites.differing_fraction(ours, expected) == 0


@luna_sprites.requires_sprites
def test_left_separator_colour_and_right_separator_colours_equal_the_separator_bitmaps():
    left = luna_sprites.sprite("StartPanel.ProgListSeparator", 0).getpixel((86, 0))[:3]
    right = [luna_sprites.sprite("StartPanel.PlacesListSeparator", 0).getpixel((67, row))[:3] for row in (0, 1)]
    assert (left, right) == (
        hex_colour(lunamenu.LEFT_SEPARATOR_COLOUR.name()),
        [hex_colour(colour.name()) for colour in lunamenu.RIGHT_SEPARATOR_COLOURS],
    )


def test_root_menu_is_a_frameless_top_level_window_kwin_places_by_its_title(qt_app):
    """Wayland refuses a grabbing popup without a parent window ("Failed to create grabbing popup"), so the menu
    never showed; the classic root menu is a top-level window that KWin's chicago95-startmenu-root rule places."""
    menu = make_menu([])
    flags = menu.windowFlags()

    assert (
        flags & Qt.WindowType_Mask == Qt.Window,
        bool(flags & Qt.FramelessWindowHint),
        bool(flags & Qt.WindowStaysOnTopHint),
        menu.windowTitle(),
    ) == (True, True, True, "chicago95-startmenu-root")


def test_submenus_hang_off_the_root_menu_so_wayland_has_a_parent_for_their_popup(qt_app):
    menu = make_menu([])
    menu.show()
    row = next(row for row in menu.rows if row.submenu is not None)
    menu.open_submenu(row)
    parent = menu.submenu.parentWidget()
    menu.submenu.close()
    menu.close()

    assert parent is menu


def test_the_footer_shows_log_off_and_turn_off_computer_in_full():
    rows = [row for row in make_menu([]).rows if row.look is lunamenu.FOOTER_LOOK]

    assert [lunamenu.row_title(row, QFontMetrics(lunamenu.ui_font(row.bold)), 1) for row in rows] == [
        "Log Off",
        "Turn Off Computer",
    ]


def test_all_programs_is_filled_by_the_menu_it_is_given_folders_and_all(qt_app):
    def folders(menu):
        accessories = QMenu("Accessories", menu)
        accessories.addAction("Calculator")
        menu.addMenu(accessories)

    menu = make_menu([], programs_filler=folders)
    menu.show()
    row = next(row for row in menu.rows if row.submenu is not None and row.text == "All Programs")
    menu.open_submenu(row)
    titles = [action.text() for action in menu.submenu.actions()]
    menu.submenu.close()
    menu.close()

    assert titles == ["Accessories"]


def test_the_all_programs_arrow_is_drawn_at_the_screens_own_resolution(qt_app):
    """A 16x24 bitmap stretched to 2x is made of 2x2 blocks; a vector arrow draws its edges in device pixels."""
    image = QImage(32, 48, QImage.Format_ARGB32_Premultiplied)
    image.setDevicePixelRatio(2)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    lunamenu.green_arrow_icon().paint(painter, 0, 0, 16, 24)
    painter.end()
    split_blocks = sum(
        len({image.pixel(x + dx, y + dy) for dx in (0, 1) for dy in (0, 1)}) > 1
        for x in range(0, 32, 2)
        for y in range(0, 48, 2)
    )

    assert split_blocks >= 30


def test_my_recent_documents_shows_its_title_in_full_beside_its_arrow(qt_app):
    row = next(row for row in make_menu([]).rows if row.text == "My Recent Documents")

    assert lunamenu.row_title(row, QFontMetrics(lunamenu.ui_font(row.bold)), lunamenu.row_room(row)) == row.text


def test_a_recent_folder_is_listed_by_its_own_name(qt_app):
    menu = lunamenu.LunaMenu([], ["/home/user/Pictures/", "/home/user/a.txt"], [].append, fake_icon, QMenu, FakeShield)
    recent = QMenu()
    menu.fill_recent_menu(recent)

    assert [action.text() for action in recent.actions()] == ["Pictures", "a.txt"]
