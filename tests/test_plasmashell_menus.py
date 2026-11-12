"""plasmashell's QMenus (window, desktop and Quick Launch chevron menus) under data/plasmashell-menus.qss.

The stylesheet paints the grey panel and the navy selection; the Windows style keeps laying out the items, so
an entry's icon sits in its gutter with the label clear of it, and a plain entry's label starts in the check gutter.
"""

import itertools

import pytest
from conftest import REPO

STYLESHEET = (REPO / "data/plasmashell-menus.qss").read_text()
PANEL, SELECTED = "#c0c0c0", "#000080"


@pytest.fixture
def menu(qt_app):
    from PySide6.QtWidgets import QMenu

    def build(icon):
        from PySide6.QtGui import QAction, QColor, QIcon, QPixmap

        solid = QPixmap(16, 16)
        solid.fill(QColor("black"))
        menu = QMenu()
        menu.setStyleSheet(STYLESHEET)
        for label in ("Firefox", "Dolphin"):
            menu.addAction(QAction(QIcon(solid) if icon else QIcon(), label, menu))
        menu.setActiveAction(menu.actions()[1])
        menu.adjustSize()
        return menu

    return build


def ink_columns(menu, entry):
    """Item-relative columns on an entry's centre row that differ from the menu panel."""
    image = menu.grab().toImage()
    item = menu.actionGeometry(menu.actions()[entry])
    row = item.center().y()
    return [x - item.x() for x in range(item.x(), item.right()) if image.pixelColor(x, row).name() != PANEL]


def label_start(columns):
    """The first ink column after the first gap: past the icon when there is one."""
    return next(column for previous, column in itertools.pairwise(columns) if column - previous > 2)


def test_an_icon_entry_starts_its_icon_at_2px_and_its_label_at_25px(menu):
    columns = ink_columns(menu(icon=True), 0)
    assert (columns[0], label_start(columns)) == (2, 25)


def test_a_plain_entry_label_starts_in_the_17px_check_gutter(menu):
    assert ink_columns(menu(icon=False), 0)[0] == 17


def test_the_panel_stays_c0c0c0_and_the_selected_entry_navy(menu):
    plain = menu(icon=False)
    image = plain.grab().toImage()
    first, selected = (plain.actionGeometry(action) for action in plain.actions())
    assert (
        image.pixelColor(first.right() - 2, first.center().y()).name(),
        image.pixelColor(selected.right() - 2, selected.center().y()).name(),
    ) == (PANEL, SELECTED)
