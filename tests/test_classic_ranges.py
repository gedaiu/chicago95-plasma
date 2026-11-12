"""Native classic GTK ranges against Qt and the reference-tested 9x slider shape."""

import sys
from pathlib import Path

import pytest
from PIL import Image, ImageChops
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QProgressBar, QSlider, QStyle, QStyleOptionSlider
from reference import qimage_to_pil

sys.path.insert(0, str(Path(__file__).parent / "luna"))
from test_luna_gtk_visual_consistency import load_images  # noqa: E402

STATES = ("normal", "start", "end", "disabled", "hovered", "pressed")


@pytest.fixture(scope="module")
def classic_ranges(tmp_path_factory, qt_app):
    from showcase import gtk_controls

    folder = tmp_path_factory.mktemp("classic-ranges")
    gtk_controls("1995", folder, audit=True, audit_kinds=("slider", "slider-before", "slider-after", "progress"))
    return load_images(folder, "#c0c0c0")


@pytest.mark.parametrize("point", (None, "before", "after"))
@pytest.mark.parametrize("orientation", ("horizontal", "vertical"))
@pytest.mark.parametrize("state", STATES)
def test_classic_sliders_match_between_gtk_versions(classic_ranges, point, orientation, state):
    kind = "slider" + (f"-{point}" if point else "")
    a, b = (classic_ranges[v, kind, f"{state}-{orientation}"] for v in ("3.0", "4.0"))
    assert a.size == b.size
    assert ImageChops.difference(a, b).getbbox() is None


@pytest.mark.parametrize("point", (None, "before", "after"))
@pytest.mark.parametrize("orientation", ("horizontal", "vertical"))
@pytest.mark.parametrize("state", STATES)
def test_classic_gtk_thumb_matches_actual_qt(qt_app, classic_ranges, point, orientation, state):
    horizontal = orientation == "horizontal"
    slider = QSlider(Qt.Horizontal if horizontal else Qt.Vertical)
    slider.setTickPosition({None: QSlider.NoTicks, "before": QSlider.TicksAbove, "after": QSlider.TicksBelow}[point])
    slider.setEnabled(state != "disabled")
    slider.resize(180, 30) if horizontal else slider.resize(30, 180)
    option = QStyleOptionSlider()
    slider.initStyleOption(option)
    option.subControls = QStyle.SC_SliderHandle
    if state == "hovered":
        option.state |= QStyle.State_MouseOver
    if state == "pressed":
        option.state |= QStyle.State_Sunken
    option.activeSubControls = QStyle.SC_SliderHandle
    rect = slider.style().subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderHandle, slider)
    image = QImage(slider.size(), QImage.Format_RGB32)
    image.fill("#ff00ff")
    painter = QPainter(image)
    slider.style().drawComplexControl(QStyle.CC_Slider, option, painter, slider)
    painter.end()
    thumb = qimage_to_pil(image).crop((rect.x(), rect.y(), rect.right() + 1, rect.bottom() + 1))
    # Transparent corners expose the channel below; compare every opaque thumb pixel.
    pixels = [
        (x, y, thumb.getpixel((x, y)))
        for y in range(thumb.height)
        for x in range(thumb.width)
        if thumb.getpixel((x, y)) != (255, 0, 255)
    ]
    kind = "slider" + (f"-{point}" if point else "")
    for version in ("3.0", "4.0"):
        gtk = classic_ranges[version, kind, f"{state}-{orientation}"]
        matches = [
            (left, top)
            for top in range(gtk.height - thumb.height + 1)
            for left in range(gtk.width - thumb.width + 1)
            if all(gtk.getpixel((left + x, top + y)) == colour for x, y, colour in pixels)
        ]
        assert len(matches) == 1, (version, point, orientation, state, matches)


@pytest.mark.parametrize("orientation", ("horizontal", "vertical"))
@pytest.mark.parametrize("state", ("empty", "low", "half", "full", "disabled", "inverted", "rtl"))
def test_classic_progress_inset_and_thickness(qt_app, classic_ranges, orientation, state):
    a, b = (classic_ranges[v, "progress", f"{state}-{orientation}"] for v in ("3.0", "4.0"))
    assert a.size == b.size
    assert ImageChops.difference(a, b).getbbox() is None
    if orientation == "vertical":
        a = a.transpose(Image.Transpose.TRANSPOSE)
    bar = QProgressBar()
    bar.setTextVisible(False)
    bar.setValue(100)
    bar.resize(260, bar.sizeHint().height())
    qt = qimage_to_pil(bar.grab().toImage())
    assert a.height == qt.height == 19
    assert next(x for x in range(qt.width) if qt.getpixel((x, 3)) == (0, 0, 128)) == 3
    bar.close()
    for x in range(1, a.width - 1):
        for y in (1, 2, 16, 17):
            assert a.getpixel((x, y)) == (192, 192, 192)
    if state == "full":
        assert a.getpixel((3, 3)) == (0, 0, 128)


@pytest.mark.parametrize("state", STATES)
def test_classic_horizontal_channel_has_reference_bevel(classic_ranges, state):
    for version in ("3.0", "4.0"):
        image = classic_ranges[version, "slider-after", f"{state}-horizontal"]
        # A point far from the thumb, including either endpoint state.
        x = 20 if state == "end" else 150
        assert [image.getpixel((x, y)) for y in range(7, 11)] == [
            (128, 128, 128),
            (0, 0, 0),
            (192, 192, 192),
            (255, 255, 255),
        ]
