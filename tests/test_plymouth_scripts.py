"""Every boot screen's script parses with Plymouth's own parser: Plymouth drops a theme it cannot parse and boots
on a dark screen. Its script language has no `? :`, for one."""

import ctypes
from pathlib import Path

import pytest
from conftest import REPO

PLUGIN = Path("/usr/lib64/plymouth/script.so")
SCRIPTS = sorted([*REPO.glob("plymouth/*/*.script"), *REPO.glob("luna/plymouth/*/*.script")])


@pytest.fixture(scope="module")
def parse_file():
    if not PLUGIN.exists():
        pytest.skip("Plymouth's script plugin is not installed")
    for library in ("libply.so.5", "libply-splash-core.so.5", "libply-splash-graphics.so.5"):
        ctypes.CDLL(library, mode=ctypes.RTLD_GLOBAL)
    function = ctypes.CDLL(str(PLUGIN)).script_parse_file
    function.restype, function.argtypes = ctypes.c_void_p, [ctypes.c_char_p]
    return function


@pytest.mark.parametrize("script", SCRIPTS, ids=[script.parent.name for script in SCRIPTS])
def test_boot_screen_script_parses_with_plymouths_parser(parse_file, script):
    assert parse_file(str(script).encode()) is not None
