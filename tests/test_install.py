import subprocess
import time

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
