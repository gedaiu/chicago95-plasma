"""The XP Plymouth screen with the user's branding: its logo picture drawn at install time from the wordmark the
boot screen shows (luna/plymouth/branded_logo.py), and centred where the XP wordmark's centre is."""

import subprocess
import sys

from conftest import REPO, run_bash_with_steps
from PIL import Image

SCRIPT = REPO / "luna/plymouth/Chicago95-XP/Chicago95-XP.script"


def test_the_script_centres_the_logo_on_the_xp_wordmarks_centre():
    """331 units less half the picture: the 244 pixel XP logo lands at 209, where it always was."""
    assert "logo.SetPosition(Math.Int(layout_x + 331 * unit - logo_image.GetWidth() * fit / 2)" in SCRIPT.read_text()


def test_the_branded_logo_pictures_hold_the_users_logo_at_1x_and_2x(tmp_path):
    logo = tmp_path / "brand.png"  # not logo.png: that is the picture being written
    Image.new("RGB", (64, 64), (255, 0, 0)).save(logo)
    subprocess.run(
        [sys.executable, str(REPO / "luna/plymouth/branded_logo.py"), "--out", str(tmp_path), "--name", "Windows2026"]
        + ["--company", "KDE", "--edition", "Professional", "--logo", str(logo)],
        env={"QT_QPA_PLATFORM": "offscreen", "PATH": "/usr/bin:/bin"},
        timeout=60,
        check=True,
    )
    pictures = [Image.open(tmp_path / name).convert("RGB") for name in ("logo.png", "logo@2x.png")]
    reds = [sum(pixel == (255, 0, 0) for pixel in picture.getdata()) for picture in pictures]

    assert ([picture.size for picture in pictures], reds[0] > 1000, reds[1] > 4000) == (
        [(round(220 * 1.85), int(68 * 1.85)), (round(220 * 3.7), int(68 * 3.7))],  # Qt floors the heights
        True,
        True,
    )


def plymouth_log(tmp_path, banner):
    lines = run_bash_with_steps(
        tmp_path,
        f"plymouth-set-default-theme() {{ :; }}; SETUP_DRY_RUN=1; SETUP_LOG=$HOME/log; SETUP_BOOT_STYLE=luna; "
        f"SETUP_BANNER_TEXT='{banner}'; ui_sudo() {{ return 1; }}; ui_message() {{ :; }}; "
        "command() { return 0; }; step_plymouth; cat $HOME/log",
    )
    return "\n".join(lines)


def test_setup_draws_the_branded_plymouth_logo_when_a_name_is_set(tmp_path):
    assert "luna/plymouth/branded_logo.py" in plymouth_log(tmp_path, "Windows2026")


def test_setup_keeps_the_xp_wordmark_on_plymouth_when_no_name_is_set(tmp_path):
    assert "branded_logo.py" not in plymouth_log(tmp_path, "")
