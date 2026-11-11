"""Whether the taskbar shows its Quick Launch: Setup's option (yes, no, or auto: the look's own, which
the originals had from 1998 on), stored on the task list and decided in quickLaunch.js."""

import subprocess
import xml.etree.ElementTree as ElementTree

import pytest
from conftest import REPO
from js_library import call, load_js_library

TASKS_APPLET = REPO / "plasmoids/org.chicago95.tasks/contents"


@pytest.fixture(scope="module")
def quick_launch(qt_app):
    return load_js_library(TASKS_APPLET / "ui/quickLaunch.js")


@pytest.mark.parametrize(
    "setting, look, shown",
    [
        ("auto", "1995", False),
        ("auto", "1998", True),
        ("auto", "2000", True),
        ("yes", "1995", True),
        ("no", "2000", False),
        ("", "1998", True),
    ],
)
def test_quick_launch_shows_as_set_or_from_1998_on(quick_launch, setting, look, shown):
    assert call(quick_launch, "shown", setting, look) is shown


def test_tasks_applet_stores_the_quick_launch_setting_as_auto_by_default():
    kcfg = "{http://www.kde.org/standards/kcfg/1.0}"
    entry = next(
        entry
        for entry in ElementTree.parse(TASKS_APPLET / "config/main.xml").iter(f"{kcfg}entry")
        if entry.get("name") == "quickLaunch"
    )

    assert (entry.get("type"), entry.findtext(f"{kcfg}default")) == ("String", "auto")


def written_by_apply_taskbar(tmp_path, **settings):
    log = tmp_path / "setup.log"
    assignments = " ".join(f"{name}={value}" for name, value in settings.items())
    script = (
        f'REPO={REPO}; source {REPO}/setup/steps.sh; plasma_script() {{ printf "%s\\n" "$1"; }}; '
        f"SETUP_IN_PLASMA=1 SETUP_DRY_RUN=0 SETUP_LOG={log} {assignments} apply_taskbar"
    )
    subprocess.run(
        ["bash", "-c", script], timeout=30, env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}, check=False
    )
    return log.read_text()


@pytest.mark.parametrize("option", ["yes", "no", "auto"])
def test_setup_writes_the_quick_launch_option_into_the_task_list(tmp_path, option):
    written = written_by_apply_taskbar(tmp_path, SETUP_MENU_STYLE=1995, SETUP_QUICK_LAUNCH=option)

    assert f"widget.writeConfig('quickLaunch', \"{option}\")" in written


@pytest.mark.parametrize(
    "option, look, filled",
    [("yes", "1995", True), ("no", "2000", False), ("auto", "1995", False), ("auto", "1998", True)],
)
def test_an_empty_quick_launch_is_filled_with_the_defaults_only_where_it_shows(tmp_path, option, look, filled):
    written = written_by_apply_taskbar(tmp_path, SETUP_MENU_STYLE=look, SETUP_QUICK_LAUNCH=option)

    assert ('"applications:firefox.desktop"' in written) is filled


def test_install_takes_the_quick_launch_option_from_its_flag(tmp_path):
    subprocess.run(
        [str(REPO / "install.sh"), "--plain", "--yes", "--dry-run", "--quick-launch=no", "--components=taskbar"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)},
        check=False,
    )
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()

    assert "quicklaunch=no" in log
