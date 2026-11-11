import os
import signal
import subprocess

from conftest import REPO

SETUP_TIMEOUT_SECONDS = 15
BUNDLED_LOGOS = ["flag|Classic flag", "penguin|Penguin"]


def apply_with_saved_settings(home, saved_settings):
    settings_path = home / ".config/chicago95/setup.conf"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("".join(f"{key}={value}\n" for key, value in {"REPO": REPO, **saved_settings}.items()))
    return run_without_terminal(
        [
            str(REPO / "install.sh"),
            "--plain",
            "--yes",
            "--dry-run",
            f"--settings={settings_path}",
            "--components=taskbar",
        ],
        home,
    )


def run_without_terminal(command, home):
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        env={"PATH": "/usr/bin:/bin", "HOME": str(home), "TMPDIR": str(home)},
    )
    try:
        output, _errors = process.communicate(timeout=SETUP_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        return f"still running after {SETUP_TIMEOUT_SECONDS} s", ""
    return process.returncode, output


def chosen_start_logo_when_answering_yes_to_everything(home, remembered_logo):
    function = f"{REPO}/install.sh"
    script = (
        f"source {REPO}/setup/ui.sh; SETUP_YES=1; UI_PLAIN=1; "
        f"eval \"$(sed -n '/^choose_image() {{/,/^}}/p' {function})\"; "
        f'choose_image "Start button logo" "Which logo?" "$1" {" ".join(map(repr, BUNDLED_LOGOS))} 2>/dev/null'
    )
    return run_without_terminal(["bash", "-c", script, "setup", str(remembered_logo)], home)


def test_setup_finishes_when_the_remembered_own_start_logo_exists(tmp_path):
    own_logo = tmp_path / "start-logo.png"
    own_logo.write_bytes(b"png")

    exit_status, _output = apply_with_saved_settings(tmp_path, {"START_LOGO": own_logo})

    assert exit_status == 0


def test_setup_finishes_when_the_remembered_own_start_logo_is_gone(tmp_path):
    exit_status, _output = apply_with_saved_settings(tmp_path, {"START_LOGO": tmp_path / "deleted-logo.png"})

    assert exit_status == 0


def test_answering_yes_keeps_the_remembered_own_logo_file(tmp_path):
    own_logo = tmp_path / "start-logo.png"
    own_logo.write_bytes(b"png")

    assert chosen_start_logo_when_answering_yes_to_everything(tmp_path, own_logo) == (0, str(own_logo))


def test_answering_yes_falls_back_to_the_first_bundled_logo_when_the_remembered_file_is_gone(tmp_path):
    assert chosen_start_logo_when_answering_yes_to_everything(tmp_path, tmp_path / "deleted.png") == (0, "flag")
