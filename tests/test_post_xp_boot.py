"""Original animation timing, editable content, preview routing and Plymouth parity."""

import ctypes
import json
import os
import re
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest
from conftest import REPO, load_script, run_bash_with_steps
from PIL import Image, ImageChops, ImageStat
from post_xp_boot import FIELDS, STYLES
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest
from reference import qimage_to_pil

SPLASH = REPO / "splash/chicago95.splashscreen/contents/splash"


@contextmanager
def boot_view(style="7", options=None, size=(960, 540)):
    view = QQuickView()
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(*size)
    view.setInitialProperties({"style": style, "options": options or {}, "animated": False})
    view.setSource(QUrl.fromLocalFile(str(SPLASH / "PostXpBoot.qml")))
    assert not view.errors(), [error.toString() for error in view.errors()]
    view.show()
    QTest.qWait(40)
    try:
        yield view, view.rootObject()
    finally:
        view.close()


def image_at(view, root, elapsed):
    root.setProperty("elapsed", elapsed)
    QTest.qWait(20)
    return qimage_to_pil(view.grabWindow()).convert("RGB")


@pytest.mark.parametrize("style", [value for _, value in STYLES])
def test_each_boot_screen_draws_and_animates(qt_app, style):
    with boot_view(style) as (view, root):
        first = image_at(view, root, 100)
        second = image_at(view, root, 2800)
        assert first.getpixel((0, 0)) == (0, 0, 0)
        assert second.getbbox() is not None
        assert ImageChops.difference(first, second).getbbox() is not None


def test_seven_plays_intro_once_then_loops_the_original_45_frames(qt_app):
    with boot_view() as (view, root):
        assert (root.property("frameCount"), root.property("fps")) == (105, 15)
        for milliseconds, expected in [(0, 0), (3999, 59), (4000, 60), (6999, 104), (7000, 60), (10000, 60)]:
            image_at(view, root, milliseconds)
            assert root.property("frame") == expected
        assert image_at(view, root, 4000) == image_at(view, root, 7000)


def test_dots_include_the_complete_original_glyph_cycle(qt_app):
    with boot_view("11") as (view, root):
        assert root.property("frameCount") == 117
        assert image_at(view, root, 100) == image_at(view, root, 100 + 117 * 1000 / 30)


@pytest.mark.parametrize("style", ["vista", "7"])
def test_default_lettering_matches_external_video_pixels(qt_app, style):
    with boot_view(style, size=(1920, 1080)) as (view, root):
        actual = image_at(view, root, 100)
        expected = Image.open(REPO / "tests/references" / f"boot-{style}-video.png").convert("RGB")
        boxes = [(800, 864, 1120, 912)] if style == "vista" else [(800, 720, 1120, 800), (800, 1000, 1120, 1048)]
        for box in boxes:
            assert ImageChops.difference(actual.crop(box), expected.crop(box)).getbbox() is None


@pytest.mark.parametrize("style", ["8", "8.1", "10", "11"])
def test_logo_geometry_tracks_the_video_within_two_pixels(qt_app, style):
    def bounds(image):
        crop = image.crop((860, 310, 1070, 520))
        # Restrict to the saturated blue artwork, away from codec ringing.
        mask = Image.new("L", crop.size)
        mask.putdata([255 if b > 100 and b > r * 2 else 0 for r, g, b in crop.get_flattened_data()])
        return mask.getbbox()

    with boot_view(style, size=(1920, 1080)) as (view, root):
        actual = image_at(view, root, 100)
        expected = Image.open(REPO / "tests/references" / f"boot-{style}-video.png").convert("RGB")
        assert all(abs(a - b) <= 2 for a, b in zip(bounds(actual), bounds(expected), strict=True)), (
            bounds(actual),
            bounds(expected),
        )


@pytest.mark.parametrize("style", ["vista", "7", "8", "8.1", "10", "11"])
def test_all_content_and_palette_overrides_are_live(qt_app, tmp_path, style):
    logo = tmp_path / "logo.png"
    Image.new("RGB", (50, 50), "red").save(logo)
    options = {
        "name": "My OS",
        "text": "Starting My OS",
        "footer": "My company",
        "logo": str(logo),
        "background": "#123456",
        "foreground": "#fedcba",
        "font": "DejaVu Sans",
        "logoSize": "200",
    }
    with boot_view(style, options) as (view, root):
        picture = image_at(view, root, 5000)
        assert picture.getpixel((0, 0)) == (18, 52, 86)
        assert root.findChild(QObject, "bootName").property("text") == "My OS"
        assert root.findChild(QObject, "bootText").property("text") == "Starting My OS"
        assert root.findChild(QObject, "bootFooter").property("text") == "My company"
        assert not root.property("referenceFooter")
        pixel = picture.getpixel((480, 270) if style in ("vista", "7") else (485, 207))
        if style == "7":
            # The travelling white highlight brightens the custom logo.
            assert pixel[0] == 255 and pixel[1] == pixel[2] and pixel[1] < 90
        else:
            assert pixel == (255, 0, 0)


def test_seven_original_artwork_has_no_black_box_on_custom_background(qt_app):
    with boot_view("7", {"background": "#123456"}) as (view, root):
        picture = image_at(view, root, 5000)
        assert picture.getpixel((410, 200)) == (18, 52, 86)
        assert picture.getpixel((480, 270)) != (18, 52, 86)


def test_custom_sprite_sheet_honours_frames_timing_and_loop(qt_app, tmp_path):
    sheet = Image.new("RGB", (32, 96))
    for index, color in enumerate(["red", "green", "blue"]):
        sheet.paste(color, (0, index * 32, 32, (index + 1) * 32))
    path = tmp_path / "animation.png"
    sheet.save(path)
    options = {"animation": str(path), "frames": "3", "fps": "10", "loopStart": "1", "logo": "none"}
    with boot_view("11", options) as (view, root):
        colors = [image_at(view, root, time).getpixel((480, 270)) for time in [0, 100, 200, 300, 400]]
        assert colors == [(255, 0, 0), (0, 128, 0), (0, 0, 255), (0, 128, 0), (0, 0, 255)]


def test_preview_options_and_setup_options_are_identical_and_quoted(qt_app, tmp_path):
    panel = load_script("chicago95-control-panel")
    values = {key: 'a "quoted" value' for key in FIELDS}
    preview = panel.LoadingPreview.settings_js(values)
    assignments = "; ".join(f"SETUP_{key}='a \"quoted\" value'" for key in FIELDS)
    emitted = "\n".join(run_bash_with_steps(tmp_path, assignments + "; write_post_xp_options"))
    shell_options = json.loads(emitted.removeprefix("var postXp = ").replace(",}", "}"))
    preview_line = next(line for line in preview.splitlines() if line.startswith("var postXp = "))
    assert shell_options == json.loads(preview_line.removeprefix("var postXp = "))
    assert set(shell_options) == set(FIELDS.values())


@pytest.mark.parametrize("style", [value for _, value in STYLES])
def test_control_panel_routes_all_styles_and_skips_text_loader(qt_app, style):
    panel = load_script("chicago95-control-panel")
    preview = panel.LoadingPreview()
    preview.refresh({"BOOT_STYLE": style, "BOOT_TEXT": "Custom boot"})
    preview.show()
    QTest.qWait(50)
    root = preview.dialog()
    assert root.property("postXp")
    screen = root.findChild(QObject, "postXpBoot")
    assert screen is not None
    assert screen.findChild(QObject, "bootText").property("text") == "Custom boot"
    root.playBootPreview()
    assert not root.property("textBoot")
    preview.close()


def test_exported_plymouth_frames_match_custom_preview_and_parse(qt_app, tmp_path):
    panel = load_script("chicago95-control-panel")
    exporter = load_script("chicago95-post-xp-boot")
    source, output = tmp_path / "splash", tmp_path / "theme"
    shutil.copytree(SPLASH, source)
    values = {
        "BOOT_STYLE": "8",
        "BOOT_BACKGROUND": "#123456",
        "BOOT_TEXT": "Booting My OS",
        "BOOT_FRAMES": "4",
        "BOOT_FPS": "12",
        "BOOT_LOOP_START": "1",
    }
    (source / "settings.js").write_text(panel.LoadingPreview.settings_js(values))
    exporter.build(source, output, (960, 540), REPO / "setup/post_xp_boot.script.in")
    meta = json.loads((output / "animation.json").read_text())
    background = Image.open(output / "background.png").convert("RGB")
    with boot_view("8", {name: values[key] for key, name in FIELDS.items() if key in values}) as (view, root):
        for index in range(4):
            composite = background.copy()
            composite.paste(Image.open(output / f"frame-{index}.png"), (meta["AX"], meta["AY"]))
            expected = image_at(view, root, index * 1000 / 12 + 0.01)
            assert ImageChops.difference(composite, expected).getbbox() is None
    script = output / "Chicago95-8.script"
    assert "@" not in script.read_text()
    plugin = Path("/usr/lib64/plymouth/script.so")
    if plugin.exists():
        for library in ("libply.so.5", "libply-splash-core.so.5", "libply-splash-graphics.so.5"):
            ctypes.CDLL(library, mode=ctypes.RTLD_GLOBAL)
        parse = ctypes.CDLL(str(plugin)).script_parse_file
        parse.restype, parse.argtypes = ctypes.c_void_p, [ctypes.c_char_p]
        assert parse(str(script).encode())
    assert (meta["FRAMES"], meta["LOOP_START"], meta["FPS"]) == (4, 1, 12)


def test_seven_exports_shutdown_with_its_own_spinner_and_status_text(qt_app, tmp_path, monkeypatch):
    art = tmp_path / "data/chicago95/session"
    art.mkdir(parents=True)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    Image.new("RGB", (64, 48), "#1d568a").save(art / "background", format="PNG")
    strip = Image.new("RGB", (360, 20))
    for i in range(18):
        strip.paste((20 + 10 * i, 90, 210), (i * 20, 0, (i + 1) * 20, 20))
    strip.save(art / "spinner.png")
    source, output = tmp_path / "splash", tmp_path / "theme"
    shutil.copytree(SPLASH, source)
    settings = load_script("chicago95-control-panel").LoadingPreview.settings_js(
        {"BOOT_STYLE": "7", "BOOT_FRAMES": "1"}
    )
    (source / "settings.js").write_text(settings)
    load_script("chicago95-post-xp-boot").build(source, output, (640, 480), REPO / "setup/post_xp_boot.script.in")
    assert len({Image.open(path).tobytes() for path in output.glob("shutdown-*.png")}) == 18
    assert Image.open(output / "shutdown.png").getpixel((0, 0))[:3] == (29, 86, 138)
    assert Image.open(output / "background.png").getpixel((0, 0))[:3] == (0, 0, 0)
    script = (output / "Chicago95-7.script").read_text()
    # Eighteen displayed poses recurred every 0.834 s in the 30 Hz Aero captures.
    shutdown_branch = script.split('image_name = "shutdown.png";', 1)[1].split("}", 1)[0]
    fps = float(shutdown_branch.split("fps = ", 1)[1].split(";", 1)[0])
    assert 18 / fps == pytest.approx(0.834, abs=1 / 30)
    assert 'if (1 && (Plymouth.GetMode() == "shutdown" || Plymouth.GetMode() == "reboot"))' in script


@pytest.mark.parametrize("width,height,scale", [(800, 600, 1), (1024, 768, 1), (1280, 960, 1.5)])
def test_seven_shutdown_status_matches_sp1(tmp_path, width, height, scale):
    source = tmp_path / "splash"
    output = tmp_path / "theme"
    shutil.copytree(SPLASH, source)
    (source / "settings.js").write_text(
        load_script("chicago95-control-panel").LoadingPreview.settings_js({"BOOT_STYLE": "7", "BOOT_FRAMES": "1"})
    )
    subprocess.run(
        [
            sys.executable,
            str(REPO / "bin/chicago95-post-xp-boot"),
            "--size",
            f"{round(width / scale)}x{round(height / scale)}",
            "--scale",
            str(scale),
            "--splash",
            str(source),
            "--out",
            str(output),
        ],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "QT_QUICK_BACKEND": "software"},
        check=True,
    )
    reference = "144dpi" if scale == 1.5 else str(width)
    native = Image.open(REPO / f"tests/references/win7-sp1-shutdown-{reference}.png").convert("RGB")
    assert Image.open(output / "shutdown.png").size == (width, height)
    x, y = width // 2 - round(120 * scale), height // 2 - round(80 * scale)
    actual = Image.open(output / "shutdown.png").convert("RGB").crop((x, y, x + native.width, y + native.height))

    def text_bounds(picture):
        # Skip the spinner and threshold all channels to exclude the blue background.
        red, green, blue = picture.crop((round(38 * scale), 0, picture.width, picture.height)).split()
        ink = ImageChops.darker(ImageChops.darker(red, green), blue)
        bounds = ink.point(lambda v: 255 if v > 230 else 0).getbbox()
        assert bounds
        return bounds

    left, top, right, bottom = text_bounds(actual)
    ref_left, ref_top, ref_right, ref_bottom = text_bounds(native)
    assert (top, bottom, (left + right) / 2) == pytest.approx(
        (ref_top, ref_bottom, (ref_left + ref_right) / 2), abs=3 * scale
    )
    script = (output / "Chicago95-7.script").read_text()
    side = round(20 * scale)
    assert Image.open(output / "shutdown-0.png").size == (side, side)
    spinner = re.search(rf"ax = (\d+); ay = (\d+); aw = {side}; ah = {side};", script)
    assert spinner
    assert int(spinner[1]) == pytest.approx(width // 2 - round(103 * scale), abs=5 * scale)
    assert int(spinner[2]) == pytest.approx(height // 2 - round(60 * scale), abs=1)
    # The default test font can substitute for Segoe UI.
    assert right - left == pytest.approx(ref_right - ref_left, abs=12 * scale)


@pytest.mark.parametrize("style", [value for _, value in STYLES])
def test_setup_dispatches_to_post_xp_exporter(tmp_path, style):
    lines = run_bash_with_steps(
        tmp_path,
        f"plymouth-set-default-theme() {{ :; }}; SETUP_DRY_RUN=1; SETUP_LOG=$HOME/log; SETUP_BOOT_STYLE={style}; "
        "ui_sudo() { return 1; }; ui_message() { :; }; ui_progress() { :; }; step_plymouth; cat $HOME/log",
    )
    assert "chicago95-post-xp-boot" in "\n".join(lines)


@pytest.mark.parametrize(
    "style,frame,box,budget",
    [
        ("7", 53, (800, 370, 1120, 710), 6),
        ("8", 77, (928, 808, 992, 872), 15),
    ],
)
def test_original_animation_shapes_match_external_video(qt_app, style, frame, box, budget):
    with boot_view(style, size=(1920, 1080)) as (view, root):
        actual = image_at(view, root, frame * 1000 / root.property("fps") + 0.01).crop(box)
        expected = Image.open(REPO / "tests/references" / f"boot-{style}-video.png").convert("RGB").crop(box)
        assert max(ImageStat.Stat(ImageChops.difference(actual, expected)).rms) <= budget


@pytest.mark.parametrize(
    "bad_options,message",
    [
        ({"BOOT_LOGO": "/missing/boot-logo.png"}, "file does not exist"),
        ({"BOOT_BACKGROUND": "not-a-color"}, "invalid color"),
        ({"BOOT_FPS": "fast"}, "expected a number"),
        ({"BOOT_FRAMES": "3", "BOOT_LOOP_START": "3"}, "below the frame count"),
    ],
)
def test_invalid_customizations_fail_before_export(qt_app, tmp_path, bad_options, message):
    panel = load_script("chicago95-control-panel")
    exporter = load_script("chicago95-post-xp-boot")
    source, output = tmp_path / "splash", tmp_path / "theme"
    shutil.copytree(SPLASH, source)
    (source / "settings.js").write_text(panel.LoadingPreview.settings_js({"BOOT_STYLE": "7", **bad_options}))
    with pytest.raises(ValueError, match=message):
        exporter.build(source, output, (960, 540), REPO / "setup/post_xp_boot.script.in")
    assert not output.exists()


def test_vista_trough_keeps_all_four_edges_in_small_previews(qt_app):
    with boot_view("vista", size=(640, 360)) as (view, root):
        picture = image_at(view, root, 800)
        for point in ((300, 265), (300, 272), (273, 269), (363, 269)):
            assert max(picture.getpixel(point)) >= 80


def test_seven_atlas_cells_render_without_neighbouring_frames(qt_app):
    sheet = Image.open(SPLASH / "postxp/seven.png").convert("RGBA")
    assert sheet.size == (3000, 1400)
    with boot_view("7", {"logoSize": "200"}, size=(1920, 1080)) as (view, root):
        for frame in (0, 14, 15, 59, 60, 89, 90, 104):
            actual = image_at(view, root, frame * 1000 / 15 + 0.01).crop((860, 440, 1060, 640))
            x, y = frame % 15 * 200, frame // 15 * 200
            cell = sheet.crop((x, y, x + 200, y + 200))
            expected = Image.new("RGBA", cell.size, (0, 0, 0, 255))
            expected.alpha_composite(cell)
            difference = ImageChops.difference(actual, expected.convert("RGB"))
            assert max(high for low, high in difference.getextrema()) <= 1, frame


def test_custom_seven_samples_logo_colors_reveals_and_loops(qt_app, tmp_path):
    logo = tmp_path / "logo.png"
    artwork = Image.new("RGBA", (80, 40))
    artwork.paste((230, 30, 130, 255), (10, 5, 70, 35))
    artwork.save(logo)
    with boot_view("7", {"logo": str(logo)}) as (view, root):
        early = image_at(view, root, 2000)
        canvas = root.findChild(QObject, "customSeven")
        palette = canvas.property("palette").toVariant()
        assert len(palette) == 4
        assert all(c[0] > c[2] > c[1] for c in palette)
        lights = early.crop((410, 200, 550, 340))
        assert lights.getbbox() is not None
        # Recolor actual light pixels, not just the stored palette.
        assert all(r >= b >= g for r, g, b in lights.get_flattened_data())
        formed = image_at(view, root, 4000)
        assert formed.getpixel((480, 270))[0] > 200
        # Preserve a wide logo's shape and transparent padding, with no flag bleed.
        assert formed.getpixel((480, 220)) == (0, 0, 0)
        assert ImageChops.difference(early, formed).getbbox() is not None
        assert ImageChops.difference(formed, image_at(view, root, 4700)).getbbox() is not None
        assert formed == image_at(view, root, 7000)


def test_custom_seven_can_disable_animation(qt_app, tmp_path):
    logo = tmp_path / "logo.png"
    Image.new("RGB", (32, 32), "red").save(logo)
    with boot_view("7", {"logo": str(logo), "animation": "none"}) as (view, root):
        assert not root.property("drawsAnimation")
        assert image_at(view, root, 0) == image_at(view, root, 5000)
        assert image_at(view, root, 0).getpixel((480, 270)) == (255, 0, 0)


def test_custom_seven_export_matches_preview(qt_app, tmp_path):
    panel = load_script("chicago95-control-panel")
    exporter = load_script("chicago95-post-xp-boot")
    logo = tmp_path / "logo.png"
    Image.new("RGBA", (80, 40), (20, 190, 120, 255)).save(logo)
    source, output = tmp_path / "splash", tmp_path / "theme"
    shutil.copytree(SPLASH, source)
    (source / "settings.js").write_text(panel.LoadingPreview.settings_js({"BOOT_STYLE": "7", "BOOT_LOGO": str(logo)}))
    exporter.build(source, output, (960, 540), REPO / "setup/post_xp_boot.script.in")
    meta = json.loads((output / "animation.json").read_text())
    assert (meta["FRAMES"], meta["LOOP_START"]) == (105, 60)
    background = Image.open(output / "background.png").convert("RGB")
    with boot_view("7", {"logo": str(logo)}) as (view, root):
        for frame in (0, 20, 55, 57, 60, 80, 104):
            composite = background.copy()
            composite.paste(Image.open(output / f"frame-{frame}.png"), (meta["AX"], meta["AY"]))
            expected = image_at(view, root, frame * 1000 / 15 + 0.01)
            assert ImageChops.difference(composite, expected).getbbox() is None


def test_custom_seven_samples_svg_quadrants_and_resamples_replacement(qt_app, tmp_path):
    logo = tmp_path / "logo.svg"
    logo.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80">'
        '<path fill="#f00" d="M0 0h40v40H0z"/><path fill="#0f0" d="M40 0h40v40H40z"/>'
        '<path fill="#00f" d="M0 40h40v40H0z"/><path fill="#ff0" d="M40 40h40v40H40z"/></svg>'
    )
    with boot_view("7", {"logo": str(logo)}) as (view, root):
        image_at(view, root, 3000)
        canvas = root.findChild(QObject, "customSeven")
        assert canvas.property("palette").toVariant() == [[255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 0]]
        replacement = tmp_path / "black.png"
        Image.new("RGB", (40, 40), "black").save(replacement)
        root.setProperty("options", {"logo": str(replacement)})
        QTest.qWait(50)
        image_at(view, root, 3200)
        assert canvas.property("palette").toVariant() == [[255, 255, 255]] * 4


def test_custom_seven_glows_around_open_logo_without_filling_its_hole(qt_app, tmp_path):
    from PIL import ImageDraw

    logo = tmp_path / "open-logo.png"
    artwork = Image.new("RGBA", (80, 80))
    ImageDraw.Draw(artwork).ellipse((10, 10, 70, 70), outline=(70, 200, 255, 255), width=4)
    artwork.save(logo)
    with boot_view("7", {"logo": str(logo)}) as (view, root):
        formed = image_at(view, root, 4000)
        assert formed.getpixel((480, 270)) == (0, 0, 0)
        # Outside the opaque ring, a genuine silhouette halo is visible.
        assert max(formed.getpixel((435, 270))) > 0
        assert formed.getpixel((410, 200)) == (0, 0, 0)
        assert ImageChops.difference(formed, image_at(view, root, 5000)).getbbox() is not None
        assert formed == image_at(view, root, 7000)
