"""Setup's Windows XP icon set: the B00merang pack, cloned at install time, over a fallback theme built from the
user's own XP icon archives in ~/Downloads when they are there (luna/icons/xp_originals.py)."""

import configparser
import subprocess
import zipfile

from conftest import REPO, load_script, run_bash_with_steps
from PIL import Image

XP_REPO = "https://github.com/B00merang-Artwork/Windows-XP"


def dry_run(tmp_path, script):
    return run_bash_with_steps(tmp_path, f"SETUP_DRY_RUN=1 SETUP_LOG=$HOME/log {script}; cat $HOME/log")


def installed_xp_theme(home):
    theme = home / ".local/share/icons/Windows-XP"
    theme.mkdir(parents=True)
    (theme / "index.theme").write_text("[Icon Theme]\nName=Windows XP\nDirectories=48x48/places\n")
    return theme


def numbered_archive(home):
    downloads = home / "Downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    icon = home / "folder.ico"
    Image.new("RGBA", (48, 48), (255, 204, 0, 255)).save(icon, sizes=[(48, 48)])
    with zipfile.ZipFile(downloads / "ICON.zip", "w") as archive:
        archive.write(icon, "ICON/19.ico")


def fallback(home):
    subprocess.run(
        [
            "bash",
            "-c",
            f"REPO={REPO}; source {REPO}/setup/steps.sh; SETUP_DRY_RUN=0 SETUP_LOG=$HOME/log xp_icon_fallback",
        ],
        env={"PATH": "/usr/bin:/bin", "HOME": str(home)},
        timeout=60,
        check=False,
    )
    index = configparser.ConfigParser(interpolation=None)
    index.read(home / ".local/share/icons/Windows-XP/index.theme")
    return index["Icon Theme"].get("Inherits")


def test_the_windows_xp_icon_set_clones_the_b00merang_pack_into_the_users_icons(tmp_path):
    log = "\n".join(dry_run(tmp_path, "SETUP_ICONS=windowsxp apply_icon_set"))

    assert (
        f"would: git clone --depth 1 {XP_REPO} {tmp_path}/src/Windows-XP" in log,
        f"{tmp_path}/src/Windows-XP" in log and f"{tmp_path}/.local/share/icons/Windows-XP" in log,
    ) == (True, True)


def test_the_users_xp_icon_archives_become_a_fallback_the_xp_set_inherits_first(tmp_path):
    installed_xp_theme(tmp_path)
    numbered_archive(tmp_path)

    inherits = fallback(tmp_path)

    assert (
        inherits,
        (tmp_path / ".local/share/icons/Windows-XP-Originals/48x48/xp/folder.png").is_file(),
    ) == ("Windows-XP-Originals,Chicago95,hicolor", True)


def test_without_the_archives_the_xp_set_falls_back_to_chicago95_alone(tmp_path):
    installed_xp_theme(tmp_path)

    inherits = fallback(tmp_path)

    assert (inherits, (tmp_path / ".local/share/icons/Windows-XP-Originals").exists()) == ("Chicago95,hicolor", False)


def test_the_xp_look_takes_the_windows_xp_icon_set_by_default(tmp_path):
    lines = run_bash_with_steps(tmp_path, "apply_look luna >/dev/null 2>&1; echo $SETUP_ICONS")

    assert lines[-1:] == ["windowsxp"]


def test_the_control_panel_offers_the_windows_xp_icons_and_its_xp_scheme_picks_them():
    control_panel = load_script("chicago95-control-panel")

    assert (("Windows XP", "windowsxp") in control_panel.ICON_SETS, control_panel.LOOK_PRESETS["luna"]["ICONS"]) == (
        True,
        "windowsxp",
    )
