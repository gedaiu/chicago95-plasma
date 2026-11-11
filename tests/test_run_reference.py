"""Our Run dialog against the 1995 original (tests/references/win95run.png): the dialog with its frame and title is
347x163; the icon, the prompt, the label, the field and the three buttons sit where the original's do. The icon,
the lettering and the title's buttons are other artwork and are masked; everything else must match pixel for pixel.
"""

import pytest
from conftest import needs_ui_font
from reference import differing_pixels, qimage_to_pil, screenshot

SIZE = (347, 163)
# Masks in the dialog's coordinates: the icon, the two prompt lines, "Open:", the title's text and buttons, and
# each button's caption.
MASKS = [
    (14, 34, 52, 72),
    (58, 38, 340, 66),
    (18, 84, 52, 98),
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


def test_the_dialog_is_347_by_163_like_the_original(ours):
    assert ours.size == SIZE


@needs_ui_font
def test_everything_but_the_icon_and_the_lettering_matches_the_original_pixel_for_pixel(ours, tmp_path):
    count = differing_pixels(screenshot("win95run"), ours, MASKS, tmp_path / "run-diff.png")

    assert count == 0, f"{count} pixels differ; diff saved in {tmp_path}"
