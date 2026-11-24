"""Compare caption button artwork with native guest captures in each interaction state."""

import subprocess
import sys

import numpy as np
import pytest
from aurorae_model import build_theme
from conftest import REPO
from PIL import Image
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from reference import REFERENCES, qimage_to_pil, rgb565, theme_references

BUTTONS = ("minimize", "maximize", "close")
STATES = ("rest", "hover", "pressed", "disabled", "restore", "cancelled")
ELEMENTS = {
    "rest": "active-center",
    "hover": "hover-center",
    "pressed": "pressed-center",
    "disabled": "deactivated-center",
    "restore": "active-center",
    "cancelled": "active-center",
}
CAPTION_REFERENCES = {
    metadata["look"]: (folder / "caption-states.png", metadata["caption_scale"])
    for folder, metadata in theme_references(REFERENCES)
}
LOOKS = tuple(CAPTION_REFERENCES)
CLASSIC = ("1995", "1998", "2000", "2001")
DISABLED_CLOSE_MATTES = ("dark", "light", "blue")
# Upper bounds from the native-size comparisons below. Strict mode uses
# zero RGB differences for each button and reports the pixel count.
RGB_LIMITS = {
    "luna": {"rest": 3.9, "hover": 3.7, "pressed": 2.7, "disabled": 3, "restore": 3, "cancelled": 4.3},
    "aero": {"rest": 11, "hover": 8, "pressed": 9, "disabled": 26, "restore": 18},
}


def build_caption_themes(tmp_path_factory):
    themes = {look: build_theme(tmp_path_factory.mktemp(look), look) for look in CLASSIC}
    luna = tmp_path_factory.mktemp("luna")
    dpi = round(96 * CAPTION_REFERENCES["luna"][1])
    subprocess.run(
        [sys.executable, str(REPO / "luna/aurorae/make_luna_aurorae.py"), "--dpi", str(dpi), "--out", str(luna)],
        check=True,
        capture_output=True,
    )
    return {
        **themes,
        "luna": luna,
        "aero": REPO / "aero/aurorae/theme",
    }


@pytest.fixture(scope="module")
def caption_themes(qt_app, tmp_path_factory):
    return build_caption_themes(tmp_path_factory)


def caption_pixels(theme, button, state, look, glass):
    """Draw a single face on the supplied VM title or glass pixels."""
    width, height = glass.size
    rgb = glass.convert("RGB").tobytes()
    image = QImage(rgb, width, height, width * 3, QImage.Format_RGB888).convertToFormat(QImage.Format_RGB32)
    painter = QPainter(image)
    try:
        suffix = "-120" if look in CLASSIC else "-large" if look == "aero" else ""
        source = theme / f"{button}{suffix}.svg"
        bounds = QRectF(0, 0, width, height)
        if look in CLASSIC:
            # The classic SVG cell carries an extra row above and below the
            # actual face, and Close starts after its two-unit space.
            gap = 3 if button == "close" else 0
            bounds = QRectF(-gap, -1, width + gap, height + 2)
        if look == "aero" and state == "restore":
            # A maximized native Aero caption clips the top physical row.
            bounds = QRectF(0, -1, width, height + 1)
        renderer = QSvgRenderer(str(source))
        assert renderer.elementExists(ELEMENTS[state])
        renderer.render(painter, ELEMENTS[state], bounds)
    finally:
        painter.end()
    rendered = qimage_to_pil(image)
    return rgb565(rendered) if look in ("2000", "2001") else rendered


def disabled_close_matte(matte):
    top = 30 * DISABLED_CLOSE_MATTES.index(matte)
    with Image.open(REFERENCES / "themes/win7/caption/disabled-close-mattes.png") as capture:
        return tuple(capture.crop((x, top, x + 75, top + 30)).convert("RGB") for x in (0, 75))


def face_region(sheet, look, state, index):
    widths, height = (
        ((45, 40, 75), 30) if look == "aero" else (((27, 27, 27), 27) if look == "luna" else ((20, 20, 20), 18))
    )
    left = 1 + sum(widths[:index])
    top = height * STATES.index(state)
    bottom = top + height - (look == "aero" and state == "restore")
    return sheet.crop((left, top, left + widths[index], bottom)), sheet.crop((0, top, 1, bottom))


def visible_pixels(look, state, size):
    width, height = size
    pixels = np.ones((height, width), dtype=bool)
    if look != "aero" and state in ("hover", "pressed"):
        # Presses on these guests use a software cursor in the lower-right.
        pixels[-6:, -6:] = False
    return pixels


def state_buttons(state):
    if state == "disabled":
        return (1, 2)
    if state == "restore":
        return (1,)
    return (0, 1, 2)


def caption_reference(look):
    path, _ = CAPTION_REFERENCES[look]
    with Image.open(path) as sheet:
        return sheet.convert("RGB")


@pytest.mark.parametrize("look", LOOKS)
@pytest.mark.parametrize(
    ("state", "index"), [(state, index) for state in STATES for index in state_buttons(state)]
)
def test_caption_svg_matches_windows_reference(caption_themes, exact_original, look, state, index):
    sheet = caption_reference(look)
    button = "restore" if state == "restore" else BUTTONS[index]
    expected, glass = face_region(sheet, look, state, index)
    actual = caption_pixels(caption_themes[look], button, state, look, glass.resize(expected.size))
    mask = visible_pixels(look, state, expected.size)
    exact_original(expected, actual, mask)
    difference = np.abs(np.asarray(actual, dtype=int) - np.asarray(expected, dtype=int))
    if look in CLASSIC:
        assert not difference[mask].any(), (look, state, button, difference[mask].mean())
        return
    limits = RGB_LIMITS[look]
    limit = limits.get(state, limits["rest"])
    if (look, state, button) == ("aero", "disabled", "maximize"):
        limit = 3.5
    assert difference[mask].mean() < limit, (look, state, button, difference[mask].mean())


@pytest.mark.parametrize("matte", DISABLED_CLOSE_MATTES)
def test_disabled_close_svg_stays_within_windows_rgb_budget_on_native_glass(caption_themes, matte):
    glass, expected = disabled_close_matte(matte)
    actual = caption_pixels(caption_themes["aero"], "close", "disabled", "aero", glass)
    difference = np.abs(np.asarray(actual, dtype=np.int16) - np.asarray(expected, dtype=np.int16))
    assert difference.mean() < 3.25


@pytest.mark.parametrize("look", LOOKS)
@pytest.mark.parametrize("index", range(len(BUTTONS)), ids=BUTTONS)
def test_caption_feedback_changes_at_the_same_pointer_events(caption_themes, look, index):
    sheet = caption_reference(look)
    changes = []
    for state in ("rest", "hover", "pressed", "cancelled"):
        expected, glass = face_region(sheet, look, state, index)
        actual = caption_pixels(caption_themes[look], BUTTONS[index], state, look, glass.resize(expected.size))
        mask = visible_pixels(look, "hover", expected.size)
        changes.append([np.asarray(image, dtype=int)[mask] for image in (expected, actual)])
    rest, hover, pressed, cancelled = np.asarray(changes)
    hover_delta = np.abs(hover - rest).mean(axis=(1, 2))
    press_delta = np.abs(pressed - hover).mean(axis=(1, 2))
    if look in CLASSIC:
        assert np.all(hover_delta < 1)
    else:
        assert np.all(hover_delta > 3)
    assert np.all(press_delta > 4)
    assert np.all(np.abs(cancelled - rest).mean(axis=(1, 2)) < 1)
