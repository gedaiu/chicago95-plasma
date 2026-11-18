"""The superbar's QML parts on the Chicago95Aero Plasma style, against Windows 7's taskbar."""

import shutil
from pathlib import Path

import pytest
from conftest import REPO
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtQuick import QQuickItem, QQuickView
from reference import qimage_to_pil, screenshot

QML_ROOTS = [Path("/usr/lib64/qt6/qml"), Path("/usr/lib/qt6/qml"), Path("/usr/lib/x86_64-linux-gnu/qt6/qml")]
BAR_TOP = 728  # the references' taskbar: rows 728..767 of a 1024x768 screen
PACKAGES = ("org.chicago95.tasks", "org.chicago95.start", "org.chicago95.clock")
LEFT = 40  # the strip leaves room on the left so the part never starts under the pointer
STRIP = """import QtQuick
import org.kde.ksvg as KSvg
import "%(folder)s"
Item {
    width: %(width)d; height: 40
    Component.onCompleted: {
        KSvg.ImageSet.basePath = "%(themes)s"
        KSvg.ImageSet.imageSetName = "Chicago95Aero"
    }
    Image { source: "%(bar)s"; x: 0; y: 0; width: parent.width; height: 40 }
    %(component)s { objectName: "item"; x: %(x)d; width: %(item_width)d; height: 40 }
}
"""


@pytest.fixture(scope="module")
def qml_root():
    found = next((root for root in QML_ROOTS if (root / "org/kde/ksvg").is_dir()), None)
    return found or pytest.skip("KSvg's QML module is not installed")


@pytest.fixture(scope="module")
def installed(tmp_path_factory):
    """The tasks package with the Aero parts laid over it, and the Chicago95Aero style, as Setup installs them."""
    root = tmp_path_factory.mktemp("plasmoids")
    for package in PACKAGES:
        shutil.copytree(REPO / "plasmoids" / package / "contents", root / package / "contents")
        shutil.copytree(REPO / "aero/plasmoids" / package / "contents", root / package / "contents", dirs_exist_ok=True)
    themes = tmp_path_factory.mktemp("themes")
    shutil.copytree(REPO / "aero/plasma-style/theme", themes / "Chicago95Aero")
    return root, themes


@pytest.fixture(scope="module")
def bar(tmp_path_factory):
    """The references' empty taskbar, one column stretched: what lies behind a button."""
    path = tmp_path_factory.mktemp("bar") / "bar.png"
    screenshot("win7dragedge").crop((600, BAR_TOP, 601, BAR_TOP + 40)).save(path)
    return path


def render_part(qt_app, qml_root, installed, bar, tmp_path, component, width, properties, package=PACKAGES[0]):
    packages, themes = installed
    folder = packages / package / "contents/ui/aero"
    (tmp_path / "strip.qml").write_text(
        STRIP
        % {
            "folder": folder.as_uri(),
            "themes": themes,
            "bar": bar.as_uri(),
            "width": LEFT + width,
            "component": component,
            "x": LEFT,
            "item_width": width,
        }
    )
    view = QQuickView()
    view.engine().addImportPath(str(qml_root))
    view.setSource(QUrl.fromLocalFile(str(tmp_path / "strip.qml")))
    assert [error.toString() for error in view.errors()] == []
    item = view.rootObject().findChild(QQuickItem, "item")
    for key, value in properties.items():
        item.setProperty(key, value)
    view.show()
    QTimer.singleShot(300, qt_app.quit)
    qt_app.exec()
    image = qimage_to_pil(view.grabWindow())
    view.close()
    return image.crop((LEFT, 0, LEFT + width, 40))


def glass_difference(ours, theirs):
    """Mean difference outside the 32px icon in the middle, where the program's own picture differs."""
    pixels = [(x, y) for x in range(ours.width) for y in range(40) if not (14 <= x < 46 and 4 <= y < 36)]
    differences = [
        abs(a - b) for x, y in pixels for a, b in zip(ours.getpixel((x, y)), theirs.getpixel((x, y)), strict=True)
    ]
    return sum(differences) / len(differences)


def test_running_task_button_is_windows_7s_outside_the_icon(qt_app, qml_root, installed, bar, tmp_path):
    """win7screenres.png's Screen Resolution button: its window is running but the desktop menu has the focus. The
    sprite itself, laid on the stretched bar column, is 14 levels from it (the bar's streaks differ along it); the
    vector face's gloss sweep adds about 5."""
    ours = render_part(qt_app, qml_root, installed, bar, tmp_path, "TaskButton", 60, {"pressed": False})
    theirs = screenshot("win7screenres").crop((247, BAR_TOP, 307, BAR_TOP + 40))

    assert glass_difference(ours, theirs) < 20


def test_start_button_draws_the_orb_where_windows_7_has_it(qt_app, qml_root, installed, bar, tmp_path):
    ours = render_part(qt_app, qml_root, installed, bar, tmp_path, "StartButton", 58, {}, "org.chicago95.start")
    theirs = screenshot("win7dragedge").crop((0, BAR_TOP, 58, BAR_TOP + 40))
    ring = [(x, y) for x in range(58) for y in range(40) if 121 <= (x + 0.5 - 27.5) ** 2 + (y + 0.5 - 20) ** 2 <= 361]
    differences = [
        abs(a - b) for x, y in ring for a, b in zip(ours.getpixel((x, y)), theirs.getpixel((x, y)), strict=True)
    ]

    assert sum(differences) / len(differences) < 20


def light_pixels(image, top, bottom):
    return sum(1 for x in range(image.width) for y in range(top, bottom) if min(image.getpixel((x, y))) > 200)


def test_clock_shows_time_over_date_and_ends_in_windows_7s_show_desktop_strip(
    qt_app, qml_root, installed, bar, tmp_path
):
    """win7screenres.png: the time on rows 733..746, the date on 750..763, then the strip at x 1009..1023."""
    from PySide6.QtCore import QDate, QDateTime, QTime

    ours = render_part(
        qt_app,
        qml_root,
        installed,
        bar,
        tmp_path,
        "Clock",
        80,
        {"now": QDateTime(QDate(2009, 10, 26), QTime(9, 16))},
        "org.chicago95.clock",
    )
    theirs = screenshot("win7screenres").crop((944, BAR_TOP, 1024, BAR_TOP + 40))
    strip = [(x, y) for x in range(65, 80) for y in range(40)]
    differences = [
        abs(a - b) for x, y in strip for a, b in zip(ours.getpixel((x, y)), theirs.getpixel((x, y)), strict=True)
    ]

    assert (
        light_pixels(ours, 4, 19) > 20,
        light_pixels(ours, 21, 36) > 20,
        sum(differences) / len(differences) < 12,
    ) == (True, True, True)


def test_clock_date_format_spells_the_year_in_full_as_windows_7_does(qt_app):
    from js_library import call, load_js_library

    clock_format = load_js_library(REPO / "plasmoids/org.chicago95.clock/contents/ui/clockFormat.js")

    assert [call(clock_format, "fullYearDateFormat", short) for short in ("M/d/yy", "dd.MM.yyyy", "yy-MM-dd")] == [
        "M/d/yyyy",
        "dd.MM.yyyy",
        "yyyy-MM-dd",
    ]
