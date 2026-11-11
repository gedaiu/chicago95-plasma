import chicago95ui
import pytest
from conftest import load_script
from PIL import Image
from reference import qimage_to_pil

REFERENCE = Image.open("tests/references/xpdisplayprop-1x.png").convert("RGB")
REFERENCE_SIZE = REFERENCE.size
CLIENT_ORIGIN = (3, 29)
FRAME_RIGHT_AND_BOTTOM = (3, 3)
BUTTON_ROW = 433
BUTTON_BORDER = "#003C74"
DISABLED_BORDER = "#C9C7BA"
PAGE_FRAME = "#919B9C"
WINDOW_FACE = (0xEC, 0xE9, 0xD8)
CAPTIONS = ["General", "Computer Name", "Hardware", "Advanced", "System Restore", "Automatic Updates", "Remote"]


def hex_colour(colour):
    return tuple(int(colour[index : index + 2], 16) for index in (1, 3, 5))


def button_borders(image, colour, row, origin_x=0):
    wanted = hex_colour(colour)
    return [x + origin_x for x in range(image.width) if image.getpixel((x, row)) == wanted]


@pytest.fixture(scope="module")
def sysprops(qt_app):
    return load_script("chicago95-sysprops")


@pytest.fixture(scope="module")
def facts(sysprops):
    return sysprops.SystemFacts(
        os_name="Fedora Linux 44",
        kernel="Linux 7.3.3",
        desktop="KDE Plasma 6.5 (Wayland)",
        owner="Doctor",
        hostname="TARDIS",
        product_key="01902-OEM-0087094-44427",
        cpu_model="GenuineIntel Pentium(r) II Processor",
        logical_processors="8 logical processors",
        memory="16 GB RAM",
        display="800x600 at 1x",
        resources_free="90% free",
        filesystem="Btrfs",
        virtual_memory="8 GB swap",
    )


@pytest.fixture(scope="module")
def luna_dialog(sysprops, facts, qt_app, tmp_path_factory):
    config = tmp_path_factory.mktemp("luna-sysprops") / "chicago95rc"
    config.write_text("[StartMenu]\nstyle=luna\n[Look]\nwidgetStyle=luna\n")
    original_config = chicago95ui.CHICAGO95RC
    chicago95ui.CHICAGO95RC = str(config)
    chicago95ui.apply_style(qt_app)
    dialog = sysprops.build_window(facts, "luna")
    dialog.show()
    qt_app.processEvents()
    yield dialog
    dialog.close()
    chicago95ui.CHICAGO95RC = original_config
    chicago95ui.apply_style(qt_app)


@pytest.fixture(scope="module")
def picture(luna_dialog):
    return qimage_to_pil(luna_dialog.grab().toImage())


def reference_borders(colour):
    return button_borders(REFERENCE, colour, BUTTON_ROW)


def our_borders(picture, colour):
    return button_borders(picture, colour, BUTTON_ROW - CLIENT_ORIGIN[1], CLIENT_ORIGIN[0])


def test_dialog_is_the_display_properties_window_less_its_frame_and_title(luna_dialog):
    expected = (
        REFERENCE_SIZE[0] - CLIENT_ORIGIN[0] - FRAME_RIGHT_AND_BOTTOM[0],
        REFERENCE_SIZE[1] - CLIENT_ORIGIN[1] - FRAME_RIGHT_AND_BOTTOM[1],
    )
    assert (luna_dialog.width(), luna_dialog.height()) == expected


def test_tabs_hold_the_seven_windows_xp_captions_in_order(luna_dialog):
    assert [luna_dialog.tabs.tabText(index) for index in range(luna_dialog.tabs.count())] == CAPTIONS


def test_ok_and_cancel_buttons_have_xp_display_properties_borders(picture):
    expected = [column for column in reference_borders(BUTTON_BORDER) if column < 320]
    assert [column for column in our_borders(picture, BUTTON_BORDER) if column < 320] == expected


def test_apply_button_has_xp_display_properties_disabled_borders(picture):
    expected = [column for column in reference_borders(DISABLED_BORDER) if column > 320]
    assert [column for column in our_borders(picture, DISABLED_BORDER) if column > 320] == expected


def test_dialog_background_is_the_luna_face(picture):
    assert picture.getpixel((1, 1)) == WINDOW_FACE


def test_page_frame_is_drawn_by_the_luna_style_in_its_border_colour(picture):
    assert picture.getpixel((6 + 150, 27 + 100 + 150)) != WINDOW_FACE
    assert picture.getpixel((6, 27 + 200)) == hex_colour(PAGE_FRAME)


def test_luna_widget_style_picks_the_xp_sheet_whatever_the_start_menu_style(sysprops, facts, luna_look):
    luna_look.write_text("[StartMenu]\nstyle=1995\n[Look]\nwidgetStyle=luna\n")
    assert not isinstance(sysprops.build_window(facts), chicago95ui.ClassicDialog)


def test_classic_widget_style_keeps_the_classic_sheet_under_the_luna_start_menu_style(sysprops, facts, luna_look):
    luna_look.write_text("[StartMenu]\nstyle=luna\n[Look]\nwidgetStyle=classic\n")
    assert isinstance(sysprops.build_window(facts), chicago95ui.ClassicDialog)


def test_luna_sheet_draws_no_classic_bevel_or_navy_title_pixels_and_saves_its_preview(picture):
    from .luna_tools_support import has_classic_bevel, save_preview

    save_preview("sysprops", picture, REFERENCE.crop((3, 29, REFERENCE_SIZE[0] - 3, REFERENCE_SIZE[1] - 3)))
    assert not has_classic_bevel(picture)
