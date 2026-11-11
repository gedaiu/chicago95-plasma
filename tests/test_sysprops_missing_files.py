import platform
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def sysprops():
    from conftest import load_script

    return load_script("chicago95-sysprops")


def test_read_os_name_returns_system_name_when_os_release_is_missing(sysprops, tmp_path, monkeypatch):
    missing_file = tmp_path / "os-release"
    real_path = Path

    def redirected_path(path):
        return real_path(missing_file if str(path) == "/etc/os-release" else path)

    redirected_path.home = real_path.home
    monkeypatch.setattr(sysprops, "Path", redirected_path)

    assert sysprops.read_os_name() == platform.system()
