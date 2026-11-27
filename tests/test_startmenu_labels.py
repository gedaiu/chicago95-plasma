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

    monkeypatch.setattr(startmenu, "suspend_available", lambda: False)

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


def test_1995_keeps_its_root_labels(root_items):
    assert labels(root_items("1995")) == ROOT_LABELS_CLASSIC


def test_1995_shows_suspend_on_supported_machines(startmenu, qt_app, monkeypatch):
    calls = []
    monkeypatch.setattr(startmenu, "suspend_available", lambda: True)
    monkeypatch.setattr(startmenu, "launch", calls.append)
    menu = startmenu.build_root_menu()
    actions = menu.actions()
    suspend = next(index for index, action in enumerate(actions) if action.text() == "Suspe&nd")
    assert actions[suspend - 1].isSeparator()
    actions[suspend].trigger()
    assert calls == [["systemctl", "suspend"]]


def test_1998_has_aligned_update_and_favorites_rows_with_its_log_off_user(root_items):
    programs, *remaining = ROOT_LABELS_CLASSIC
    assert labels(root_items("1998")) == [
        "Windows Update", programs, "Favorites", *remaining[:-2], f"Log Off {getpass.getuser()}...", remaining[-1]
    ]


def test_2000_calls_its_find_menu_search(root_items):
    assert labels(root_items("2000")) == ["Search" if label == "Find" else label for label in ROOT_LABELS_CLASSIC]


def test_1998_update_and_favorites_open_the_project_links(startmenu, qt_app, tmp_path, monkeypatch):
    settings = tmp_path / "chicago95rc"
    settings.write_text("[StartMenu]\nstyle=1998\n")
    calls = []
    monkeypatch.setattr(startmenu, "SETTINGS_FILE", settings)
    monkeypatch.setattr(startmenu, "launch", calls.append)
    menu = startmenu.build_root_menu()
    menu.actions()[0].trigger()
    favorites = next(action.menu() for action in menu.actions() if action.text() == "F&avorites")
    favorites.actions()[-1].trigger()
    assert calls == [
        ["xdg-open", "https://github.com/gedaiu/chicago95-plasma/releases"],
        ["xdg-open", "https://github.com/gedaiu/chicago95-plasma"],
    ]


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
