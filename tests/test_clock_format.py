import xml.etree.ElementTree as ElementTree

import pytest

from conftest import REPO
from js_library import call, load_js_library

CLOCK_APPLET = REPO / "plasmoids/org.chicago95.clock/contents"


@pytest.fixture(scope="module")
def clock_format(qt_app):
    return load_js_library(CLOCK_APPLET / "ui/clockFormat.js")


@pytest.mark.parametrize("hour_format, locale_format, expected", [
    ("24", "h:mm AP", "HH:mm"),
    ("12", "HH:mm", "h:mm AP"),
    ("locale", "HH:mm", "HH:mm"),
    ("locale", "h:mm AP", "h:mm AP"),
    ("", "HH:mm", "HH:mm"),
])
def test_time_format_is_24_hour_12_hour_or_the_locales_own(clock_format, hour_format, locale_format, expected):
    assert call(clock_format, "timeFormat", hour_format, locale_format) == expected


def test_clock_applet_stores_the_hour_format_following_the_locale_by_default():
    kcfg = "{http://www.kde.org/standards/kcfg/1.0}"
    entry = next(entry for entry in ElementTree.parse(CLOCK_APPLET / "config/main.xml").iter(f"{kcfg}entry") if entry.get("name") == "hourFormat")

    assert (entry.get("type"), entry.findtext(f"{kcfg}default")) == ("String", "locale")


def test_clock_applet_formats_its_time_with_the_clock_format_library():
    main_qml = (CLOCK_APPLET / "ui/main.qml").read_text()

    assert "ClockFormat.timeFormat(Plasmoid.configuration.hourFormat, Qt.locale().timeFormat(Locale.ShortFormat))" in main_qml
