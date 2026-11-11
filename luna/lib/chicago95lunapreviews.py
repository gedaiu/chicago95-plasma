"""The Windows XP parts the Control Panel's previews draw with: the Luna QML trees laid beside the splash and
log-on screens that load them, and the Luna taskbar's Start and task buttons on the panel's rows."""

import shutil
from pathlib import Path

from chicago95lunacontrolpanel import PALETTE

QML_ROOTS = (Path("/usr/lib64/qt6/qml"), Path("/usr/lib/qt6/qml"), Path("/usr/lib/x86_64-linux-gnu/qt6/qml"))
SCREEN_TREES = ("qml", "images")
TASK_GAP = 3
PANEL_HEIGHT = 30
FRAME_IMPORTS = """import QtQuick
import org.kde.ksvg as KSvg
"""
PANEL_ROWS = """    color: "#ff00ff"
    Component.onCompleted: {
        KSvg.ImageSet.basePath = "%(themes)s"
        KSvg.ImageSet.imageSetName = "Chicago95Luna"
    }
    Column {
        Repeater {
            model: panelRows
            Rectangle { required property string modelData; width: parent.parent.width; height: 1; color: modelData }
        }
    }
"""
START_SCENE = (
    FRAME_IMPORTS
    + """import "%(start)s" as Start
Rectangle {
"""
    + PANEL_ROWS
    + """    Start.StartButton { objectName: "startButton"; width: 98; height: %(height)d; text: startText; held: true }
}
"""
)
TASKS_SCENE = (
    FRAME_IMPORTS
    + """import "%(tasks)s" as Tasks
Rectangle {
"""
    + PANEL_ROWS
    + """    Tasks.TaskButton {
        objectName: "windowButton"
        width: taskWidth; height: %(height)d
        text: "Document - Notepad"; icon: "text-x-generic"
    }
    Tasks.TaskButton {
        objectName: "activeButton"
        x: taskWidth + %(gap)d; width: taskWidth; height: %(height)d
        text: "My Computer"; icon: "text-x-generic"; pressed: true
    }
}
"""
)
WORDMARK_SCENE = """import QtQuick
import "luna/qml"
Rectangle {
    color: "#000000"
    XpWordmark {
        anchors.centerIn: parent
        unit: 1.1
        edition: wordmarkEdition
        textColor: "#efefef"
    }
}
"""


def qml_import_root():
    return next((root for root in QML_ROOTS if (root / "org/kde/ksvg").is_dir()), None)


def copy_screen_trees(luna_root, destination, *screens):
    """luna/qml, luna/images and the given screens' folders in destination, where the screen's Loader finds them."""
    for name in (*SCREEN_TREES, *screens):
        shutil.copytree(Path(luna_root) / name, Path(destination) / name, dirs_exist_ok=True)


def copy_panel_parts(luna_root, folder):
    """The Luna Start button and task button QML beside their images, and the Luna panel theme, in folder."""
    luna_root, folder = Path(luna_root), Path(folder)
    plasmoids = luna_root / "plasmoids"
    for plasmoid in ("start", "tasks"):
        shutil.copytree(
            plasmoids / f"org.chicago95.{plasmoid}/contents/ui/luna", folder / plasmoid / "contents/ui/luna"
        )
    shutil.copy(plasmoids / "family.js", folder / "tasks/contents/ui/luna/family.js")
    (folder / "start/contents/images").mkdir(parents=True)
    shutil.copy(luna_root / "images/windows-xp-flag.svg", folder / "start/contents/images")
    shutil.copytree(luna_root / "plasma-style/theme", folder / "themes/Chicago95Luna")


def panel_scene(template, folder):
    folder = Path(folder)
    return template % {
        "themes": folder / "themes",
        "start": (folder / "start/contents/ui/luna").as_uri(),
        "tasks": (folder / "tasks/contents/ui/luna").as_uri(),
        "height": PANEL_HEIGHT,
        "gap": TASK_GAP,
    }


def panel_rows():
    return list(PALETTE["taskbar"])
