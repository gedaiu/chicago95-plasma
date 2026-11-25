"""Drive the launcher and capture selected bands and popup edges at the reference DPI."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conftest import REPO, load_script  # noqa: E402
from PIL import Image  # noqa: E402
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QIcon, QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QFrame  # noqa: E402
from reference import qimage_to_pil, rgb565  # noqa: E402
from render_report import MENU_SETTINGS  # noqa: E402


def render(manifest, output):
    import chicago95ui

    settings = json.loads(manifest.read_text())
    look = settings["look"]
    capture = settings["start_menu_interaction"]
    scale = capture["scale"]
    os.environ["QT_SCALE_FACTOR"] = str(scale)
    os.environ["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=/nonexistent"
    app = QApplication([])
    startmenu = load_script("chicago95-startmenu")
    rc, colours = MENU_SETTINGS.get(look, (f"[StartMenu]\nstyle={look}\n", ""))
    startmenu.SETTINGS_FILE.write_text(rc + "\n[Animations]\nANIM_MENUS=none\n")
    Path(chicago95ui.KDEGLOBALS).write_text(colours)
    startmenu.apply_retro_look(app)
    output.mkdir(parents=True, exist_ok=True)

    def image(widget):
        frame = widget.grab()
        assert frame.devicePixelRatio() == scale
        actual = qimage_to_pil(frame.toImage())
        return rgb565(actual) if capture.get("rgb565") else actual

    def selected(widget, rect, x, name, *, pixel_height=None):
        left = round(x * scale)
        top = round(rect.top() * scale)
        bottom = round((rect.bottom() + 1) * scale)
        if pixel_height is not None:
            # QPainter snaps half pixels up. The native Classic crop is
            # 32 pixels of highlight with two pixels of context on each side.
            top = int(rect.top() * scale + 0.5)
            bottom = top + pixel_height
        image(widget).crop((left, top - 2, left + 3, bottom + 2)).save(output / f"{name}-selection.png")

    def popup(widget, name):
        image(widget).crop((0, 0, 5, 24)).save(output / f"{name}-popup.png")

    if look == "aero":
        from chicago95aeromenu import AeroMenu

        menu = AeroMenu([], lambda _: None, QIcon, {}, "Reference", REPO / "aero/icons/file-manager.svg")
        menu.show()
        QTest.qWait(25)
        QTest.mouseClick(menu.toggle, Qt.LeftButton)
        menu.toggle.setFocus()
        app.processEvents()
        assert menu.all_programs
        selected(menu.toggle.parentWidget(), menu.toggle.geometry(), menu.toggle.geometry().right() - 34, "programs")
        pane = menu.findChild(QFrame, "programs")
        origin = pane.mapTo(menu, QPoint()) - QPoint(1, 0)
        expanded = output / "aero-expanded.png"
        assert menu.grab().save(str(expanded))
        with Image.open(expanded) as capture:
            frame = capture.convert("RGBA")
        backdrop = Image.new("RGBA", frame.size, "#4395d1")
        backdrop.alpha_composite(frame)
        x, y = origin.x(), origin.y()
        backdrop.crop((x, y, x + 5, y + 24)).save(output / "programs-popup.png")
    elif look == "luna":
        from chicago95lunamenu import LunaMenu, highlight_rect

        menu = LunaMenu(
            [{"name": "Calculator", "categories": [], "path": "/test/calculator.desktop"}],
            [],
            lambda _: None,
            lambda _: QIcon(),
            startmenu.RetroMenu,
            None,
        )
        menu.move(5, 80)
        menu.show()
        for title, name, x in (("All Programs", "programs", 20), ("My Recent Documents", "recent", 370)):
            row = next(row for row in menu.rows if row.text == title)
            point = QPointF(row.rect.center())
            event = QMouseEvent(QEvent.MouseMove, point, point, Qt.NoButton, Qt.NoButton, Qt.NoModifier)
            QApplication.sendEvent(menu, event)
            assert menu.hovered is row
            selected(menu, highlight_rect(row), x, name)
            QTest.mouseClick(menu, Qt.LeftButton, pos=row.rect.center())
            assert menu.submenu is not None and menu.submenu.isVisible()
            popup(menu.submenu, name)
            menu.submenu.close()
    else:

        def fill_programs(menu):
            menu.addAction("Accessories")
            menu.addAction("Startup")

        startmenu.fill_programs_menu = fill_programs
        menu = startmenu.build_root_menu()
        programs = next(action for action in menu.actions() if action.text().replace("&", "") == "Programs")
        # Match the number of preceding actions when comparing a strip that
        # includes the two pixels above the selected row.
        if look == "2000":
            titles = ("Set Program Access and Defaults", "Windows Update")
            for title in titles:
                menu.insertAction(programs, startmenu.QAction(title, menu))
            menu.insertSeparator(programs)
        elif look == "2001":
            first = menu.actions()[0]
            menu.insertAction(first, startmenu.QAction("Set Program Access and Defaults", menu))
        menu.move(5, 50)
        menu.show()
        menu.setActiveAction(programs)
        row = menu.actionGeometry(programs)
        selected(menu, row, row.right() - 30, "programs", pixel_height=32)
        QTest.keyClick(menu, Qt.Key_Right)
        submenu = programs.menu()
        assert submenu.isVisible()
        if submenu.activeAction() is None:
            QTest.keyClick(submenu, Qt.Key_Down)
        popup(submenu, "programs")
        submenu.close()
    menu.close()


if __name__ == "__main__":
    render(Path(sys.argv[1]), Path(sys.argv[2]))
