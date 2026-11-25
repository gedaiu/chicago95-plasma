"""Our Run dialog against the 1995 original (tests/references/win95run.png): the dialog with its frame and title is
347x163; the icon, the prompt, the label, the field and the three buttons sit where the original's do. The icon,
the lettering and the title's buttons are other artwork and are masked; everything else must match pixel for pixel,
with the original's 3D light (#DFDFDF, the second line of a button's bevel) read as the face, as our palette draws it.
"""

import pytest
from conftest import REPO, needs_ui_font
from reference import differing_pixels, qimage_to_pil, rgb565, screenshot
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
    files = log.replace(str(tmp_path), "~")
    assert "lib/chicago95aerobutton.py -> ~/.local/lib/chicago95/chicago95aerobutton.py" in files
    assert "data/run/aero-down.svg -> ~/.local/share/chicago95/run/aero-down.svg" in files

    assert (
        "bin/chicago95-run -> ~/.local/bin/chicago95-run" in files,
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


@pytest.mark.parametrize(("scale", "height"), [("1", 163), ("1.25", 160)])
def test_setup_measures_the_windows_98_run_dialog_at_the_selected_scale(tmp_path, scale, height):
    from chicago95appliers import run_window_height
    from chicago95setup import Setup

    setup = Setup(
        {"WIDGET_STYLE": "classic", "START_MENU_STYLE": "1998", "SCALE": scale},
        repo=REPO,
        home=tmp_path,
        environment={},
    )
    assert run_window_height(setup) == height


@pytest.mark.parametrize("edition", ["win95-osr2-run", "win98-se-run"])
def test_classic_run_controls_match_guest_geometry(ours, edition):
    native = screenshot(edition)
    assert native.size == ours.size
    # The combo box and buttons share a layout on 95 and 98. Compare their
    # outlines separately from focus, the text cursor and the selected font.
    actual = without_light(ours)
    for band in ((57, 82, 332, 84), (57, 100, 332, 103), (93, 124, 333, 127), (93, 144, 333, 147)):
        assert actual.crop(band).tobytes() == native.crop(band).tobytes(), (edition, band)


@pytest.mark.parametrize(("style", "guest"), [("2000", "win2000-pro"), ("2001", "xp-sp3-classic")])
def test_nt_classic_run_matches_guest(qt_app, tmp_path, monkeypatch, style, guest):
    import chicago95ui
    from aurorae_model import build_theme
    from conftest import load_script
    from reference import LOOK_2000_KDEGLOBALS, installed_look

    native = screenshot(guest + "-run")
    monkeypatch.setattr(chicago95ui, "DECORATION", build_theme(tmp_path, style))
    with installed_look(qt_app, f"[StartMenu]\nstyle={style}\n[Look]\nbevel=2000\n", LOOK_2000_KDEGLOBALS):
        dialog = load_script("chicago95-run").RunDialog({"style": style, "widgetStyle": "classic"}, [], [], [])
        image = qimage_to_pil(dialog.grab().toImage())
        dialog.close()
    assert image.size == native.size
    if style == "2000":
        image = rgb565(image)
        icon = image.crop((14, 40, 46, 72))
        assert icon.tobytes() == screenshot("win2000-pro-120dpi-run-icon").tobytes()
    for x in (75, 190, 266):
        for y in (81, 82, 83, 84, 100, 101, 102, 103):
            assert image.getpixel((x, y)) == native.getpixel((x, y)), (x, y)
    for x in (190, 266):
        for y in (135, 136, 137, 156, 157, 158, 159):
            assert image.getpixel((x, y)) == native.getpixel((x, y)), (x, y)


def test_classic_run_hourglass_matches_96_and_120_dpi_guests(ours):
    icon = ours.crop((14, 40, 46, 72))
    for guest in ("win95-osr2-run", "win98-se-run"):
        assert icon.tobytes() == screenshot(guest).crop((14, 40, 46, 72)).tobytes()
    for guest in ("win95-osr2", "win98-se"):
        assert icon.tobytes() == screenshot(guest + "-120dpi-run-icon").tobytes()


@pytest.mark.parametrize("guest", ["xp-sp3", "xp-sp3-classic"])
def test_xp_run_svg_at_120_dpi_matches_the_sp3_guest(qt_app, guest):
    from conftest import REPO
    from PIL import Image, ImageChops, ImageStat
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QIcon, QImage

    native = screenshot(guest + "-120dpi-run-icon")
    icon = QIcon(str(REPO / "data/run/xp-run.svg")).pixmap(QSize(32, 32), 1.25)
    assert icon.width() == icon.height() == 40
    pixels = icon.toImage().convertToFormat(QImage.Format_RGBA8888)
    rgba = Image.frombytes("RGBA", (40, 40), bytes(pixels.constBits()))
    actual = Image.new("RGBA", rgba.size, native.getpixel((0, 0)) + (255,))
    actual.alpha_composite(rgba)
    diff = ImageChops.difference(actual.convert("RGB"), native)
    # Exclude the empty top and bottom margins of the native 40-pixel icon.
    assert max(ImageStat.Stat(diff.crop((0, 8, 39, 32))).mean) < 25
