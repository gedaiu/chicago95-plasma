import subprocess

from conftest import REPO

SETUP_TIMEOUT_SECONDS = 30


def apply_with_saved_settings(home, saved_settings):
    settings_path = home / ".config/chicago95/setup.conf"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("".join(f"{key}={value}\n" for key, value in {"REPO": REPO, **saved_settings}.items()))
    try:
        result = subprocess.run(
            [
                str(REPO / "install.sh"),
                "--plain",
                "--yes",
                "--dry-run",
                f"--settings={settings_path}",
                "--components=taskbar",
            ],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            timeout=SETUP_TIMEOUT_SECONDS,
            env={"PATH": "/usr/bin:/bin", "HOME": str(home), "TMPDIR": str(home)},
            check=False,
        )
    except subprocess.TimeoutExpired:
        return f"still running after {SETUP_TIMEOUT_SECONDS} s", ""
    return result.returncode, "".join(log.read_text() for log in home.glob("chicago95-setup-*.log"))


def test_setup_finishes_and_keeps_the_remembered_own_start_logo(tmp_path):
    own_logo = tmp_path / "start-logo.png"
    own_logo.write_bytes(b"png")

    exit_status, log = apply_with_saved_settings(tmp_path, {"START_LOGO": own_logo})

    assert (exit_status, str(own_logo) in log) == (0, True)


def test_setup_finishes_when_the_remembered_own_start_logo_is_gone(tmp_path):
    exit_status, _log = apply_with_saved_settings(tmp_path, {"START_LOGO": tmp_path / "deleted-logo.png"})

    assert exit_status == 0
