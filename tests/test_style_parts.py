"""Which file a taskbar part loads for each taskbar style (styleParts.js)."""

import pytest
from conftest import REPO
from js_library import call, load_js_library


@pytest.fixture(scope="module")
def parts(qt_app):
    return load_js_library(REPO / "plasmoids/org.chicago95.tasks/contents/ui/styleParts.js")


@pytest.mark.parametrize(
    ("style", "part", "expected"),
    [
        ("classic", "TaskButton.qml", "TaskButton.qml"),
        ("luna", "TaskButton.qml", "luna/TaskButton.qml"),
        ("luna", "Chevron.qml", "luna/Chevron.qml"),
        ("aero", "TaskButton.qml", "aero/TaskButton.qml"),
        ("aero", "QuickLaunchButton.qml", "aero/QuickLaunchButton.qml"),
        ("aero", "Chevron.qml", "Chevron.qml"),
    ],
)
def test_part_loads_the_styles_own_file_or_the_classic_one(parts, style, part, expected):
    assert call(parts, "path", style, part) == expected
