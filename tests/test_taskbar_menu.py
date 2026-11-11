"""The taskbar's right-click menu (plasmoids/org.chicago95.tasks), as the Windows 98 original's
(tests/references/win98taskbarmenu.png): the toolbar, Cascade Windows, Tile Windows Horizontally, Tile Windows
Vertically, Minimize All Windows with an Undo of the last arrangement, and Properties."""

import re

from conftest import REPO
from test_install import dry_run_log, kwriteconfig

MAIN_QML = (REPO / "plasmoids/org.chicago95.tasks/contents/ui/main.qml").read_text()


def menu_entries():
    start = MAIN_QML.index("Plasmoid.contextualActions: [")
    actions = MAIN_QML[start : MAIN_QML.index("\n    ]\n", start)]
    return [
        "-" if "isSeparator: true" in action else re.search(r'i18n\("([^"]*)"', action).group(1)
        for action in re.findall(r"PlasmaCore\.Action \{.*?\n        \}", actions, re.S)
    ]


def test_the_menu_lists_the_originals_entries_in_their_order():
    assert menu_entries() == [
        "Quick Launch",
        "-",
        "Cascade Windows",
        "Tile Windows Horizontally",
        "Tile Windows Vertically",
        "-",
        "Minimize All Windows",
        "Undo %1",
        "-",
        "Properties",
    ]


def test_each_arrangement_invokes_the_scripts_shortcut_through_kglobalaccels_kwin_component():
    assert (
        re.findall(r'root\.arrange\("(\w+)"', MAIN_QML),
        "--object-path /component/kwin --method org.kde.kglobalaccel.Component.invokeShortcut " in MAIN_QML,
    ) == (
        [
            "Chicago95CascadeWindows",
            "Chicago95TileWindowsHorizontally",
            "Chicago95TileWindowsVertically",
            "Chicago95MinimizeAllWindows",
            "Chicago95UndoArrangement",
        ],
        True,
    )


def test_setups_taskbar_component_installs_the_arrangement_script_and_switches_it_on(tmp_path):
    log = dry_run_log(tmp_path, "--components=taskbar")

    assert (
        "~/.local/share/kwin/scripts/chicago95windows/contents/code/main.js" in log.replace(str(tmp_path), "~"),
        kwriteconfig("kwinrc", "Plugins", "chicago95windowsEnabled", "true") in log,
    ) == (True, True)
