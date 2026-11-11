"""The desktop icons component: the links Setup puts in ~/Desktop and the Folder View layout it asks Plasma for."""

import configparser
import re
import subprocess

import pytest
from conftest import REPO, load_script, run_bash_with_steps
from test_install import dry_run_log

ICON_THEME = REPO.parent / "Chicago95/Icons/Chicago95"


def desktop_script(tmp_path, assignments=""):
    return " ".join(" ".join(run_bash_with_steps(tmp_path, f"{assignments} desktop_script")).split())


def chosen(tmp_path, assignments=""):
    return run_bash_with_steps(tmp_path, f"{assignments} desktop_icons_chosen")


def link(name):
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(REPO / "config/desktop" / name)
    return dict(parser["Desktop Entry"])


def test_desktop_script_asks_folder_view_for_32px_icons_with_narrow_two_line_labels_in_left_columns(tmp_path):
    assert desktop_script(tmp_path) == (
        "desktops().forEach(desktop => { "
        'if (desktop.type !== "org.kde.plasma.folder") { print("desktop " + desktop.id + " is " + desktop.type + '
        '", not a Folder View: no desktop icons"); return; } '
        'desktop.currentConfigGroup = ["General"]; desktop.writeConfig("iconSize", 1); '
        'desktop.writeConfig("labelWidth", 0); desktop.writeConfig("textLines", 2); '
        'desktop.writeConfig("arrangement", 1); desktop.writeConfig("alignment", 0); desktop.reloadConfig(); });'
    )


def test_desktop_script_parses_as_javascript(qt_app, tmp_path):
    from PySide6.QtQml import QJSEngine, QJSValue

    assert QJSEngine().evaluate(desktop_script(tmp_path)).errorType() == QJSValue.ErrorType.ReferenceError


def test_1995_shows_my_computer_network_neighborhood_and_the_recycle_bin_and_later_looks_add_my_documents(tmp_path):
    assert (chosen(tmp_path), chosen(tmp_path, "SETUP_START_MENU_STYLE=1998"), chosen(tmp_path, "SETUP_START_MENU_STYLE=2000")) == (
        ["computer", "network", "recycle"],
        ["computer", "documents", "network", "recycle"],
        ["computer", "documents", "network", "recycle"],
    )


def test_a_saved_choice_picks_the_icons_and_an_empty_choice_or_an_unknown_name_gives_none(tmp_path):
    assert (
        chosen(tmp_path, "SETUP_DESKTOP_ICONS=recycle,computer"),
        chosen(tmp_path, "SETUP_DESKTOP_ICONS="),
        chosen(tmp_path, "SETUP_DESKTOP_ICONS='evil;rm -rf'"),
    ) == (["recycle", "computer"], [], [])


def test_dry_run_of_the_desktop_component_copies_the_links_under_their_names_into_the_desktop_folder(tmp_path):
    log = dry_run_log(tmp_path, "--components=desktop", "--look=1998")

    assert sorted(re.findall(r"would: cp \S+ (\S+/Desktop/.+\.desktop)", log)) == sorted(
        f"{tmp_path}/Desktop/{name}.desktop"
        for name in ("My Computer", "My Documents", "Network Neighborhood", "Recycle Bin")
    )


def test_the_2000_look_calls_the_network_my_network_places(tmp_path):
    log = dry_run_log(tmp_path, "--components=desktop", "--look=2000")

    assert ("my-network-places.desktop" in log, "Network Neighborhood" in log) == (True, False)


def test_a_settings_file_limits_the_icons_to_the_saved_ones(tmp_path):
    saved = tmp_path / "setup.conf"
    saved.write_text("DESKTOP_ICONS=recycle\n")
    log = dry_run_log(tmp_path, "--components=desktop", f"--settings={saved}")

    assert re.findall(r"would: cp \S+ \S+/Desktop/(.+)\.desktop", log) == ["Recycle Bin"]


def test_my_documents_link_points_into_the_home_folder_once_installed(tmp_path):
    (tmp_path / "stubs").mkdir()
    for command in ("systemctl", "gdbus", "kwriteconfig6"):
        (tmp_path / "stubs" / command).write_text("#!/bin/sh\nexit 0\n")
        (tmp_path / "stubs" / command).chmod(0o755)
    subprocess.run(
        [str(REPO / "install.sh"), "--plain", "--yes", "--components=desktop", "--look=1998"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=120,
        env={"PATH": f"{tmp_path / 'stubs'}:/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)},
        check=False,
    )

    assert f"URL=file://{tmp_path}/Documents" in (tmp_path / "Desktop/My Documents.desktop").read_text()


@pytest.mark.parametrize(
    "name, expected",
    [
        ("my-computer.desktop", {"type": "Link", "name": "My Computer", "icon": "computer", "url": "file:///"}),
        (
            "network-neighborhood.desktop",
            {"type": "Link", "name": "Network Neighborhood", "icon": "network-workgroup", "url": "remote:/"},
        ),
        (
            "my-network-places.desktop",
            {"type": "Link", "name": "My Network Places", "icon": "network-workgroup", "url": "remote:/"},
        ),
        (
            "trash.desktop",
            {
                "type": "Link",
                "name": "Recycle Bin",
                "icon": "user-trash-full",
                "emptyicon": "user-trash",
                "url": "trash:/",
            },
        ),
        (
            "my-documents.desktop",
            {"type": "Link", "name": "My Documents", "icon": "folder-documents", "url": "file://@HOME@/Documents"},
        ),
    ],
)
def test_each_link_names_its_place_and_a_chicago95_icon(name, expected):
    entry = link(name)
    icons = {key: value for key, value in entry.items() if key in ("icon", "emptyicon")}

    assert (
        {key: entry[key] for key in expected},
        [icon for icon in icons.values() if ICON_THEME.exists() and not list(ICON_THEME.glob(f"*/32/{icon}.png"))],
    ) == (expected, [])


def test_an_auto_choice_takes_the_looks_own_icons(tmp_path):
    assert chosen(tmp_path, "SETUP_DESKTOP_ICONS=auto SETUP_START_MENU_STYLE=1998") == [
        "computer",
        "documents",
        "network",
        "recycle",
    ]


def test_every_control_panel_choice_is_one_setup_understands(tmp_path):
    control_panel = load_script("chicago95-control-panel")

    assert [
        chosen(tmp_path, f"SETUP_DESKTOP_ICONS='{value}'") for _label, value in control_panel.DESKTOP_ICON_CHOICES
    ] == [
        ["computer", "network", "recycle"],
        [],
        ["computer", "network", "recycle"],
        ["computer", "documents", "network", "recycle"],
    ]


def test_effects_tab_offers_the_desktop_icon_sets_and_reports_the_saved_one(qt_app):
    control_panel = load_script("chicago95-control-panel")
    saved = control_panel.build_tab(
        "Display", "Effects", {"DESKTOP_ICONS": "computer,network,recycle"}, control_panel.Actions()
    )
    unset = control_panel.build_tab("Display", "Effects", {}, control_panel.Actions())

    assert (saved.values()["DESKTOP_ICONS"], unset.values()["DESKTOP_ICONS"]) == ("computer,network,recycle", "auto")
