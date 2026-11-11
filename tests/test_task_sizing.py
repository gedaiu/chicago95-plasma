import xml.etree.ElementTree as ElementTree

import pytest
from conftest import REPO
from js_library import call, load_js_library

TASKS_APPLET = REPO / "plasmoids/org.chicago95.tasks/contents"


@pytest.fixture(scope="module")
def sizing(qt_app):
    return load_js_library(TASKS_APPLET / "ui/sizing.js")


@pytest.mark.parametrize(
    "configured, look, expected",
    [(0, "1995", 95), (0, "1998", 160), (0, "2000", 160), (220, "1995", 220), (60, "2000", 60)],
)
def test_max_button_width_is_the_configured_width_or_the_looks_own(sizing, configured, look, expected):
    assert call(sizing, "maxButtonWidth", configured, look) == expected


def test_tasks_applet_stores_the_max_button_width_with_zero_meaning_the_looks_own():
    kcfg = "{http://www.kde.org/standards/kcfg/1.0}"
    entry = next(
        entry
        for entry in ElementTree.parse(TASKS_APPLET / "config/main.xml").iter(f"{kcfg}entry")
        if entry.get("name") == "maxButtonWidth"
    )

    assert (entry.get("type"), entry.findtext(f"{kcfg}default")) == ("Int", "0")


def test_tasks_applet_sizes_its_buttons_with_the_sizing_library():
    main_qml = (TASKS_APPLET / "ui/main.qml").read_text()

    assert "Sizing.maxButtonWidth(Plasmoid.configuration.maxButtonWidth, Plasmoid.configuration.look)" in main_qml
