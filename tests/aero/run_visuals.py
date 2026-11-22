"""Run the complete Windows 7 visual suite, treating missing reference coverage as a failure."""

import os
import sys
from pathlib import Path

import pytest


class RequireEveryComparison:
    def pytest_sessionfinish(self, session, exitstatus):
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        skipped = reporter.stats.get("skipped", [])
        if skipped and exitstatus == 0:
            reporter.write_line(f"Windows 7 visual validation is incomplete: {len(skipped)} skipped comparisons.")
            session.exitstatus = pytest.ExitCode.TESTS_FAILED


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    os.chdir(root)
    os.environ.setdefault("AERO_MSSTYLES_DIR", str(Path.home() / "src/aero-msstyles"))
    aero_tests = ["tests/aero"]
    if "--exact-originals" in sys.argv:
        # pytest deduplicates an explicit non-test file under an already collected directory.
        aero_tests = [str(path) for path in sorted(Path("tests/aero").glob("test_*.py"))]
        aero_tests.append("tests/aero/audit_desktop_pixels.py")
    sys.exit(
        pytest.main(
            [
                "-q",
                "-rs",
                *aero_tests,
                "tests/test_devmgr.py::test_aero_console_bands_match_win7_sp1",
                "tests/test_boot_visual_states.py",
                "tests/test_post_xp_boot.py",
                "tests/test_login_failure.py",
                "tests/test_classic_lockscreen.py",
                *sys.argv[1:],
            ],
            plugins=[RequireEveryComparison()],
        )
    )
