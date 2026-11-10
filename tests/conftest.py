import importlib.machinery
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_SCALE_FACTOR"] = "1"
# An empty settings folder, set before our modules load: tests see the defaults, never the colour
# scheme, look or icon set of whoever runs them (CI and every machine get the same results).
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="chicago95-tests-config-")
sys.path.insert(0, str(REPO / "lib"))


def load_script(name):
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), str(REPO / "bin" / name))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def ui_font_installed():
    import subprocess
    families = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True).stdout
    return "MS W98 UI" in families


# The UI font can't be redistributed (CI machines don't have it); tests that measure our lettering
# are only meaningful with it, so they skip without it instead of failing for the wrong reason.
needs_ui_font = pytest.mark.skipif(not ui_font_installed(), reason="MS W98 UI font is not installed")


def icon_set_installed(name):
    return any((Path(base) / name / "index.theme").exists()
               for base in (Path.home() / ".icons", Path.home() / ".local/share/icons", "/usr/share/icons"))


# Icon sets come from other projects (Chicago95, SE98, ClassicOS-2000) and are installed by Setup, not
# shipped here; tests that compare icons skip without them.
needs_chicago95_icons = pytest.mark.skipif(not icon_set_installed("Chicago95"), reason="Chicago95 icon set is not installed")


@pytest.fixture(scope="session")
def qt_app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="session")
def shutdown():
    return load_script("chicago95-shutdown")


@pytest.fixture(scope="session")
def startmenu():
    return load_script("chicago95-startmenu")


@pytest.fixture
def path_with(tmp_path, monkeypatch):
    def install(*binaries):
        for binary in binaries:
            executable = tmp_path / binary
            executable.write_text("#!/bin/sh\n")
            executable.chmod(0o755)
        monkeypatch.setenv("PATH", str(tmp_path))
    return install
