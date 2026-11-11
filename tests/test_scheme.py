import chicago95ui
from PySide6.QtGui import QColor


def names(colors):
    return {name: color.name() for name, color in colors.items()}


def test_scheme_without_kdeglobals_is_the_1995_palette(tmp_path):
    assert names(chicago95ui.read_scheme(tmp_path / "kdeglobals")) == {
        "face": "#c0c0c0",
        "selection": "#000080",
        "selection_text": "#ffffff",
        "title_active": "#000080",
        "title_active_blend": "#000080",
        "title_active_text": "#ffffff",
        "title_inactive": "#808080",
        "title_inactive_blend": "#808080",
        "title_inactive_text": "#c0c0c0",
    }


def test_scheme_reads_title_gradient_and_face_written_by_system_settings(tmp_path):
    settings = tmp_path / "kdeglobals"
    settings.write_text(
        "[Colors:Window]\nBackgroundNormal=212,208,200\n\n[WM]\nactiveBackground=0,0,128\nactiveBlend=16,132,208\n"
    )

    scheme = names(chicago95ui.read_scheme(settings))

    assert (scheme["face"], scheme["title_active"], scheme["title_active_blend"]) == ("#d4d0c8", "#000080", "#1084d0")


def test_bevel_shades_of_c0c0c0_are_dfdfdf_and_808080():
    assert [shade.name() for shade in chicago95ui.bevel_shades(QColor("#C0C0C0"))] == ["#dfdfdf", "#808080"]


def test_sync_colors_passes_solid_titles_as_one_colour_and_gradients_as_two():
    from conftest import load_script

    sync = load_script("chicago95-sync-colors")
    scheme = chicago95ui.read_scheme("/nonexistent")
    scheme["title_active_blend"] = QColor("#1084D0")

    assert sync.decoration_arguments(scheme, "1998")[:4] == ["--active", "#000080,#1084d0", "--inactive", "#808080"]


def test_sync_colors_gives_the_2000_decoration_its_greys_and_gradient_ends():
    from conftest import load_script

    sync = load_script("chicago95-sync-colors")
    scheme = chicago95ui.read_scheme("/nonexistent")
    scheme["face"] = QColor("#D4D0C8")
    arguments = sync.decoration_arguments(scheme, "2000")
    options = dict(zip(arguments[::2], arguments[1::2], strict=False))

    assert {key: options[key] for key in ("--face", "--light", "--shadow", "--dark", "--gradient-margins")} == {
        "--face": "#d4d0c8",
        "--light": "#d4d0c8",
        "--shadow": "#808080",
        "--dark": "#404040",
        "--gradient-margins": "18,52",
    }


def test_icon_theme_is_chicago95_without_a_setting(tmp_path):
    assert chicago95ui.icon_theme(tmp_path / "kdeglobals") == "Chicago95"


def test_icon_theme_follows_the_set_chosen_with_the_look(tmp_path):
    settings = tmp_path / "kdeglobals"
    settings.write_text("[Icons]\nTheme=ClassicOS-2000\n")

    assert chicago95ui.icon_theme(settings) == "ClassicOS-2000"


def test_branding_falls_back_to_the_start_menu_banner(tmp_path):
    settings = tmp_path / "chicago95rc"
    settings.write_text("[StartMenu]\nbannerText=Fedora 44\n")

    look = chicago95ui.look_settings(settings)

    assert (look["osName"], look["osCompany"], look["edition"], look["companyLogo"]) == (
        "Fedora 44",
        "",
        "Professional",
        "",
    )


def test_branding_values_come_from_the_branding_group(tmp_path):
    settings = tmp_path / "chicago95rc"
    settings.write_text(
        "[StartMenu]\nbannerText=Chicago95\n\n[Branding]\nosCompany=Microsoft\n"
        "osName=Windows 2000\nosEdition=Professional\n"
    )

    look = chicago95ui.look_settings(settings)

    assert (look["osName"], look["osCompany"], look["bannerText"]) == ("Windows 2000", "Microsoft", "Chicago95")


def test_placeholders_fill_from_the_branding(tmp_path):
    settings = tmp_path / "chicago95rc"
    settings.write_text("[Branding]\nosCompany=Contoso\nosName=Windows2026\nosEdition=Home Edition\n")
    look = chicago95ui.look_settings(settings)

    assert (
        chicago95ui.fill_placeholders("Log On to {os} {edition} by {company}; {osname}", look)
        == "Log On to Windows Home Edition by Contoso; Windows2026"
    )


def test_sync_colors_runs_the_luna_aurorae_generator_into_the_luna_theme_when_decoration_is_luna():
    from conftest import load_script

    sync = load_script("chicago95-sync-colors")
    command = sync.decoration_command("luna", ["--active", "#000080"])

    assert command[1:] == [
        str(sync.LUNA_GENERATORS / "aurorae/make_luna_aurorae.py"),
        "--out",
        str(sync.LUNA_DECORATION),
    ]


def test_sync_colors_runs_the_flat_aurorae_generator_with_the_title_colours_when_decoration_is_classic():
    from conftest import load_script

    sync = load_script("chicago95-sync-colors")
    command = sync.decoration_command("classic", ["--active", "#000080"])

    assert command[1:] == [
        str(sync.DECORATION / "make_chicago95_aurorae.py"),
        "--out",
        str(sync.DECORATION),
        "--active",
        "#000080",
    ]


def test_sync_colors_builds_the_luna_plasma_style_on_the_flat_theme_when_taskbar_style_is_luna():
    from conftest import load_script

    sync = load_script("chicago95-sync-colors")
    scheme = chicago95ui.read_scheme("/nonexistent")

    assert sync.plasma_style_command("luna", scheme, "2000")[1:] == [
        str(sync.LUNA_GENERATORS / "plasma-style/make_luna_plasmastyle.py"),
        "--out",
        str(sync.LUNA_PLASMA_STYLE),
        "--base",
        str(sync.PLASMA_STYLE),
    ]


def test_look_settings_reads_the_taskbar_style_from_chicago95rc(tmp_path, monkeypatch):
    config = tmp_path / "chicago95rc"
    config.write_text("[Look]\ntaskbarStyle=luna\n")
    monkeypatch.setattr(chicago95ui, "CHICAGO95RC", str(config))

    assert chicago95ui.look_settings()["taskbarStyle"] == "luna"
