import subprocess
import time
from pathlib import Path

from conftest import REPO


def test_dry_run_of_sddm_component_writes_the_zz_override_without_asking_for_a_password(tmp_path):
    result = subprocess.run([str(REPO / "install.sh"), "--plain", "--yes", "--dry-run", "--components=sddm"],
                            capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60,
                            env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)})
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()

    assert (result.returncode, "Administrator password" in result.stdout,
            "would: sudo tee /etc/sddm.conf.d/zz-chicago95.conf" in log) == (0, False, True)


def run_setup(home, *arguments):
    stubs = home / "stubs"
    stubs.mkdir(exist_ok=True)
    for command in ("systemctl", "gdbus", "qdbus", "qdbus6", "kwriteconfig6", "plasma-apply-colorscheme",
                    "plasma-apply-desktoptheme", "plasma-apply-cursortheme", "xrdb"):
        (stubs / command).write_text("#!/bin/sh\nexit 0\n")
        (stubs / command).chmod(0o755)
    (stubs / "plasmashell").write_text("#!/bin/sh\necho plasmashell 6.8.2\n")
    (stubs / "plasmashell").chmod(0o755)
    return subprocess.run([str(REPO / "install.sh"), "--plain", "--yes", *arguments],
                          capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120,
                          env={"PATH": f"{stubs}:/usr/bin:/bin", "HOME": str(home), "TMPDIR": str(home)})


def test_reinstall_keeps_the_original_file_as_the_only_backup_and_lists_it_once(tmp_path):
    launcher = tmp_path / ".local/share/applications/qmmp.desktop"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("original launcher\n")

    first, second = run_setup(tmp_path, "--components=winamp"), (time.sleep(1.1), run_setup(tmp_path, "--components=winamp"))[1]
    backups = sorted(path.read_text() for path in (tmp_path / ".local/share/chicago95").glob("backup-*/.local/share/applications/qmmp.desktop"))
    manifest = (tmp_path / ".local/share/chicago95/installed-files.txt").read_text().splitlines()

    assert (first.returncode, second.returncode, backups, manifest.count(str(launcher))) == (0, 0, ["original launcher\n"], 1)


def test_dry_run_of_the_2000_look_downloads_the_waving_flag_for_the_loading_screen(tmp_path):
    subprocess.run([str(REPO / "install.sh"), "--plain", "--yes", "--dry-run", "--look=2000", "--components=splash"],
                   capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60,
                   env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)})
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()

    assert f"would: python3 {REPO}/setup/fetch-waving-flag.py {tmp_path}/.local/share/chicago95/waving-flag.png" in log


def test_login_theme_settings_carry_title_message_and_picture_without_banner_texts(tmp_path):
    script = (f'REPO={REPO}; source {REPO}/setup/steps.sh; SETUP_LOGIN_TITLE="Welcome to %h"; '
              'SETUP_LOGIN_MESSAGE="Hi & welcome"; SETUP_LOGIN_ICON=padlock; sddm_theme_conf')
    settings = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30,
                              env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}).stdout.splitlines()

    assert ({"loginTitle=Welcome to %h", "loginMessage=Hi & welcome", "loginIcon=login-icon.svg"} <= set(settings),
            [line for line in settings if line.startswith("brand")]) == (True, [])


def test_dry_run_of_the_2000_login_draws_the_banner_with_the_shut_down_code(tmp_path):
    subprocess.run([str(REPO / "install.sh"), "--plain", "--yes", "--dry-run", "--login-style=2000", "--components=sddm"],
                   capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60,
                   env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)})
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()

    assert (f"would: env QT_QPA_PLATFORM=offscreen python3 {REPO}/bin/chicago95-shutdown "
            f"--login-banner {tmp_path}/.local/share/chicago95/login-banner.png") in log


def test_dry_run_of_the_2000_look_alone_writes_the_look_before_redrawing_the_bevels(tmp_path):
    """chicago95-sync-colors draws the decoration and the taskbar with the look's bevel colours, read from
    chicago95rc: the look step writes it even without the Start menu."""
    subprocess.run([str(REPO / "install.sh"), "--plain", "--yes", "--dry-run", "--look=2000", "--components=look"],
                   capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60,
                   env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)})
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()
    style = log.find("would: kwriteconfig6 --file chicago95rc --group StartMenu --key style 2000")
    redraw = log.find("chicago95-sync-colors --force")

    assert -1 < style < redraw, (style, redraw)


def test_dry_run_of_the_base_theme_selects_chicago95_for_gtk_3_and_4(tmp_path):
    """GTK programs draw their own widgets, and GTK 4 its own title bars: both take the classic theme."""
    subprocess.run([str(REPO / "install.sh"), "--plain", "--yes", "--dry-run", "--components=base"],
                   capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60,
                   env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path),
                        "CHICAGO95_SRC": str(Path.home() / "src/Chicago95")})
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()

    assert [f"would: kwriteconfig6 --file {tmp_path}/.config/gtk-{version}/settings.ini --group Settings --key gtk-theme-name Chicago95" in log
            for version in ("3.0", "4.0")] == [True, True]
