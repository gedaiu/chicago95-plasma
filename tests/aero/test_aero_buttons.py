"""The vector caption button faces against the aero.msstyles states they were fitted to."""

import importlib.util

import pytest
from aero_sprites import requires_sprites
from conftest import REPO
from fit_aero_stops import FACES, STATES, glyph_image, state_image
from PIL import Image
from reference import screenshot
from test_caption_states_reference import caption_pixels, caption_reference, face_region

spec = importlib.util.spec_from_file_location("make_aero_aurorae", REPO / "aero/aurorae/make_aero_aurorae.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
GLASS = (82, 139, 185, 255)


def rendered(svg, size):
    from PySide6.QtCore import QByteArray, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    image = QImage(*size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    QSvgRenderer(QByteArray(svg.encode())).render(painter)
    painter.end()
    rgba = image.convertToFormat(QImage.Format_RGBA8888)
    return Image.frombuffer("RGBA", size, bytes(rgba.constBits()), "raw", "RGBA", rgba.bytesPerLine(), 1)


def over_glass(image):
    base = Image.new("RGBA", image.size, GLASS)
    base.alpha_composite(image)
    return base.convert("RGB")


@requires_sprites
@pytest.mark.parametrize("state", range(len(STATES)))
@pytest.mark.parametrize("window", ["active", "inactive"])
@pytest.mark.parametrize("face", sorted(FACES))
def test_vector_face_matches_its_sprite_over_glass_within_six_levels(qt_app, face, window, state, exact_original):
    sprite = state_image(FACES[face][window == "inactive"], state)
    fitted = generator.stops.FACES[face][window][STATES[state]]
    ours = over_glass(rendered(generator.face_svg(fitted), sprite.size))
    theirs = over_glass(sprite)
    exact_original(theirs, ours)
    differences = [
        abs(a - b)
        for p, q in zip(ours.get_flattened_data(), theirs.get_flattened_data(), strict=True)
        for a, b in zip(p, q, strict=True)
    ]

    assert sum(differences) / len(differences) < 6


@requires_sprites
@pytest.mark.parametrize("state", range(len(STATES)))
@pytest.mark.parametrize("glyph", ["close", "minimize", "maximize", "restore"])
def test_vector_glyph_matches_its_96_dpi_sprite_over_glass_within_twelve_levels(qt_app, glyph, state, exact_original):
    sprite = glyph_image(glyph, state)
    ours = over_glass(rendered(generator.glyph_svg(glyph, generator.stops.GLYPHS[glyph][STATES[state]]), sprite.size))
    theirs = over_glass(sprite)
    exact_original(theirs, ours)
    differences = [
        abs(a - b)
        for p, q in zip(ours.get_flattened_data(), theirs.get_flattened_data(), strict=True)
        for a, b in zip(p, q, strict=True)
    ]

    assert sum(differences) / len(differences) < 12


@pytest.mark.parametrize(
    ("kind", "left", "width"), [("minimize", 0, 45), ("maximize", 45, 40), ("close", 85, 75), ("restore", 0, 40)]
)
def test_large_caption_glyph_matches_144_dpi_guest(qt_app, kind, left, width):
    import numpy as np

    native = Image.open(REPO / "tests/references/win7-sp1-144dpi-caption.png").convert("RGB")
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    from reference import qimage_to_pil

    asset = REPO / f"aero/aurorae/theme/{kind}-large.svg"
    renderer = QSvgRenderer(str(asset))
    assert renderer.elementExists("active-center")
    pixels = QImage(width, 30, QImage.Format_RGB32)
    pixels.fill(Qt.black)
    painter = QPainter(pixels)
    renderer.render(painter, "active-center", QRectF(0, 0, width, 30))
    painter.end()
    actual = qimage_to_pil(pixels)
    expected = native.crop((left, 0, left + width, 30))

    if kind == "restore":
        expected = Image.open(REPO / "tests/references/win7-sp1-144dpi-restore.png").convert("RGB")
        # The maximized caption clips the topmost row at the screen edge.
        actual = actual.crop((0, 1, width, 30))
        observed, guest = (np.asarray(im, dtype=int)[4:25, 7:33] for im in (actual, expected))
        bright, native_bright = [(im.min(2) > 198) & (np.ptp(im, axis=2) < 12) for im in (observed, guest)]
        assert np.array_equal(bright, native_bright)
        assert np.array_equal(observed[native_bright], guest[native_bright])
        return

    # Isolate the bright glyph body from the bevel and translucent glass.
    def body(im):
        return np.asarray(im)[4:25, 6:-6].min(axis=2) > 198

    a, b = body(actual), body(expected)
    assert (a & b).sum() / (a | b).sum() > 0.82


@pytest.mark.parametrize(
    ("kind", "width", "left", "dpi96_limit", "dpi144_limit"),
    [("minimize", 30, 0, 14, 17), ("maximize", 27, 45, 19, 18), ("close", 50, 85, 14, 17), ("restore", 27, 0, 10, 5)],
)
@pytest.mark.parametrize("large", [False, True], ids=["96dpi", "144dpi"])
def test_complete_caption_face_against_guest(
    qt_app, exact_original, kind, width, left, dpi96_limit, dpi144_limit, large
):
    import numpy as np
    from test_aero_imported_art import render

    theme = REPO / "aero/aurorae/theme"
    restore = kind == "restore"
    if large:
        width = 40 if kind in ("maximize", "restore") else round(width * 1.5)
        height, matte, limit = 30, (62, 106, 148), dpi144_limit
        name = "144dpi-restore" if restore else "144dpi-caption"
        top = 0
    else:
        height, matte, limit = 20, (109, 146, 181), dpi96_limit
        name = f"caption-{kind}-motion"
        left, top = 0, 0 if restore else 2
    if large and restore:
        expected, glass = face_region(caption_reference("aero"), "aero", "restore", 1)
        actual = caption_pixels(theme, kind, "restore", "aero", glass.resize(expected.size))
    else:
        reference = screenshot(f"win7-sp1-{name}")
        expected = reference.crop((left, top, left + width, top + height - restore))
        asset = theme / f"{kind}{'-large' if large else ''}.svg"
        button = render(asset.read_bytes(), (width, height), "active-center")
        glass = Image.new("RGBA", button.size, matte)
        glass.alpha_composite(button)
        actual = glass.convert("RGB").crop((0, int(restore), width, height))
    exact_original(expected, actual)
    difference = np.abs(np.asarray(actual, dtype=int) - np.asarray(expected, dtype=int))
    assert difference.mean() < limit
    if kind == "maximize" and not large:
        assert difference[:17, 0].mean() < 16


@pytest.mark.parametrize("band", range(3), ids=("dark", "light", "blue"))
def test_maximize_sheen_matches_native_glass(qt_app, band):
    import numpy as np

    y = 30 * band
    with Image.open(REPO / "tests/references/win7-sp1-144dpi-caption-mattes.png") as reference:
        glass = reference.crop((1, y, 2, y + 30)).convert("RGB")
        # The sheet begins with the backdrop and glass columns, then the 45px Minimize cell.
        expected = reference.crop((47, y, 87, y + 30)).convert("RGB")
    actual = caption_pixels(REPO / "aero/aurorae/theme", "maximize", "rest", "aero", glass.resize(expected.size))
    difference = np.abs(np.asarray(actual, dtype=int) - np.asarray(expected, dtype=int))
    assert difference.mean() < 2, difference.mean()


@pytest.mark.parametrize(
    ("kind", "width", "ink_pixels"), [("minimize", 30, 56), ("maximize", 27, 108), ("restore", 27, 126)]
)
@pytest.mark.parametrize(("state", "frame"), [("active", 0), ("hover", 55)])
def test_96dpi_caption_glyph_matches_native_ink(qt_app, kind, width, ink_pixels, state, frame):
    import numpy as np
    from test_aero_imported_art import render

    restore = kind == "restore"
    reference = screenshot(f"win7-sp1-caption-{kind}-motion")
    x, y = frame % 10 * width, frame // 10 * 25 + (0 if restore else 2)
    native = np.asarray(reference.crop((x + 5, y + 2, x + width - 5, y + 16)))
    asset = REPO / f"aero/aurorae/theme/{kind}.svg"
    layer = np.asarray(render(asset.read_bytes(), (width, 20), state + "-center"))
    # The restored cluster overlaps adjacent cells by one pixel, so its
    # native filmstrip is one pixel ahead of the unjoined SVG's glyph.
    shift = 0 if restore else 1
    glyph = layer[2 + int(restore) : 16 + int(restore), 5 + shift : width - 5 + shift]

    def ink(rgb):
        return np.all(rgb == (83, 86, 102), axis=2) | ((rgb.min(axis=2) > 210) & (np.ptp(rgb, axis=2) < 4))

    mask = ink(native)
    assert mask.sum() == ink_pixels
    assert np.array_equal(mask, ink(glyph[..., :3]) & (glyph[..., 3] == 255))
    assert np.array_equal(native[mask], glyph[mask, :3])


@pytest.mark.parametrize(
    ("kind", "left", "width", "limit", "joined_edges"),
    [
        ("minimize", 0, 45, 4, [-1]),
        ("maximize", 45, 40, 6, [0, -1]),
        ("close", 85, 75, 6, []),
    ],
)
@pytest.mark.parametrize("top", [0, 30, 60], ids=["dark", "light", "blue"])
def test_144dpi_resting_caption_over_native_glass(qt_app, exact_original, kind, left, width, limit, joined_edges, top):
    import numpy as np
    from test_aero_imported_art import render

    capture = Image.open(REPO / "tests/references/win7-sp1-144dpi-caption-mattes.png")
    asset = REPO / f"aero/aurorae/theme/{kind}-large.svg"
    button = render(asset.read_bytes(), (width, 30), "active-center")
    glass = capture.crop((1, top, 2, top + 30)).resize(button.size, Image.Resampling.NEAREST).convert("RGBA")
    glass.alpha_composite(button)
    expected = capture.crop((2 + left, top, 2 + left + width, top + 30))
    actual = glass.convert("RGB")
    exact_original(expected, actual)
    native = np.asarray(expected, dtype=int)
    difference = np.abs(np.asarray(actual, dtype=int) - native)
    assert difference.mean() < limit
    if joined_edges:
        assert np.all(difference[:, joined_edges].mean(axis=(0, 2)) < 4.5)
    if kind == "minimize":
        # The outer highlight, dark divider and inner highlight are separate
        # optical bands. Measure their straight portions and the opposite join.
        assert np.all(difference[1:25, [0, 1, 2, -2]].mean(axis=(0, 2)) < 7)
        assert difference[13:15, 5:15].mean() < 2
    if kind == "maximize":
        # Compare the gloss transition in the face area clear of the glyph.
        assert difference[13:15, 3:9].mean() < 2.5
        # The bright left and right stems are four whole pixels on the
        # 40-pixel cell. Compare their exact RGB without the glass.
        assert not np.any(difference[11:17, [11, 12, 13, 14, 25, 26, 27, 28]])
    if top == 0 and kind in ("minimize", "maximize"):
        # On dark glass the opaque glyph is the only bright neutral paint inside the face.
        interior = native[5:23, 7:-7]
        ink = (interior.min(axis=2) > 198) & (np.ptp(interior, axis=2) < 12)
        assert ink.sum() == {"minimize": 64, "maximize": 172}[kind]
        assert not np.any(difference[5:23, 7:-7][ink])
    if kind == "close":
        # The inset highlights and red bevel are visible above the rounded corners.
        assert not np.any(difference[0, 5:-5])
        assert np.all(difference[:25, [1, -3, -2]].mean(axis=(0, 2)) < 7)
        assert difference[-1, 6:-7].mean() < 5
        assert difference[[5, 22], 27:47].mean() < 4


@pytest.mark.parametrize("large", [False, True], ids=["96dpi", "144dpi"])
def test_close_bevel_retains_glass_transparency_in_each_state(qt_app, large):
    from test_aero_imported_art import render

    asset = REPO / "aero/aurorae/theme" / ("close-large.svg" if large else "close.svg")
    width, height = (75, 30) if large else (50, 20)
    for state in generator.AURORAE_STATES:
        button = render(asset.read_bytes(), (width, height), state + "-center")
        left = button.getpixel((0, height - 1))
        lower_rim = button.getpixel((width // 2, height - 1))
        if large and state == "deactivated":
            assert left == lower_rim
        else:
            assert left[3] == 0
        top = button.getpixel((width // 2, 0))
        assert min(top[:3]) >= 248
        if state in ("active", "hover", "pressed"):
            assert top == (252, 252, 252, 255)
        red, green, blue, alpha = lower_rim
        assert max(red, green, blue) - min(red, green, blue) < 5
        if large and state == "active":
            assert 193 <= alpha <= 199
        else:
            assert 80 <= alpha <= 180


@pytest.mark.parametrize(("kind", "width", "radius"), [("minimize", 30, 2), ("close", 50, 2)])
def test_caption_lower_corner_keeps_its_circular_rim_when_enlarged(qt_app, kind, width, radius):
    import numpy as np
    from test_aero_imported_art import render

    asset = REPO / f"aero/aurorae/theme/{kind}.svg"
    scale = 16
    alpha = np.asarray(render(asset.read_bytes(), (width * scale, 20 * scale), "active-center"))[:, :, 3]
    outer_radius = radius + 0.5
    side = int(scale * outer_radius)
    # Sample the outer edge around the quarter circle and leave one sample
    # either side of the boundary for the renderer's antialiasing.
    y, x = np.indices((side, side))
    distance = np.hypot((x + 0.5) / scale - outer_radius, (y + 0.5) / scale)
    corner = alpha[-side:, :side]
    assert np.all(corner[distance < outer_radius - 1 / scale] > 40)
    rim = (distance > outer_radius - 0.6) & (distance < outer_radius - 0.125)
    assert np.all((160 <= corner[rim]) & (corner[rim] <= 175))
    assert np.all(corner[distance > outer_radius + 1 / scale] <= 4)


@pytest.mark.parametrize("state_index", range(8))
def test_optional_commands_have_distinct_visible_symbols_in_each_state(qt_app, state_index):
    import xml.etree.ElementTree as ET

    from PIL import ImageChops

    masks = set()
    theme = REPO / "aero/aurorae/theme"
    for name in ("help", "shade", "keepabove", "keepbelow", "alldesktops"):
        tree = ET.parse(theme / f"{name}.svg").getroot()
        size = int(tree.get("width")), int(tree.get("height"))
        group = tree.findall("{*}g")[state_index]
        x = state_index * (generator.palette.BUTTON_WIDTHS["maximize"] + generator.GAP)
        area = (x, 0, x + generator.palette.BUTTON_WIDTHS["maximize"], size[1])
        face = over_glass(rendered(ET.tostring(tree, encoding="unicode"), size)).crop(area)
        group.remove(group[-1])
        background = over_glass(rendered(ET.tostring(tree, encoding="unicode"), size)).crop(area)
        mask = ImageChops.difference(face, background).convert("L").point(lambda value: 255 if value > 2 else 0)
        assert mask.histogram()[255] >= 12, name
        masks.add(mask.tobytes())
    assert len(masks) == 5
