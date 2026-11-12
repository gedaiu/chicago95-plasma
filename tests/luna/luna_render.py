"""Luna pieces drawn straight from their modules, for tests/render_report.py: the taskbar, the Start menu, the
Turn Off dialog, a window frame, the controls and the splash and log-on screens, each as a PIL image."""

import importlib.util
import shutil
import sys
from pathlib import Path

from conftest import REPO
from luna_gallery import luna_gallery, style_tree
from luna_model import LunaWindow, build_luna_theme
from PIL import Image
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtQuick import QQuickView
from reference import qimage_to_pil

sys.path.insert(0, str(REPO / "luna"))
from palette import PALETTE  # noqa: E402

LUNA_LIB = REPO / "luna/lib"
PANEL_HEIGHT, SCREEN_WIDTH = 30, 800
OFF_POINTER = 40  # the offscreen pointer rests at the window's corner and would hover whatever sits there
QML_ROOTS = [Path("/usr/lib64/qt6/qml"), Path("/usr/lib/qt6/qml"), Path("/usr/lib/x86_64-linux-gnu/qt6/qml")]
PACKAGES = ["org.chicago95.start", "org.chicago95.tasks", "org.chicago95.trayframe"]
# xprunning.png: the Start pill, three task buttons (the last pressed) and the tray box, left edges and widths
START_PILL = (0, 98)
TASK_BUTTONS = [
    (106, 160, "Control Panel", False),
    (266, 160, "My Computer", False),
    (426, 160, "Windows XP Tour", True),
]
TRAY_BOX = (707, SCREEN_WIDTH - 707)
STRIP = """import QtQuick
import org.kde.ksvg as KSvg
import "%(start)s" as Start
import "%(tasks)s" as Tasks
import "%(tray)s" as Tray
Rectangle {
    width: %(width)d; height: %(height)d
    color: "#ff00ff"
    Component.onCompleted: {
        KSvg.ImageSet.basePath = "%(themes)s"
        KSvg.ImageSet.imageSetName = "Chicago95Luna"
    }
    Column {
        Repeater {
            model: %(rows)s
            Rectangle { required property string modelData; width: %(width)d; height: 1; color: modelData }
        }
    }
    Start.StartButton { objectName: "start"; x: %(start_left)d; width: %(start_width)d; height: %(height)d; text: "start" }
%(tasks_items)s
    Tray.TrayBox { x: %(tray_left)d; width: %(tray_width)d; height: %(height)d }
}
"""
TASK_ITEM = '    Tasks.TaskButton { x: %d; width: %d; height: %d; text: "%s"; pressed: %s }'


def load_module(name):
    sys.path.insert(0, str(LUNA_LIB))
    spec = importlib.util.spec_from_file_location(name, LUNA_LIB / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def luna_taskbar(app, scratch, width=SCREEN_WIDTH, tray_width=TRAY_BOX[1]):
    """The Luna panel as Plasma draws it: the Start pill, task buttons and tray box on the panel's rows
    (icons, the labels' fonts and the clock are the programs' own). xprunning.png is 800 wide with a 93px tray
    box; xptaskbar-1x.png is 3000 wide with a 147px one."""
    scratch = scratch / f"luna-panel-{width}"
    scratch.mkdir(exist_ok=True)
    qml_root = next((root for root in QML_ROOTS if (root / "org/kde/ksvg").is_dir()), None)
    if qml_root is None:
        raise RuntimeError("KSvg's QML module is not installed")
    packages, themes = scratch / "plasmoids", scratch / "themes"
    for package in PACKAGES:
        shutil.copytree(REPO / "plasmoids" / package / "contents", packages / package / "contents")
        shutil.copytree(
            REPO / "luna/plasmoids" / package / "contents", packages / package / "contents", dirs_exist_ok=True
        )
        shutil.copy(REPO / "luna/plasmoids/family.js", packages / package / "contents/ui/luna/family.js")
    shutil.copytree(REPO / "luna/plasma-style/theme", themes / "Chicago95Luna")
    folder = {
        key: (packages / f"org.chicago95.{key}" / "contents/ui/luna").as_uri()
        for key in ("start", "tasks", "trayframe")
    }
    tasks = "\n".join(
        TASK_ITEM % (left + OFF_POINTER, width, PANEL_HEIGHT, text, str(pressed).lower())
        for left, width, text, pressed in TASK_BUTTONS
    )
    (scratch / "strip.qml").write_text(
        STRIP
        % {
            "start": folder["start"],
            "tasks": folder["tasks"],
            "tray": folder["trayframe"],
            "themes": themes,
            "width": width + OFF_POINTER,
            "height": PANEL_HEIGHT,
            "rows": "[" + ", ".join(f'"{row}"' for row in PALETTE["taskbar"]) + "]",
            "start_left": START_PILL[0] + OFF_POINTER,
            "start_width": START_PILL[1],
            "tasks_items": tasks,
            "tray_left": OFF_POINTER + width - tray_width,
            "tray_width": tray_width,
        }
    )
    view = QQuickView()
    view.engine().addImportPath(str(qml_root))
    view.setSource(QUrl.fromLocalFile(str(scratch / "strip.qml")))
    errors = [error.toString() for error in view.errors()]
    if errors:
        raise RuntimeError(errors)
    view.show()
    QTimer.singleShot(400, app.quit)
    app.exec()
    image = qimage_to_pil(view.grabWindow())
    view.close()
    return image.crop((OFF_POINTER, 0, OFF_POINTER + width, PANEL_HEIGHT))


def solid_icon(colour="#808080"):
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor(colour))
    return QIcon(pixmap)


def sample_apps():
    names = ("Firefox", "Thunderbird", *(f"Tool {index}" for index in range(8)))
    return [
        {"name": name, "icon": name, "categories": ["Utility"], "path": f"/apps/{index}.desktop"}
        for index, name in enumerate(names)
    ]


def luna_menu():
    """The two-column Start menu, drawn whole (380 wide), with a sample user and programs."""
    menu = load_module("chicago95lunamenu")
    return qimage_to_pil(menu.drawn_root_menu(sample_apps(), [], lambda _item: solid_icon(), user_name="Nathan"))


def luna_turn_off():
    return qimage_to_pil(load_module("chicago95lunadialogs").drawn_turn_off_dialog())


def luna_window(width, height, active, scratch, caption=""):
    """The Luna frame at the original's size, over white (the screenshots' windows sit on their own content)."""
    theme = build_luna_theme(scratch / f"luna-aurorae-{'active' if active else 'inactive'}")
    frame = LunaWindow(width, height, theme=theme, active=active, caption=caption).render_rgba()
    background = Image.new("RGBA", frame.size, (255, 255, 255, 255))
    background.alpha_composite(frame)
    return background.convert("RGB")


def luna_controls(app):
    """The gallery of controls LunaStyle draws, in the look's palette and font (tests/luna/luna_gallery.py)."""
    style = load_module("chicago95luna")
    gallery = luna_gallery()
    style_tree(gallery, style.LunaStyle())
    gallery.setPalette(style.luna_palette())
    gallery.setFont(style.luna_font())
    gallery.show()
    app.processEvents()
    image = qimage_to_pil(gallery.grab().toImage())
    gallery.close()
    return image
