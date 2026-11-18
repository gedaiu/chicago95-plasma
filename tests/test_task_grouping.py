"""When the task list combines a program's windows into one button (grouping.js), as Windows 7's "Group similar
taskbar buttons" setting does: always, when the taskbar is full, or never."""

import pytest
from conftest import REPO
from js_library import call, load_js_library


@pytest.fixture(scope="module")
def grouping(qt_app):
    return load_js_library(REPO / "plasmoids/org.chicago95.tasks/contents/ui/grouping.js")


@pytest.mark.parametrize(
    ("setting", "style", "expected"),
    [
        ("auto", "aero", "always"),
        ("auto", "luna", "never"),
        ("auto", "classic", "never"),
        ("always", "classic", "always"),
        ("full", "aero", "full"),
        ("never", "aero", "never"),
        ("", "aero", "always"),
    ],
)
def test_setting_and_taskbar_style_give_the_grouping(grouping, setting, style, expected):
    assert call(grouping, "mode", setting, style) == expected


@pytest.mark.parametrize(
    ("mode", "fitting", "expected"),
    [
        ("always", 9, 0),  # group whatever the count
        ("full", 9, 9),  # group once more windows than the 9 buttons that fit are open
        ("full", 0, 1),  # no room at all: still one window before grouping
        ("never", 9, -1),
    ],
)
def test_grouping_threshold_is_the_window_count_above_which_windows_combine(grouping, mode, fitting, expected):
    assert call(grouping, "threshold", mode, fitting) == expected


@pytest.mark.parametrize(
    ("focused", "expected"),
    [
        ([False, False, False], 0),  # none focused: the first
        ([False, True, False], 2),  # the next after the focused one
        ([False, False, True], 0),  # round to the first again
        ([True], 0),
    ],
)
def test_clicking_a_combined_button_focuses_the_window_after_the_focused_one(grouping, focused, expected):
    assert call(grouping, "nextWindow", focused) == expected


@pytest.mark.parametrize("option", ["auto", "always", "full", "never"])
def test_setup_writes_the_grouping_option_into_the_task_list(tmp_path, option):
    from test_quick_launch import written_by_apply_taskbar

    written = written_by_apply_taskbar(tmp_path, SETUP_START_MENU_STYLE=1995, SETUP_TASK_GROUPING=option)

    assert f"widget.writeConfig('grouping', \"{option}\")" in written


def test_install_takes_the_grouping_option_from_its_flag(tmp_path):
    import subprocess

    subprocess.run(
        [str(REPO / "install.sh"), "--plain", "--yes", "--dry-run", "--task-grouping=never", "--components=taskbar"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        env={"PATH": "/usr/bin:/bin", "SETUP_OS_RELEASE": "/dev/null", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)},
        check=False,
    )
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()

    assert "grouping=never" in log
