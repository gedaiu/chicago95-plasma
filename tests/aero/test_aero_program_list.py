import pytest
from chicago95aeromenu import AeroMenu
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtTest import QTest


@pytest.mark.parametrize("mode", ["programs", "search"])
def test_long_names_fit_the_viewport_and_keep_the_full_launch_target(qt_app, mode):
    names = [{"name": f"Long program {index} " + "Word " * 40, "icon": ""} for index in range(60)]
    launched = []
    menu = AeroMenu(names, launched.append, lambda _: QIcon(), {}, "Demo")
    try:
        menu.show()
        if mode == "search":
            menu.search.setText("Long program")
        else:
            menu.toggle_programs()
        QTest.qWait(30)
        view = menu.list
        assert view.verticalScrollBar().isVisible()
        assert view.textElideMode() == Qt.ElideRight
        assert not view.horizontalScrollBar().isVisible()
        assert view.visualItemRect(view.item(0)).width() == view.viewport().width()
        menu.open_first()
        assert launched == [names[0]]
    finally:
        menu.close()


def test_shutdown_and_options_are_separate_targets(qt_app):
    from PySide6.QtWidgets import QMenu, QPushButton

    launched = []
    commands = {"shut_down": ["shutdown-test"], "restart": ["restart-test"]}
    menu = AeroMenu([], launched.append, lambda _: QIcon(), commands, "Demo")
    try:
        menu.show()
        menu.findChild(QPushButton, "powerArrow").click()
        options = menu.findChild(QMenu)
        assert options.isVisible() and not launched
        options.actions()[0].trigger()
        assert launched == [commands["restart"]]
        menu.show()
        menu.findChild(QPushButton, "shutdown").click()
        assert launched[-1] == commands["shut_down"]
    finally:
        menu.close()
