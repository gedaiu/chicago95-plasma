"""Native GTK3/GTK4 pixel comparisons, and matching Qt indicator geometry/marks.

The radio's antialiased perimeter differs between Cairo and GTK4's renderer; its
interior pixels, diameter and colour roles must still agree. Checkbox pixels match exactly.
"""

import json
import shutil
import subprocess
import sys

import pytest
from PIL import Image, ImageChops, ImageFilter
from PySide6.QtCore import QRect
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QStyle, QStyleOptionButton
from reference import qimage_to_pil

STATES = (
    "normal",
    "checked",
    "mixed",
    "disabled",
    "hovered",
    "pressed",
    "checked-hovered",
    "checked-pressed",
    "focused",
)
CASES = [(kind, state) for kind in ("checkbox", "radio") for state in STATES if (kind, state) != ("radio", "mixed")]
FACE = "#ece9d8"


@pytest.fixture(scope="module")
def gtk_images(tmp_path_factory, qt_app):
    if not shutil.which("kwin_wayland") or not shutil.which("dbus-run-session"):
        pytest.skip("native GTK visual checks need isolated KWin and D-Bus")
    for version in ("3.0", "4.0"):
        probe = subprocess.run(
            [sys.executable, "-c", f'import gi; gi.require_version("Gtk", "{version}")'],
            capture_output=True,
            check=False,
        )
        if probe.returncode:
            pytest.skip(f"GTK {version} Python bindings unavailable")
    from showcase import gtk_controls

    folder = tmp_path_factory.mktemp("gtk-visual-consistency")
    gtk_controls("luna", folder, audit=True)
    return load_images(folder, FACE)


def load_images(folder, face):
    images = {}
    for version in ("3.0", "4.0"):
        output = folder / f"gtk-{version}"
        for _, label, filename in json.loads((output / "manifest.json").read_text()):
            image = Image.open(output / filename).convert("RGBA")
            paper = Image.new("RGBA", image.size, face)
            paper.alpha_composite(image)
            image = paper.convert("RGB")
            box = ImageChops.difference(image, Image.new("RGB", image.size, face)).getbbox()
            assert box is not None, f"{version}: {label} rendered blank"
            images[version, *label.split()] = image.crop(box)
            if label == "tabfont normal":
                images[version, "tabfont", "normal"].info["font"] = json.loads((output / "font.json").read_text())
    return images


@pytest.mark.parametrize("kind,state", CASES)
def test_gtk_versions_match_same_indicator_state(gtk_images, kind, state, tmp_path):
    a, b = (gtk_images[version, kind, state] for version in ("3.0", "4.0"))
    assert a.size == b.size == (13, 13)
    # Square controls have no renderer-dependent curved perimeter to mask.
    region = (0, 0, 13, 13) if kind == "checkbox" else (3, 3, 10, 10)
    diff = ImageChops.difference(a.crop(region), b.crop(region))
    # Curved hover glows round colour channels differently by at most 2/255.
    tolerance = 0 if kind == "checkbox" else 2
    if max(high for _low, high in diff.getextrema()) > tolerance:
        a.save(tmp_path / "gtk3.png")
        b.save(tmp_path / "gtk4.png")
        ImageChops.difference(a, b).save(tmp_path / "difference.png")
        pytest.fail(f"{kind} {state}: GTK renderers disagree; see {tmp_path}")


@pytest.mark.parametrize("state", STATES)
def test_qt_and_gtk_checkboxes_share_mark_pixels(qt_app, gtk_images, state):
    import chicago95luna

    style = chicago95luna.LunaStyle()
    option = QStyleOptionButton()
    option.rect = QRect(0, 0, 13, 13)
    option.palette = chicago95luna.luna_palette()
    option.state = QStyle.State_Enabled
    if state.startswith("checked") or state == "disabled":
        option.state |= QStyle.State_On
    if state == "mixed":
        option.state |= QStyle.State_NoChange
    if state == "disabled":
        option.state &= ~QStyle.State_Enabled
    if state.endswith("hovered"):
        option.state |= QStyle.State_MouseOver
    if state.endswith("pressed"):
        option.state |= QStyle.State_Sunken
    if state == "focused":
        option.state |= QStyle.State_HasFocus
    image = QImage(13, 13, QImage.Format_RGB32)
    image.fill(option.palette.window().color())
    painter = QPainter(image)
    style.drawPrimitive(QStyle.PE_IndicatorCheckBox, option, painter)
    painter.end()
    ours = qimage_to_pil(image)
    mark = (202, 200, 187) if state == "disabled" else (33, 161, 33)

    def mark_pixels(picture):
        return {(x, y) for y in range(3, 10) for x in range(3, 10) if picture.getpixel((x, y)) == mark}

    for version in ("3.0", "4.0"):
        assert mark_pixels(ours) == mark_pixels(gtk_images[version, "checkbox", state])
    if state.startswith("checked") or state in ("mixed", "disabled"):
        assert mark_pixels(ours), "a selected/mixed checkbox must contain a visible mark"


@pytest.mark.parametrize("version", ("3.0", "4.0"))
def test_indicator_states_change_pixels(gtk_images, version):
    for kind in ("checkbox", "radio"):
        normal = gtk_images[version, kind, "normal"].tobytes()
        for state in ("checked", "hovered", "pressed", "disabled"):
            assert gtk_images[version, kind, state].tobytes() != normal, f"{kind}: {state} looks normal"


@pytest.fixture(scope="module")
def classic_gtk_images(tmp_path_factory, gtk_images):
    # Reuse the runtime availability checks in the Luna fixture.
    from showcase import gtk_controls

    folder = tmp_path_factory.mktemp("classic-gtk-tabs")
    gtk_controls("1995", folder, audit=True)
    return load_images(folder, "#c0c0c0")


@pytest.mark.parametrize("look", ("classic", "luna"))
@pytest.mark.parametrize("position", ("top", "bottom", "left", "right"))
@pytest.mark.parametrize("state", ("first", "second", "disabled"))
def test_gtk_tab_chrome_matches(gtk_images, classic_gtk_images, look, position, state, tmp_path):
    images = gtk_images if look == "luna" else classic_gtk_images
    a, b = (images[version, "tabs", f"{state}-{position}"] for version in ("3.0", "4.0"))
    a.save(tmp_path / "gtk3.png")
    b.save(tmp_path / "gtk4.png")
    assert a.size == b.size, f"tab geometry differs; see {tmp_path}"
    diff = ImageChops.difference(a, b)
    diff.save(tmp_path / "difference.png")
    if look == "luna":
        assert max(high for _, high in diff.getextrema()) <= 2, f"tab chrome differs; see {tmp_path}"
    else:
        # Allow bitmap-slice corner antialiasing, never a border through the selected tab.
        # A shifted border or changed tab size must fail.
        changed = sum(max(pixel) > 2 for pixel in diff.get_flattened_data())
        assert changed <= a.width * a.height * 0.002, f"tab chrome differs; see {tmp_path}"
        low = a.filter(ImageFilter.MinFilter(3))
        high = a.filter(ImageFilter.MaxFilter(3))
        assert ImageChops.subtract(low, b).getbbox() is None
        assert ImageChops.subtract(b, high).getbbox() is None, "selected tab has a closing page border"



@pytest.mark.parametrize("look", ("classic", "luna"))
def test_selecting_another_tab_changes_chrome(gtk_images, classic_gtk_images, look):
    images = gtk_images if look == "luna" else classic_gtk_images
    for version in ("3.0", "4.0"):
        for position in ("top", "bottom", "left", "right"):
            first = images[version, "tabs", f"first-{position}"]
            second = images[version, "tabs", f"second-{position}"]
            assert first.tobytes() != second.tobytes()


@pytest.mark.parametrize("look", ("classic", "luna"))
@pytest.mark.parametrize("orientation", ("horizontal", "vertical"))
@pytest.mark.parametrize("state", ("empty", "low", "half", "full", "disabled", "inverted", "rtl"))
def test_gtk_progress_matches(gtk_images, classic_gtk_images, look, orientation, state, tmp_path):
    images = gtk_images if look == "luna" else classic_gtk_images
    a, b = (images[version, "progress", f"{state}-{orientation}"] for version in ("3.0", "4.0"))
    a.save(tmp_path / "gtk3.png")
    b.save(tmp_path / "gtk4.png")
    assert a.size == b.size
    diff = ImageChops.difference(a, b)
    diff.save(tmp_path / "difference.png")
    assert max(high for _, high in diff.getextrema()) <= 2, f"progress rendering differs; see {tmp_path}"


@pytest.mark.parametrize("look", ("classic", "luna"))
def test_progress_fill_is_visible_and_increases(gtk_images, classic_gtk_images, look):
    images = gtk_images if look == "luna" else classic_gtk_images
    colour = (57, 230, 58) if look == "luna" else (0, 0, 128)
    for version in ("3.0", "4.0"):
        for orientation in ("horizontal", "vertical"):
            counts = [
                sum(
                    pixel == colour
                    for pixel in images[version, "progress", f"{state}-{orientation}"].get_flattened_data()
                )
                for state in ("empty", "low", "half", "full")
            ]
            assert counts[0] == 0
            assert counts[0] < counts[1] < counts[2] < counts[3]


@pytest.mark.parametrize("look", ("classic", "luna"))
@pytest.mark.parametrize("orientation", ("horizontal", "vertical"))
@pytest.mark.parametrize("state", ("normal", "start", "end", "disabled", "hovered", "pressed"))
def test_gtk_scrollbar_artwork_matches(gtk_images, classic_gtk_images, look, orientation, state, tmp_path):
    images = gtk_images if look == "luna" else classic_gtk_images
    a, b = (images[version, "scrollbar", f"{state}-{orientation}"] for version in ("3.0", "4.0"))
    a.save(tmp_path / "gtk3.png")
    b.save(tmp_path / "gtk4.png")
    width = 17 if look == "luna" else 16
    assert a.size == b.size == ((220, width) if orientation == "horizontal" else (width, 180))
    # GTK4 has no real steppers and cannot disable an individual end cap at range limits.
    # Compare the trough/thumb at limits; all other states also compare both arrow images.
    if state in ("start", "end"):
        region = (width, 0, a.width - width, a.height) if orientation == "horizontal" else (
            0, width, a.width, a.height - width
        )
        a, b = a.crop(region), b.crop(region)
    diff = ImageChops.difference(a, b)
    diff.save(tmp_path / "difference.png")
    if look == "classic":
        # Cairo's bitmap border slicing differs at a single thumb corner.
        assert sum(max(pixel) > 2 for pixel in diff.get_flattened_data()) <= 2, str(tmp_path)
    else:
        assert max(high for _, high in diff.getextrema()) <= 2, str(tmp_path)


@pytest.mark.parametrize("look", ("classic", "luna"))
@pytest.mark.parametrize("version", ("3.0", "4.0"))
def test_scrollbar_arrows_are_visible_at_both_ends(gtk_images, classic_gtk_images, look, version):
    images = gtk_images if look == "luna" else classic_gtk_images
    ink = (36, 92, 171) if look == "luna" else (0, 0, 0)
    size = 17 if look == "luna" else 16
    for orientation in ("horizontal", "vertical"):
        bar = images[version, "scrollbar", f"normal-{orientation}"]
        for x, y in ((0, 0), (bar.width - size, bar.height - size)):
            glyph = bar.crop((x + 4, y + 4, x + size - 4, y + size - 4))
            assert sum(pixel == ink for pixel in glyph.get_flattened_data()) >= 4


@pytest.mark.parametrize("version", ("3.0", "4.0"))
def test_luna_thumb_hover_and_press_change_pixels(gtk_images, version):
    for orientation in ("horizontal", "vertical"):
        normal = gtk_images[version, "scrollbar", f"normal-{orientation}"].tobytes()
        hovered = gtk_images[version, "scrollbar", f"hovered-{orientation}"].tobytes()
        pressed = gtk_images[version, "scrollbar", f"pressed-{orientation}"].tobytes()
        assert len({normal, hovered, pressed}) == 3


@pytest.mark.parametrize("look", ("classic", "luna"))
@pytest.mark.parametrize("state", ("normal", "disabled", "unlabelled"))
def test_gtk_group_box_border_and_content_alignment(gtk_images, classic_gtk_images, look, state, tmp_path):
    images = gtk_images if look == "luna" else classic_gtk_images
    a, b = (images[version, "groupbox", state] for version in ("3.0", "4.0"))
    a.save(tmp_path / "gtk3.png")
    b.save(tmp_path / "gtk4.png")
    assert a.size == b.size == (240, 80)
    diff = ImageChops.difference(a, b)
    diff.save(tmp_path / "difference.png")
    assert max(high for _, high in diff.getextrema()) <= 2, str(tmp_path)
    # The child marker must remain 8x8; border parity must not hide missing content.
    assert sum(pixel == (0, 0, 0) for pixel in a.get_flattened_data()) == 64


@pytest.mark.parametrize("look", ("classic", "luna"))
def test_gtk_tab_fonts_match_qt(qt_app, gtk_images, classic_gtk_images, look):
    from PySide6.QtGui import QFontInfo
    from showcase import themed

    images = gtk_images if look == "luna" else classic_gtk_images
    with themed(qt_app, "1995" if look == "classic" else "luna"):
        font = qt_app.font()
        resolved = QFontInfo(font)
        for version in ("3.0", "4.0"):
            actual = images[version, "tabfont", "normal"].info["font"]
            assert actual["requested_family"] == resolved.family()
            assert actual["resolved_family"] == resolved.family()
            pixels = actual["size"] if actual["absolute"] else actual["size"] * 96 / 72
            assert pixels == font.pixelSize() == 11


@pytest.mark.parametrize("look", ("classic", "luna"))
@pytest.mark.parametrize("kind", ("dropdown", "spinbox"))
@pytest.mark.parametrize("state", ("normal", "disabled", "hovered", "pressed"))
def test_gtk_dropdown_and_spinbox_match(gtk_images, classic_gtk_images, look, kind, state, tmp_path):
    from PIL import ImageDraw

    images = gtk_images if look == "luna" else classic_gtk_images
    a, b = (images[version, kind, state] for version in ("3.0", "4.0"))
    a.save(tmp_path / "gtk3.png")
    b.save(tmp_path / "gtk4.png")
    assert a.size == b.size == (160, 21 if look == "luna" else 20)
    diff = ImageChops.difference(a, b)
    if look == "luna":
        # Pango antialiases glyphs differently. Verify their bounds, then compare all surrounding pixels exactly.
        field_colour = (236, 233, 216) if state == "disabled" else (255, 255, 255)
        bounds = []
        for im in (a, b):
            field = im.crop((2, 2, 120, im.height - 2))
            box = ImageChops.difference(field, Image.new("RGB", field.size, field_colour)).getbbox()
            assert box is not None and box[2] < 70 and box[3] - box[1] <= 12
            bounds.append(box)
            assert im.getpixel((100, im.height // 2)) == field_colour
        assert all(abs(x - y) <= 1 for x, y in zip(*bounds, strict=True))
        left = min(box[0] for box in bounds) + 2
        top = min(box[1] for box in bounds) + 2
        right = max(box[2] for box in bounds) + 2
        bottom = max(box[3] for box in bounds) + 2
        ImageDraw.Draw(diff).rectangle((left, top, right - 1, bottom - 1), fill=(0, 0, 0))
    diff.save(tmp_path / "difference.png")
    assert max(high for _, high in diff.getextrema()) <= 2, str(tmp_path)


@pytest.mark.parametrize("look", ("classic", "luna"))
def test_input_arrow_artwork_is_visible(gtk_images, classic_gtk_images, look):
    images = gtk_images if look == "luna" else classic_gtk_images
    size = 17 if look == "luna" else 16
    ink = (36, 92, 171) if look == "luna" else (0, 0, 0)
    for version in ("3.0", "4.0"):
        for kind, count in (("dropdown", 1), ("spinbox", 2)):
            im = images[version, kind, "normal"]
            for index in range(count):
                left = im.width - 2 - (index + 1) * size
                glyph = im.crop((left + 4, 6, left + size - 4, 2 + size - 4))
                assert sum(pixel == ink for pixel in glyph.get_flattened_data()) >= 4


@pytest.mark.parametrize("version", ("3.0", "4.0"))
@pytest.mark.parametrize("orientation", ("horizontal", "vertical"))
@pytest.mark.parametrize("state", ("normal", "start", "end", "hovered", "pressed", "disabled"))
def test_luna_scrollbar_thumb_has_four_visible_grip_ridges(gtk_images, version, orientation, state):
    image = gtk_images[version, "scrollbar", f"{state}-{orientation}"]
    dark, light = (152, 186, 233), (236, 242, 251)
    pixels = {
        (x, y): image.getpixel((x, y))
        for y in range(image.height)
        for x in range(image.width)
        if image.getpixel((x, y)) in (dark, light)
    }
    if state == "disabled":
        assert not pixels, "a disabled thumb must not show an active grip"
        return
    assert len(pixels) == 88, "four 11px dark ridges and four 11px highlights must be visible"
    left = min(x for x, _ in pixels)
    top = min(y for _, y in pixels)
    width, height = (8, 11) if orientation == "horizontal" else (11, 8)
    for y in range(height):
        for x in range(width):
            band = x if orientation == "horizontal" else y
            assert pixels[left + x, top + y] == (dark if band % 2 == 0 else light)

    # Centre the artwork within the thumb, not the entire track or one of the end buttons.
    border = (111, 141, 219) if state == "pressed" else (138, 163, 230)
    thumb = [(x, y) for y in range(image.height) for x in range(image.width) if image.getpixel((x, y)) == border]
    assert thumb
    assert abs(2 * left + width - 1 - min(x for x, _ in thumb) - max(x for x, _ in thumb)) <= 1
    assert abs(2 * top + height - 1 - min(y for _, y in thumb) - max(y for _, y in thumb)) <= 1


@pytest.mark.parametrize("orientation", ("horizontal", "vertical"))
@pytest.mark.parametrize("state", ("normal", "start", "end", "disabled", "hovered", "pressed"))
def test_luna_slider_thumb_matches_qt_and_has_a_smooth_gradient(qt_app, gtk_images, orientation, state, tmp_path):
    import chicago95luna
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QStyleOptionSlider

    horizontal = orientation == "horizontal"
    style = chicago95luna.LunaStyle()
    option = QStyleOptionSlider()
    option.rect = QRect(0, 0, 180, 21) if horizontal else QRect(0, 0, 21, 180)
    option.orientation = Qt.Horizontal if horizontal else Qt.Vertical
    option.minimum, option.maximum = 0, 100
    option.sliderPosition = {"start": 0, "end": 100}.get(state, 40)
    option.palette = chicago95luna.luna_palette()
    option.state = QStyle.State_None if state == "disabled" else QStyle.State_Enabled
    if horizontal:
        option.state |= QStyle.State_Horizontal
    if state in ("hovered", "pressed"):
        option.state |= QStyle.State_MouseOver if state == "hovered" else QStyle.State_Sunken
        option.activeSubControls = QStyle.SC_SliderHandle
    option.subControls = QStyle.SC_SliderGroove | QStyle.SC_SliderHandle
    image = QImage(option.rect.size(), QImage.Format_RGB32)
    image.fill(option.palette.window().color())
    painter = QPainter(image)
    style.drawComplexControl(QStyle.CC_Slider, option, painter)
    painter.end()
    handle = style.subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderHandle)
    qt = qimage_to_pil(image).crop((handle.x(), handle.y(), handle.right() + 1, handle.bottom() + 1))
    assert qt.size == ((11, 21) if horizontal else (21, 11))
    # Four flat colour bands are not a gradient, even if both GTK versions match them.
    shades = [qt.getpixel((5, i) if horizontal else (i, 5)) for i in range(3, 20)]
    assert len(set(shades)) >= 12
    luminance = [sum(pixel) for pixel in shades]
    assert luminance == sorted(luminance, reverse=state != "pressed")
    for version in ("3.0", "4.0"):
        actual = gtk_images[version, "slider", f"{state}-{orientation}"]
        border = [(x, y) for y in range(actual.height) for x in range(actual.width)
                  if actual.getpixel((x, y)) in ((181, 196, 205), (119, 136, 146))]
        assert border, "slider thumb is missing"
        xs, ys = zip(*border, strict=True)
        thumb = actual.crop((min(xs), min(ys), max(xs) + 1, max(ys) + 1))
        thumb.save(tmp_path / f"gtk-{version}.png")
        qt.save(tmp_path / "qt.png")
        assert thumb.size == qt.size
        assert thumb.tobytes() == qt.tobytes(), f"{version}: thumb differs from Qt; see {tmp_path}"


@pytest.mark.parametrize("orientation", ("horizontal", "vertical"))
@pytest.mark.parametrize("state", ("normal", "start", "end", "disabled", "hovered", "pressed"))
def test_luna_slider_gtk_geometry_and_track_match(gtk_images, orientation, state, tmp_path):
    a, b = (gtk_images[v, "slider", f"{state}-{orientation}"] for v in ("3.0", "4.0"))
    a.save(tmp_path / "gtk3.png")
    b.save(tmp_path / "gtk4.png")
    assert a.size == b.size
    assert a.tobytes() == b.tobytes(), f"slider track or position differs; see {tmp_path}"


@pytest.mark.parametrize("orientation", ("horizontal", "vertical"))
@pytest.mark.parametrize("state", ("empty", "low", "half", "full", "disabled", "inverted", "rtl"))
def test_luna_progress_qt_gtk_thickness_inset_and_fill(qt_app, gtk_images, orientation, state):
    import chicago95luna
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QProgressBar

    horizontal = orientation == "horizontal"
    style = chicago95luna.LunaStyle()
    bar = QProgressBar()
    bar.setStyle(style)
    bar.setPalette(chicago95luna.luna_palette())
    bar.setFont(chicago95luna.luna_font())
    bar.setOrientation(Qt.Horizontal if horizontal else Qt.Vertical)
    bar.setTextVisible(False)
    bar.setValue({"empty": 0, "low": 1, "full": 100}.get(state, 55))
    bar.setEnabled(state != "disabled")
    bar.setInvertedAppearance(state == "inverted")
    if state == "rtl":
        bar.setLayoutDirection(Qt.RightToLeft)
    bar.resize(260, bar.sizeHint().height()) if horizontal else bar.resize(bar.sizeHint().width(), 160)
    qt = qimage_to_pil(bar.grab().toImage())
    assert (qt.height if horizontal else qt.width) == 17
    for version in ("3.0", "4.0"):
        gtk = gtk_images[version, "progress", f"{state}-{orientation}"]
        assert gtk.size == qt.size
        for image in (qt, gtk):
            for x in range(2, image.width - 2):
                assert image.getpixel((x, 1)) == image.getpixel((x, image.height - 2)) == (255, 255, 255)
            for y in range(2, image.height - 2):
                assert image.getpixel((1, y)) == image.getpixel((image.width - 2, y)) == (255, 255, 255)
        # Ignore only the rounded frame corners, whose antialiasing differs by renderer.
        region = (2, 2, qt.width - 2, qt.height - 2)
        assert qt.crop(region).tobytes() == gtk.crop(region).tobytes(), f"{version}: fill differs from Qt"
    bar.close()


@pytest.mark.parametrize("active", (False, True))
@pytest.mark.parametrize("state", ("normal", "disabled", "hovered", "pressed", "focused"))
def test_luna_switches_match_in_both_positions_and_states(gtk_images, active, state, tmp_path):
    label = f"{'on' if active else 'off'}-{state}"
    a, b = (gtk_images[v, "switch", label] for v in ("3.0", "4.0"))
    a.save(tmp_path / "gtk3.png")
    b.save(tmp_path / "gtk4.png")
    assert a.size == b.size == (36, 19)
    assert a.tobytes() == b.tobytes(), f"switch {label} differs; see {tmp_path}"
    for version, image in (("3.0", a), ("4.0", b)):
        normal = gtk_images[version, "switch", f"{'on' if active else 'off'}-normal"]
        if state != "normal":
            assert image.tobytes() != normal.tobytes(), f"{label}: missing state feedback"
        if state != "disabled":
            assert image.getpixel((8, 8) if active else (22, 9)) == ((255, 255, 255) if active else (0, 0, 0))
        if state == "hovered":
            assert image.getpixel((18 if active else 1, 9)) == (229, 151, 0)
        if state == "focused":
            assert image.getpixel((2 if active else 20, 2)) == (0, 0, 0)
        # The light thumb must occupy the correct half, independently of icon/background matches.
        if state == "normal":
            assert min(image.getpixel((26 if active else 9, 9))) > 200
            assert image.tobytes() != gtk_images[version, "switch", f"{'off' if active else 'on'}-normal"].tobytes()
