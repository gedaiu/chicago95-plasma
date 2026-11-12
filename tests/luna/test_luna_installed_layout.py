import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO

COPY_LINE = re.compile(r"would: cp (?:-r )?(\S+) (\S+)$")
LUNA_MODULES = sorted(path.stem for path in (REPO / "luna/lib").glob("*.py"))
ENVIRONMENT = {"PATH": "/usr/bin:/bin", "QT_QPA_PLATFORM": "offscreen", "QT_SCALE_FACTOR": "1"}


def planned_copies(home):
    subprocess.run(
        [
            str(REPO / "install.sh"),
            "--plain",
            "--yes",
            "--dry-run",
            "--look=luna",
            "--components=look,taskbar,fonts,startmenu,controlpanel",
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=180,
        env={"PATH": "/usr/bin:/bin", "SETUP_OS_RELEASE": "/dev/null", "HOME": str(home), "TMPDIR": str(home)},
        check=False,
    )
    log = next(home.glob("chicago95-setup-*.log")).read_text()
    wanted = (f"{home}/.local/lib/chicago95", f"{home}/.local/bin")
    return [
        match.groups()
        for line in log.splitlines()
        if (match := COPY_LINE.search(line.strip())) and match.group(2).startswith(wanted)
    ]


@pytest.fixture(scope="module")
def installed_home(tmp_path_factory):
    home = tmp_path_factory.mktemp("installed-home")
    for source, destination in planned_copies(home):
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target, dirs_exist_ok=True) if Path(source).is_dir() else shutil.copy(source, target)
    (home / ".config").mkdir()
    (home / ".config/chicago95rc").write_text("[StartMenu]\nstyle=luna\n[Look]\nwidgetStyle=luna\n")
    return home


def run_installed(home, *arguments, script=None):
    command = [sys.executable, *arguments] if script is None else [sys.executable, "-c", script]
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=120,
        cwd=home,
        env={
            **ENVIRONMENT,
            "SETUP_OS_RELEASE": "/dev/null",
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_RUNTIME_DIR": str(home),
        },
        check=False,
    )


@pytest.mark.parametrize("module", LUNA_MODULES)
def test_luna_module_imports_from_the_installed_layout(installed_home, module):
    library = installed_home / ".local/lib/chicago95"
    result = run_installed(installed_home, script=f"import sys; sys.path.insert(0, {str(library)!r}); import {module}")
    assert (result.returncode, result.stderr.strip().splitlines()[-1:] or [""]) == (0, [""])


def test_installed_start_menu_screenshot_is_the_380_by_477_luna_menu(installed_home):
    from PIL import Image

    picture = installed_home / "menu.png"
    result = run_installed(
        installed_home, str(installed_home / ".local/bin/chicago95-startmenu"), "--screenshot", str(picture)
    )
    assert (result.returncode, Image.open(picture).size) == (0, (380, 477))


SHOW_PATH = """
import importlib.machinery, importlib.util, sys
loader = importlib.machinery.SourceFileLoader("startmenu", {script!r})
module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
loader.exec_module(module)
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
module.apply_retro_look(app)
controller = module.StartMenu(app)
controller.show()
app.processEvents()
visible = controller.visible()
controller.hide()
print("visible" if visible else "hidden")
"""


def test_installed_start_menu_show_path_opens_the_luna_menu_without_raising(installed_home):
    script = str(installed_home / ".local/bin/chicago95-startmenu")
    result = run_installed(installed_home, script=SHOW_PATH.format(script=script))
    assert (result.returncode, result.stdout.strip(), "Traceback" in result.stderr) == (0, "visible", False)
