import importlib.util
import subprocess

import pytest
from conftest import REPO, run_bash_with_steps
from PySide6.QtGui import QImage


def background_script(tmp_path, assignments=""):
    lines = run_bash_with_steps(tmp_path, f"{assignments} background_script")
    return " ".join(" ".join(lines).split())


def load_pattern_module():
    spec = importlib.util.spec_from_file_location("background_pattern", REPO / "setup/background_pattern.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_background_is_the_classic_teal_colour_wallpaper_by_default(tmp_path):
    script = background_script(tmp_path)

    assert (
        'desktop.wallpaperPlugin = "org.kde.color";' in script,
        'desktop.currentConfigGroup = ["Wallpaper", "org.kde.color", "General"];' in script,
        'desktop.writeConfig("Color", "0,128,128");' in script,
    ) == (True, True, True)


def test_background_color_is_written_as_red_green_blue(tmp_path):
    assert 'desktop.writeConfig("Color", "255,0,16");' in background_script(tmp_path, "SETUP_BACKGROUND_COLOR=#FF0010")


def test_background_color_that_is_not_a_hex_colour_falls_back_to_teal(tmp_path):
    script = background_script(tmp_path, "SETUP_BACKGROUND_COLOR='red\"); evil(\"'")

    assert ('desktop.writeConfig("Color", "0,128,128");' in script, "evil" in script) == (True, False)


@pytest.mark.parametrize("fill, fill_mode", [("center", 6), ("tile", 3), ("stretch", 0), ("", 6)])
def test_background_image_is_written_as_a_file_url_with_the_fill_mode(tmp_path, fill, fill_mode):
    script = background_script(
        tmp_path, f"SETUP_BACKGROUND_MODE=image SETUP_BACKGROUND_IMAGE=/home/u/wall.png SETUP_BACKGROUND_FILL={fill}"
    )

    assert (
        'desktop.wallpaperPlugin = "org.kde.image";' in script,
        'desktop.writeConfig("Image", "file:///home/u/wall.png");' in script,
        f'desktop.writeConfig("FillMode", {fill_mode});' in script,
    ) == (True, True, True)


def test_background_pattern_is_the_generated_picture_tiled(tmp_path):
    script = background_script(tmp_path, "SETUP_BACKGROUND_MODE=pattern")

    assert (
        f'desktop.writeConfig("Image", "file://{tmp_path}/.local/share/chicago95/pattern.png");' in script,
        'desktop.writeConfig("FillMode", 3);' in script,
    ) == (True, True)


def test_background_script_parses_as_javascript(qt_app, tmp_path):
    from PySide6.QtQml import QJSEngine, QJSValue

    engine = QJSEngine()
    outcome = engine.evaluate(background_script(tmp_path, "SETUP_BACKGROUND_MODE=image SETUP_BACKGROUND_IMAGE=/a.png"))

    assert outcome.errorType() == QJSValue.ErrorType.ReferenceError


def test_dry_run_of_the_background_component_sets_the_saved_colour(tmp_path):
    saved = tmp_path / "setup.conf"
    saved.write_text("BACKGROUND_MODE=color\nBACKGROUND_COLOR=#102030\n")
    subprocess.run(
        [str(REPO / "install.sh"), "--plain", "--yes", "--dry-run", f"--settings={saved}", "--components=background"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)},
    )
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()

    assert 'desktop.writeConfig("Color", "16,32,48");' in log


def test_dry_run_of_a_pattern_background_draws_the_pattern_first(tmp_path):
    saved = tmp_path / "setup.conf"
    saved.write_text("BACKGROUND_MODE=pattern\nBACKGROUND_PATTERN=diagonal\nBACKGROUND_COLOR=#102030\n")
    subprocess.run(
        [str(REPO / "install.sh"), "--plain", "--yes", "--dry-run", f"--settings={saved}", "--components=background"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)},
    )
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()

    assert (
        f"would: python3 {REPO}/setup/background_pattern.py diagonal #102030 {tmp_path}/.local/share/chicago95/pattern.png"
        in log
    )


def test_pattern_png_draws_set_bits_black_on_the_background_colour(tmp_path):
    diagonal = [0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01]
    picture = tmp_path / "pattern.png"

    load_pattern_module().pattern_png(diagonal, "#008080", picture)

    image = QImage(str(picture))
    assert (
        image.width(),
        image.height(),
        image.pixelColor(0, 0).name(),
        image.pixelColor(1, 0).name(),
        image.pixelColor(1, 1).name(),
    ) == (8, 8, "#000000", "#008080", "#000000")


def test_named_patterns_are_eight_rows_of_eight_bits():
    assert {name: len(rows) for name, rows in load_pattern_module().PATTERNS.items()} == {
        "checks": 8,
        "diagonal": 8,
        "grid": 8,
        "dots": 8,
    }
