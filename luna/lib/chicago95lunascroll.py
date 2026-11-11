"""Windows XP Luna scroll bars and sliders for LunaStyle.

Measured from the B00merang Windows XP Luna theme's bitmaps (averaged, not copied) and the XP notepad reference
(tests/references/xpnotepad.png, x=577..592 y=53..380 is a disabled scroll bar):

  trough       17px wide, a gradient across the bar #EEEDE5 .. #F4F3EE .. #FEFEFB
  stepper      17x17, rounded 2.5, vertical gradient; arrow #245CAB, 7x4
               normal #E1EBF8 #CADBF3 #B6CEEF   hover #FBFCFE #DDE8F8 #CADBF3   pressed #79A5E2 #93B6E8 #B6CEEF
               disabled gradient #EEEEE7 .. #E6E6DC, border #C9C9B6, arrow #C9C9C2
  slider       same family, the gradient across the bar: normal #CADBF3 .. #B6CEEF, hover #DDE8F8 .. #D2E1F5,
               pressed #B3CCEE .. #97B9E8; a grip of four #98BAE9 lines each over a #ECF2FB line
  track bar    1px neutral-grey groove, with no white highlight; thumb 11x21 gradient #F7F7F4 #F3F3EF #DCDCD9 #C3C3C0,
               border #B5C4CD top and left, #778892 bottom and right; green normal caps, orange hover caps;
               a pointed end faces a single row of tick marks, a rectangular thumb serves unmarked/two-sided ranges
"""

from chicago95luna import blend_rows, fill_rows, rounded_path, stroke_rounded
from chicago95lunaslider import GROOVE_ROWS, thumb_pixels
from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPolygonF
from PySide6.QtWidgets import QSlider, QStyle

SCROLL_EXTENT = 17
TROUGH_STOPS = ("#EEEDE5", "#FEFEFB")
ARROW = "#245CAB"
ARROW_DISABLED = "#C9C9C2"
STEPPER_FACES = {
    "normal": ("#E1EBF8", "#CADBF3", "#B6CEEF"),
    "hover": ("#FBFCFE", "#DDE8F8", "#CADBF3"),
    "pressed": ("#79A5E2", "#93B6E8", "#B6CEEF"),
    "disabled": ("#EEEEE7", "#EBEBE3", "#E6E6DC"),
}
STEPPER_BORDERS = {"normal": "#89B0E6", "hover": "#89B0E6", "pressed": "#6D9DE0", "disabled": "#C9C9B6"}
SLIDER_FACES = {"normal": ("#CADBF3", "#B6CEEF"), "hover": ("#DDE8F8", "#D2E1F5"), "pressed": ("#B3CCEE", "#97B9E8")}
GRIP_DARK, GRIP_LIGHT = "#98BAE9", "#ECF2FB"
GRIP_LINES = 4
ARROW_POINTS = {
    "up": ((-3.5, 2), (0, -2), (3.5, 2)),
    "down": ((-3.5, -2), (3.5, -2), (0, 2)),
    "left": ((2, -3.5), (-2, 0), (2, 3.5)),
    "right": ((-2, -3.5), (2, 0), (-2, 3.5)),
}


def part_state(option, sub_control):
    if not option.state & QStyle.State_Enabled:
        return "disabled"
    active = bool(option.activeSubControls & sub_control)
    return {
        (True, True): "pressed",
        (True, False): "hover" if option.state & QStyle.State_MouseOver else "normal",
    }.get((active, bool(option.state & QStyle.State_Sunken)), "normal")


def fill_stripes(painter, rect, horizontal, colours):
    for index, colour in enumerate(colours):
        stripe = (
            QRect(rect.left(), rect.top() + index, rect.width(), 1)
            if horizontal
            else QRect(rect.left() + index, rect.top(), 1, rect.height())
        )
        painter.fillRect(stripe, QColor(colour))


def paint_trough(painter, rect, horizontal):
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, False)
    fill_stripes(painter, rect, horizontal, blend_rows(*TROUGH_STOPS, rect.height() if horizontal else rect.width()))
    painter.restore()


def paint_arrow(painter, rect, direction, colour):
    centre = QPointF(rect.center()) + QPointF(0.5, 0.5)
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, False)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(colour))
    painter.drawPolygon(QPolygonF([centre + QPointF(*point) for point in ARROW_POINTS[direction]]))
    painter.restore()


def paint_stepper(painter, rect, direction, state):
    stops = STEPPER_FACES[state]
    half = max(rect.height() // 2, 1)
    colours = blend_rows(stops[0], stops[1], half) + blend_rows(stops[1], stops[2], rect.height() - half)
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setClipPath(rounded_path(rect, 2.5), Qt.IntersectClip)
    painter.setRenderHint(QPainter.Antialiasing, False)
    fill_rows(painter, rect, colours)
    painter.restore()
    stroke_rounded(painter, rect, 2.5, STEPPER_BORDERS[state])
    paint_arrow(painter, rect, direction, ARROW_DISABLED if state == "disabled" else ARROW)


def paint_grip(painter, rect, horizontal):
    thickness = GRIP_LINES * 2
    long_side, short_side = (rect.width(), rect.height()) if horizontal else (rect.height(), rect.width())
    if long_side < thickness + 6:
        return
    start = (short_side - thickness) // 2
    for line in range(GRIP_LINES):
        for shade, offset in ((GRIP_DARK, 0), (GRIP_LIGHT, 1)):
            across = start + line * 2 + offset
            band = (
                QRect(
                    rect.left() + (rect.width() - thickness) // 2 + line * 2 + offset,
                    rect.top() + 3,
                    1,
                    rect.height() - 6,
                )
                if horizontal
                else QRect(rect.left() + 3, rect.top() + across, rect.width() - 6, 1)
            )
            painter.fillRect(band, QColor(shade))


def paint_scroll_slider(painter, rect, horizontal, state):
    stops = SLIDER_FACES[state]
    across = rect.height() if horizontal else rect.width()
    shades = blend_rows(*stops, across)
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setClipPath(rounded_path(rect, 2.5), Qt.IntersectClip)
    painter.setRenderHint(QPainter.Antialiasing, False)
    fill_stripes(painter, rect, horizontal, shades)
    painter.restore()
    stroke_rounded(painter, rect, 2.5, STEPPER_BORDERS[state])
    paint_grip(painter, rect, horizontal)


def stepper_direction(horizontal, line):
    return {(True, "sub"): "left", (True, "add"): "right", (False, "sub"): "up", (False, "add"): "down"}[
        (horizontal, line)
    ]


def paint_scroll_bar(painter, option, style, widget):
    horizontal = bool(option.state & QStyle.State_Horizontal)
    rect_of = lambda sub_control: style.subControlRect(QStyle.CC_ScrollBar, option, sub_control, widget)  # noqa: E731
    paint_trough(painter, option.rect, horizontal)
    for line, sub_control in (("sub", QStyle.SC_ScrollBarSubLine), ("add", QStyle.SC_ScrollBarAddLine)):
        paint_stepper(
            painter, rect_of(sub_control), stepper_direction(horizontal, line), part_state(option, sub_control)
        )
    slider = rect_of(QStyle.SC_ScrollBarSlider)
    if option.state & QStyle.State_Enabled and option.maximum > option.minimum:
        paint_scroll_slider(painter, slider, horizontal, part_state(option, QStyle.SC_ScrollBarSlider))


def paint_slider_groove(painter, rect, horizontal):
    thickness = len(GROOVE_ROWS)
    centre = rect.center()
    groove = (
        QRect(rect.left(), centre.y() - thickness // 2, rect.width(), thickness)
        if horizontal
        else QRect(centre.x() - thickness // 2, rect.top(), thickness, rect.height())
    )
    fill_stripes(painter, groove, horizontal, GROOVE_ROWS)


def paint_thumb(painter, rect, horizontal, state, point=None):
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, False)
    for y, row in enumerate(thumb_pixels(rect.width(), rect.height(), horizontal, state, point)):
        for x, colour in enumerate(row):
            if colour is not None:
                painter.fillRect(rect.left() + x, rect.top() + y, 1, 1, QColor(colour))
    painter.restore()


def paint_slider(painter, option, style, widget):
    horizontal = option.orientation == Qt.Horizontal
    groove = style.subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderGroove, widget)
    handle = style.subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderHandle, widget)
    groove.adjust(5 if horizontal else 0, 0 if horizontal else 5,
                  -5 if horizontal else 0, 0 if horizontal else -5)
    paint_slider_groove(painter, groove, horizontal)
    state = part_state(option, QStyle.SC_SliderHandle)
    point = {QSlider.TicksAbove: "before", QSlider.TicksBelow: "after"}.get(option.tickPosition)
    paint_thumb(painter, handle, horizontal, state, point)
    if option.subControls & QStyle.SC_SliderTickmarks and option.tickPosition != QSlider.NoTicks:
        interval = option.tickInterval or option.pageStep or 1
        span = max(option.maximum - option.minimum, 1)
        # Do not paint the same pixel millions of times for very large ranges.
        extent = option.rect.width() if horizontal else option.rect.height()
        interval = max(interval, span // max(extent, 1), 1)
        for value in range(option.minimum, option.maximum + 1, interval):
            fraction = (value - option.minimum) / span
            if option.upsideDown:
                fraction = 1 - fraction
            start = option.rect.left() if horizontal else option.rect.top()
            length = option.rect.width() - handle.width() if horizontal else option.rect.height() - handle.height()
            centre = start + round(fraction * length) + (handle.width() if horizontal else handle.height()) // 2
            for before, side in ((True, QSlider.TicksAbove), (False, QSlider.TicksBelow)):
                if option.tickPosition in (side, QSlider.TicksBothSides):
                    edge = ((handle.top() - 5 if before else handle.bottom() + 3) if horizontal else
                            (handle.left() - 5 if before else handle.right() + 3))
                    tick = QRect(centre, edge, 1, 3) if horizontal else QRect(edge, centre, 3, 1)
                    painter.fillRect(tick, QColor("#ACA899"))
