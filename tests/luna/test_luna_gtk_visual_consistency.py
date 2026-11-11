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
def gtk_images(tmp_path_factory):
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
        # GTK4 composites the selected tab/page seam and bitmap slice corners differently.
        # Allow at most 0.2% edge pixels; a shifted border or changed tab size must fail.
        changed = sum(max(pixel) > 2 for pixel in diff.get_flattened_data())
        assert changed <= a.width * a.height * 0.002, f"tab chrome differs; see {tmp_path}"
        low = a.filter(ImageFilter.MinFilter(3))
        high = a.filter(ImageFilter.MaxFilter(3))
        assert ImageChops.subtract(low, b).getbbox() is None
        seam = ImageChops.subtract(b, high).getbbox()
        if seam is not None:
            # GTK4 paints the page highlight over the selected tab's overlap.
            assert position in ("top", "left")
            assert (seam[3] - seam[1] if position == "top" else seam[2] - seam[0]) == 1
            for y in range(seam[1], seam[3]):
                for x in range(seam[0], seam[2]):
                    assert b.getpixel((x, y)) == (255, 255, 255)


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
