"""Luna thumb variants: pointed toward marks, green-capped when unmarked."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider
from reference import qimage_to_pil


@pytest.mark.parametrize("orientation", (Qt.Horizontal, Qt.Vertical))
@pytest.mark.parametrize("ticks", (QSlider.NoTicks, QSlider.TicksAbove, QSlider.TicksBelow, QSlider.TicksBothSides))
def test_native_slider_shape_and_marks_follow_tick_position(qt_app, orientation, ticks):
    import chicago95luna

    style = chicago95luna.LunaStyle()
    slider = QSlider(orientation)
    slider.setStyle(style)
    slider.setPalette(chicago95luna.luna_palette())
    slider.setRange(0, 100)
    slider.setValue(50)
    slider.setTickInterval(25)
    slider.setTickPosition(ticks)
    slider.resize(180, 45) if orientation == Qt.Horizontal else slider.resize(45, 180)
    image = qimage_to_pil(slider.grab().toImage())
    option = QStyleOptionSlider()
    slider.initStyleOption(option)
    handle = style.subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderHandle, slider)
    thumb = image.crop((handle.x(), handle.y(), handle.right() + 1, handle.bottom() + 1))
    if orientation == Qt.Vertical:
        from PIL import Image

        thumb = thumb.transpose(Image.Transpose.TRANSPOSE)
    assert thumb.size == (11, 21)
    assert (73, 201, 75) in set(thumb.get_flattened_data())
    if ticks in (QSlider.TicksAbove, QSlider.TicksBelow):
        for distance, width in enumerate((1, 3, 5, 7, 9)):
            y = distance if ticks == QSlider.TicksAbove else 20 - distance
            filled = sum(thumb.getpixel((x, y)) != (236, 233, 216) for x in range(11))
            assert filled == width, "the thumb must taper to a centred point, not a rectangle"
    else:
        assert thumb.getpixel((0, 0)) != (236, 233, 216)
        assert thumb.getpixel((10, 20)) != (236, 233, 216)
    marks = sum(pixel == (172, 168, 153) for pixel in image.get_flattened_data())
    assert marks == (0 if ticks == QSlider.NoTicks else 30 if ticks == QSlider.TicksBothSides else 15)
    slider.close()
