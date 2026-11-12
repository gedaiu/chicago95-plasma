import colorsys
import getpass

import pytest

ROOT_LABELS_2001 = [
    "Windows Catalog",
    "Windows Update",
    "Programs",
    "Documents",
    "Settings",
    "Search",
    "Help and Support",
    "Run...",
    f"Log Off {getpass.getuser()}...",
    "Turn Off Computer...",
]
ROOT_LABELS_CLASSIC = ["Programs", "Documents", "Settings", "Find", "Help", "Run...", "Log Off...", "Shut Down..."]


@pytest.fixture
def root_items(startmenu, qt_app, tmp_path, monkeypatch):
    """(label without mnemonic, is separator) for each root menu item of the style."""

    def items_of(style):
        settings = tmp_path / "chicago95rc"
        settings.write_text(f"[StartMenu]\nstyle={style}\n")
        monkeypatch.setattr(startmenu, "SETTINGS_FILE", settings)
        menu = startmenu.build_root_menu()
        return [(action.text().replace("&", ""), action.isSeparator()) for action in menu.actions()]

    return items_of


def labels(items):
    return [label for label, is_separator in items if not is_separator]


def test_2001_root_menu_lists_the_xp_classic_items(root_items):
    assert labels(root_items("2001")) == ROOT_LABELS_2001


@pytest.mark.parametrize("style", ["1995", "1998", "2000"])
def test_older_styles_keep_their_root_labels(root_items, style):
    assert labels(root_items(style)) == ROOT_LABELS_CLASSIC


def test_2001_has_a_separator_below_the_software_items(root_items):
    assert [is_separator for _, is_separator in root_items("2001")[:4]] == [False, False, True, False]


PANE_HUE_RANGES = {"orange": range(10, 30), "yellow": range(42, 58), "green": range(65, 90), "blue": range(195, 215)}


def opaque_hues(logo):
    pixels = (logo.getpixel((x, y)) for x in range(logo.width) for y in range(logo.height))
    return {
        round(colorsys.rgb_to_hsv(*(channel / 255 for channel in pixel[:3]))[0] * 360)
        for pixel in pixels
        if pixel[3] > 200
    }


def test_2001_logo_renderer_draws_a_16px_flag_with_the_four_pane_hues_and_transparent_corners():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).parent.parent / "luna/images/render_logo.py"
    spec = importlib.util.spec_from_file_location("render_logo", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    logo = module.render_flag((16, 16))
    corner_alphas = [logo.getpixel(corner)[3] <= 8 for corner in ((0, 0), (15, 0), (0, 15), (15, 15))]
    hues = opaque_hues(logo)
    panes_present = {name: any(hue in hue_range for hue in hues) for name, hue_range in PANE_HUE_RANGES.items()}
    assert (logo.size, corner_alphas, panes_present) == (
        (16, 16),
        [True] * 4,
        {"orange": True, "yellow": True, "green": True, "blue": True},
    )
