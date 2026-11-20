"""Check live-blur dependency decisions without installing packages or loading a compositor plugin."""

import os
import shutil
import subprocess

import pytest
from conftest import REPO, run_bash_with_steps


@pytest.mark.parametrize("report,ready", [("(true,)", "yes"), ("(false,)", "no"), ("offline", "yes")])
def test_installed_effect_is_checked_with_the_running_compositor(tmp_path, report, ready):
    lines = run_bash_with_steps(
        tmp_path,
        f"""native_effect_available() {{ return 0; }}
gdbus() {{ [ '{report}' != offline ] || return 1; echo '{report}'; }}
SETUP_IN_PLASMA=1
if live_blur_available; then echo yes; else echo no; fi""",
    )
    assert lines == [ready]


def test_fedora_requests_exact_headers_and_rechecks_after_dnf(tmp_path):
    scripts = tmp_path / "bin"
    scripts.mkdir()
    helper = tmp_path / "aero/build-native.sh"
    helper.parent.mkdir()
    shutil.copy(REPO / "aero/build-native.sh", helper)
    for name, body in {
        "rpm": """case "$*" in
  *--qf*) printf '6.8.3-1.fc44.x86_64';;
  *kwin-devel-6.8.3-1.fc44.x86_64*) exit 1;;
  *) exit 0;;
esac""",
        "sudo": 'echo "$*" >> "$TEST_LOG"',
        "dnf": "exit 0",
    }.items():
        stub = scripts / name
        stub.write_text("#!/bin/sh\n" + body + "\n")
        stub.chmod(0o755)
    log = tmp_path / "calls"
    result = subprocess.run(
        ["bash", str(helper), "--install-wobbly"],
        env=os.environ | {"PATH": f"{scripts}:/usr/bin:/bin", "TEST_LOG": str(log)},
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "dependencies are incomplete" in result.stderr
    assert "dnf install" in log.read_text()
    assert "kwin-devel-6.8.3-1.fc44.x86_64" in log.read_text()
    assert "vulkan-loader-devel" in log.read_text()
