"""Compare caption button artwork with native guest captures in each interaction state."""

import numpy as np
import pytest
from aurorae_model import build_theme
from conftest import REPO
from PIL import Image
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from reference import REFERENCES, qimage_to_pil, theme_references

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
    metadata["look"]: folder / "caption-states.png" for folder, metadata in theme_references(REFERENCES)
}
LOOKS = tuple(CAPTION_REFERENCES)
CLASSIC = ("1995", "1998", "2000", "2001")
DISABLED_CLOSE_MATTES = ("dark", "light", "blue")
# Upper bounds from the native-size comparisons below. Strict mode uses
# zero RGB differences for each button and reports the pixel count.
RGB_LIMITS = {
    "classic": {"rest": 52, "hover": 50, "pressed": 36, "disabled": 41, "restore": 81},
    "luna": {"rest": 44, "hover": 40, "pressed": 37, "disabled": 25, "restore": 44},
    "aero": {"rest": 11, "hover": 19, "pressed": 24, "disabled": 26, "restore": 18},
}


def build_caption_themes(tmp_path_factory):
    themes = {look: build_theme(tmp_path_factory.mktemp(look), look) for look in CLASSIC}
    return {
        **themes,
        "luna": REPO / "luna/aurorae/theme",
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
        source = theme / f"{button}{'-large' if look == 'aero' else ''}.svg"
        bounds = QRectF(0, 0, width, height)
        if look in CLASSIC:
            # The classic SVG cell carries an extra row above and below the
            # actual face, and Close starts after its two-unit space.
            sx, sy = width / 16, height / 14
            gap = 2 if button == "close" else 0
            bounds = QRectF(-gap * sx, -sy, (16 + gap) * sx, 16 * sy)
        if look == "aero" and state == "restore":
            # A maximized native Aero caption clips the top physical row.
            bounds = QRectF(0, -1, width, height + 1)
        renderer = QSvgRenderer(str(source))
        assert renderer.elementExists(ELEMENTS[state])
        renderer.render(painter, ELEMENTS[state], bounds)
    finally:
        painter.end()
    return qimage_to_pil(image)


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
    with Image.open(CAPTION_REFERENCES[look]) as sheet:
        return sheet.convert("RGB")


@pytest.mark.parametrize("look", LOOKS)
@pytest.mark.parametrize(
    ("state", "index"), [(state, index) for state in STATES[:-1] for index in state_buttons(state)]
)
def test_caption_svg_stays_within_windows_rgb_budget(caption_themes, exact_original, look, state, index):
    sheet = caption_reference(look)
    button = "restore" if state == "restore" else BUTTONS[index]
    expected, glass = face_region(sheet, look, state, index)
    actual = caption_pixels(caption_themes[look], button, state, look, glass.resize(expected.size))
    mask = visible_pixels(look, state, expected.size)
    exact_original(expected, actual, mask)
    difference = np.abs(np.asarray(actual, dtype=int) - np.asarray(expected, dtype=int))
    limits = RGB_LIMITS["classic" if look in CLASSIC else look]
    assert difference[mask].mean() < limits[state], (look, state, button, difference[mask].mean())


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
