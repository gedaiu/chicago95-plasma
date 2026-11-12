"""Our Run dialog against the 1995 original (tests/references/win95run.png): the dialog with its frame and title is
347x163; the icon, the prompt, the label, the field and the three buttons sit where the original's do. The icon,
the lettering and the title's buttons are other artwork and are masked; everything else must match pixel for pixel,
with the original's 3D light (#DFDFDF, the second line of a button's bevel) read as the face, as our palette draws it.
"""

import pytest
from conftest import needs_ui_font
from reference import differing_pixels, qimage_to_pil, screenshot
from test_install import dry_run_log, kwriteconfig

SIZE = (347, 163)
LIGHT, FACE = (223, 223, 223), (192, 192, 192)
# Masks in the dialog's coordinates: the icon, the two prompt lines, "Open:", the title's text and buttons, and
# each button's caption, and the text cursor at the field's start.
MASKS = [
    (14, 34, 52, 72),
    (54, 38, 340, 66),
    (8, 82, 52, 100),
    (59, 84, 66, 101),
    (4, 4, 90, 21),
    (300, 3, 345, 21),
    (110, 128, 170, 142),
    (190, 128, 245, 142),
    (268, 128, 328, 142),
]


@pytest.fixture(scope="module")
def ours(qt_app, tmp_path_factory):
    import chicago95ui
    from aurorae_model import build_theme
    from conftest import load_script

    chicago95ui.DECORATION = build_theme(tmp_path_factory.mktemp("aurorae-1995"), "1995")
    run = load_script("chicago95-run")
    dialog = run.RunDialog({"style": "1995", "osName": "Windows"}, [], [], history=[])
    dialog.show()
    qt_app.processEvents()
    image = qimage_to_pil(dialog.grab().toImage())
    image.save(tmp_path_factory.getbasetemp() / "ours-run-1995.png")
    dialog.close()
    return image


def without_light(image):
    mapped = image.copy()
    pixels = mapped.load()
    for x in range(mapped.width):
        for y in range(mapped.height):
            if pixels[x, y] == LIGHT:
                pixels[x, y] = FACE
    return mapped


def test_the_dialog_is_347_by_163_like_the_original(ours):
    assert ours.size == SIZE


@needs_ui_font
def test_everything_but_the_icon_and_the_lettering_matches_the_original_pixel_for_pixel(ours, tmp_path):
    count = differing_pixels(
        without_light(screenshot("win95run")), without_light(ours), MASKS, tmp_path / "run-diff.png"
    )

    assert count == 0, f"{count} pixels differ; diff saved in {tmp_path}"


def test_setup_installs_run_with_its_place_above_the_taskbar_and_the_originals_keys(tmp_path):
    log = dry_run_log(tmp_path, "--components=startmenu", "--screen=1280x1024@1")

    assert (
        "bin/chicago95-run -> ~/.local/bin/chicago95-run" in log.replace(str(tmp_path), "~"),
        "would: write kwin rule [chicago95-run]" in log,
        "would: kwriteconfig6 --file kglobalshortcutsrc --group services --group chicago95-run.desktop "
        "--key _launch Meta+R" in log,
        "would: kwriteconfig6 --file kglobalshortcutsrc --group services --group chicago95-startmenu.desktop "
        "--key _launch Ctrl+Esc" in log,
        "--group chicago95-showdesktop.desktop --key _launch Meta+D\tMeta+M" in log,
        "--group thunar.desktop --key _launch Meta+E" in log,
        kwriteconfig(
            "kwinrc",
            "ModifierOnlyShortcuts",
            "Meta",
            "org.kde.kglobalaccel,/component/chicago95_startmenu_desktop,org.kde.kglobalaccel.Component,invokeShortcut,_launch",
        )
        in log,
    ) == (True, True, True, True, True, True, True)
