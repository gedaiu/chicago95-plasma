"""The window menu a task button's right click opens, as the originals' system menu: Restore, Move, Size, Minimize,
Maximize, then Close, each greyed out when it does not apply to the window as it is."""

import pytest
from conftest import REPO
from js_library import call, load_js_library
from test_quick_launch_drop import main_qml, qml_block

NORMAL = {
    "minimized": False,
    "maximized": False,
    "movable": True,
    "resizable": True,
    "minimizable": True,
    "maximizable": True,
    "closable": True,
}


@pytest.fixture(scope="module")
def window_menu(qt_app):
    return load_js_library(REPO / "plasmoids/org.chicago95.tasks/contents/ui/windowMenu.js")


@pytest.mark.parametrize(
    "changes, expected",
    [
        ({}, {"restore": False, "move": True, "size": True, "minimize": True, "maximize": True, "close": True}),
        (
            {"minimized": True},
            {"restore": True, "move": False, "size": False, "minimize": False, "maximize": True, "close": True},
        ),
        (
            {"maximized": True},
            {"restore": True, "move": False, "size": False, "minimize": True, "maximize": False, "close": True},
        ),
        (
            {"resizable": False, "maximizable": False},
            {"restore": False, "move": True, "size": False, "minimize": True, "maximize": False, "close": True},
        ),
        (
            {"movable": False, "minimizable": False, "closable": False},
            {"restore": False, "move": False, "size": True, "minimize": False, "maximize": True, "close": False},
        ),
    ],
    ids=["normal", "minimized", "maximized", "fixed size", "unmovable unminimizable unclosable"],
)
def test_menu_items_are_enabled_only_when_they_apply_to_the_window(window_menu, changes, expected):
    assert call(window_menu, "enabledItems", {**NORMAL, **changes}) == expected


def test_window_state_reads_the_task_models_roles_and_takes_missing_ones_as_false(window_menu):
    roles = {"IsMinimized": False, "IsMaximized": True, "IsMovable": True, "IsResizable": True, "IsClosable": True}

    assert call(window_menu, "windowState", roles) == {
        **NORMAL,
        "maximized": True,
        "minimizable": False,
        "maximizable": False,
    }


def test_a_window_buttons_right_click_gives_the_menu_that_windows_state():
    assert "windowMenu.window = WindowMenu.windowState(entry.model);" in qml_block(main_qml(), "id: windowButton")


def test_the_window_menu_lists_the_system_menu_in_the_originals_order():
    menu = qml_block(main_qml(), "PlasmaExtras.Menu {\n        id: windowMenu")
    items = ["Restore", "Move", "Size", "Minimize", "Maximize", "Add to Quick Launch", "Close"]

    positions = [menu.index(f'i18n("{item}")') for item in items]

    assert (positions == sorted(positions), "requestMove(" in menu, "requestResize(" in menu) == (True, True, True)


def test_right_clicks_open_the_window_and_quick_launch_menus_at_the_pointer():
    text = main_qml()

    assert (
        "windowMenu.open(clickX, clickY);" in qml_block(text, "id: windowButton"),
        "launcherMenu.open(clickX, clickY);" in qml_block(text, "id: launcherCell"),
        "windowMenu.openRelative()" in text or "launcherMenu.openRelative()" in text,
    ) == (True, True, False)
