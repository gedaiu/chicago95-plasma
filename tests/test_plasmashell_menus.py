"""plasmashell's QMenus (window, desktop and Quick Launch chevron menus) under data/plasmashell-menus.qss.

The stylesheet paints the grey panel and the navy selection; the Windows style keeps laying out the items, so
an entry's icon sits in its gutter with the label clear of it, and a plain entry's label starts in the check gutter.
"""

import itertools

import pytest
from conftest import REPO, run_bash_with_steps

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


@pytest.mark.parametrize(
    "look,scale,height",
    (("1995", 1, 17), ("1995", 1.25, 16), ("1998", 1.25, 16), ("2000", 1.25, 17), ("2001", 1.25, 17)),
)
def test_compact_classic_menu_keeps_icons_and_checks(qt_app, tmp_path, look, scale, height):
    from PySide6.QtGui import QColor, QIcon, QPixmap
    from PySide6.QtWidgets import QMenu

    sheet = "\n".join(run_bash_with_steps(
        tmp_path, f'SETUP_SCALE={scale} SETUP_LOOK={look} render_menus_qss "$REPO/data/plasmashell-menus.qss"'
    ))
    menu = QMenu()
    menu.setStyleSheet(sheet)
    icon = QPixmap(16, 16)
    icon.fill(QColor("#FF00FF"))
    with_icon = menu.addAction(QIcon(icon), "Open")
    checked = menu.addAction("Checked")
    checked.setCheckable(True)
    checked.setChecked(True)
    submenu = menu.addMenu("Nested")
    menu.addSeparator()
    disabled = menu.addAction("Unavailable")
    disabled.setEnabled(False)
    menu.adjustSize()
    image = menu.grab().toImage()
    rows = [menu.actionGeometry(action) for action in (with_icon, checked, submenu.menuAction(), disabled)]
    assert [row.height() for row in rows] == [height] * 4
    first, second, nested, last = rows
    assert image.pixelColor(first.x() + 2, first.center().y()).name() == "#ff00ff"
    assert any(
        image.pixelColor(x, y).name() == "#000000"
        for x in range(second.x(), second.x() + 17)
        for y in range(second.y(), second.bottom() + 1)
    )
    assert any(
        image.pixelColor(x, y).name() == "#000000"
        for x in range(nested.right() - 13, nested.right())
        for y in range(nested.y(), nested.bottom() + 1)
    )
    assert any(
        image.pixelColor(x, y).name() == "#808080"
        for x in range(last.x() + 20, last.right() - 5)
        for y in range(last.y(), last.bottom() + 1)
    )
