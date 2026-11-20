"""Render deterministic Aero UI states in a separate Qt process at the requested device scale."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conftest import REPO, load_script
from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtGui import QFont, QIcon
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu, QTabWidget
from screencast_stubs import write_stubs


def render(out, scale):
    import chicago95ui
    from chicago95aeromenu import AeroMenu

    out.mkdir(parents=True, exist_ok=True)
    os.environ["QT_SCALE_FACTOR"] = str(scale)
    os.environ["QT_QUICK_BACKEND"] = "software"
    # No screenshot should acquire a name on the real Start menu's bus.
    os.environ["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=/nonexistent"
    config = Path(os.environ["XDG_CONFIG_HOME"])
    (config / "chicago95rc").write_text("[Look]\nwidgetStyle=aero\n[StartMenu]\nstyle=aero\n")
    # Use a fixed family even on machines with Microsoft's optional fonts installed.
    fonts = Path(subprocess.check_output(["fc-match", "-f", "%{file}", "DejaVu Sans"], text=True)).parent
    (config / "fonts.conf").write_text(
        f"<fontconfig><dir>{fonts}</dir><cachedir>{config}/font-cache</cachedir></fontconfig>"
    )
    os.environ["FONTCONFIG_FILE"] = str(config / "fonts.conf")
    app = QApplication([])
    app.setStyle("Fusion")
    app.setPalette(app.style().standardPalette())
    font = QFont("DejaVu Sans")
    font.setPixelSize(12)
    app.setFont(font)
    app.setCursorFlashTime(0)
    theme = config / "AeroTest"
    shutil.copytree(REPO / "aero/icons", theme / "actions")
    shutil.copyfile(theme / "actions/file-manager.svg", theme / "actions/computer.svg")
    (theme / "index.theme").write_text(
        "[Icon Theme]\nName=AeroTest\nDirectories=actions\n[actions]\nSize=32\nMinSize=1\nMaxSize=512\nType=Scalable\n"
    )
    QIcon.setThemeSearchPaths([str(config)])
    QIcon.setFallbackSearchPaths([])
    QIcon.setThemeName("AeroTest")
    assert chicago95ui.widget_style() == "aero"

    def capture(widget, name):
        widget.show()
        app.processEvents()
        if isinstance(widget, AeroMenu):
            # Capture the settled menu after its visible theme icons have arrived.
            while widget.model.loader.isActive():
                app.processEvents()
        picture = widget.grab()
        assert picture.devicePixelRatio() == scale
        assert picture.save(str(out / f"{name}.png"))

    shutdown = load_script("chicago95-shutdown")
    for name, choice in (
        ("shutdown", shutdown.SHUT_DOWN),
        ("restart", shutdown.RESTART),
        ("logoff", shutdown.LOG_OFF),
        ("chooser", None),
    ):
        dialog = shutdown.screenshot_dialog(choice == shutdown.LOG_OFF, choice)
        capture(dialog, name)
        dialog.close()

    daemon = load_script("chicago95-notifyd")
    balloon = daemon.NotificationPopup(
        daemon.Notification(1, "Files", "file-manager", "Copy complete", "All files were copied.", [], {}, 0)
    )
    capture(balloon, "balloon")
    balloon.close()

    props = load_script("chicago95-sysprops")
    facts = props.SystemFacts(
        "Windows 7",
        "6.8",
        "Plasma",
        "Demo",
        "Desktop",
        "1234",
        "Processor",
        "4",
        "8 GB",
        "1024x768",
        "80%",
        "ext4",
        "4 GB",
    )
    dialog = props.build_window(facts)
    tabs = dialog.findChild(QTabWidget)
    for index, name in enumerate(("general", "hardware", "advanced")):
        tabs.setCurrentIndex(index)
        capture(dialog, f"system-{name}")
    dialog.close()

    apps = [{"name": f"Application {i:02d} with a long program name", "icon": "file-manager"} for i in range(32)]
    for entry in apps[24:]:
        entry["categories"] = ["Accessories"]
    keys = (
        "home my_documents my_pictures my_music games my_computer control_panel printers defaults help "
        "shut_down switch_user log_off lock restart sleep hibernate"
    )
    menu = AeroMenu(
        apps,
        lambda _: None,
        QIcon.fromTheme,
        dict.fromkeys(keys.split(), ["dummy"]),
        "Demo",
        REPO / "aero/icons/file-manager.svg",
        folder_for=lambda app: app["categories"][0],
    )
    capture(menu, "start")
    menu.toggle_programs()
    capture(menu, "programs")
    menu.search.setText("Application 12")
    capture(menu, "search")
    options = menu.findChild(QMenu)
    options.popup(menu.pos())
    capture(options, "power-options")
    options.close()
    menu.close()

    view = QQuickView()
    imports = write_stubs(config / "preview-imports")
    # The list fixture has no app-provided icons; keep the slot empty on non-Plasma CI too.
    kirigami = imports / "org/kde/kirigami"
    kirigami.mkdir(parents=True)
    (kirigami / "qmldir").write_text("module org.kde.kirigami\nIcon 1.0 Icon.qml\n")
    (kirigami / "Icon.qml").write_text("import QtQuick\nImage {}\n")
    view.engine().addImportPath(str(imports))
    view.setColor(Qt.transparent)
    view.setSource(
        QUrl.fromLocalFile(str(REPO / "aero/plasmoids/org.chicago95.tasks/contents/ui/aero/TaskToolTip.qml"))
    )
    assert not view.errors()
    tip = view.rootObject()
    tip.setProperty("title", "Document")
    tip.setProperty("ids", ["00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000002"])
    for size, name in ((0, "preview-list"), (144, "preview-cards")):
        tip.setProperty("previewSize", size)
        view.resize(round(tip.implicitWidth()), round(tip.implicitHeight()))
        view.show()
        QTest.mouseMove(view, QPoint(45, 15))
        QTest.qWait(80)
        assert view.grabWindow().save(str(out / f"{name}.png"))
    view.close()


if __name__ == "__main__":
    render(Path(sys.argv[1]), float(sys.argv[2]))
