import importlib.machinery
import importlib.util
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_SCALE_FACTOR"] = "1"
sys.path.insert(0, str(REPO / "lib"))


def load_script(name):
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), str(REPO / "bin" / name))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


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
