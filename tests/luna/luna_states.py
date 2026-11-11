from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import (
    QStyle,
    QStyleOptionButton,
    QStyleOptionComboBox,
    QStyleOptionFocusRect,
    QStyleOptionFrame,
    QStyleOptionGroupBox,
    QStyleOptionHeader,
    QStyleOptionMenuItem,
    QStyleOptionSlider,
    QStyleOptionSpinBox,
    QStyleOptionTab,
    QStyleOptionToolButton,
    QTabBar,
)

from .luna_tools_support import PREVIEW_DIR

WINDOW_FACE = "#ECE9D8"
ENABLED = QStyle.State_Enabled
STATE_FLAGS = {
    "normal": ENABLED,
    "hover": ENABLED | QStyle.State_MouseOver,
    "pressed": ENABLED | QStyle.State_Sunken | QStyle.State_MouseOver,
    "disabled": QStyle.State_None,
    "focused": ENABLED | QStyle.State_HasFocus,
}


def painted(width, height, paint, background=WINDOW_FACE):
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(QColor(background))
    painter = QPainter(image)
    paint(painter)
    painter.end()
    return image


def with_palette(option, palette, state, rect):
    option.rect = rect
    option.state = STATE_FLAGS[state]
    option.palette = palette
    return option


def push_button(style, palette, state, default=False):
    option = with_palette(QStyleOptionButton(), palette, state, QRect(0, 0, 75, 23))
    if default:
        option.features = QStyleOptionButton.DefaultButton
    return painted(75, 23, lambda painter: style.drawControl(QStyle.CE_PushButtonBevel, option, painter))


def focus_rectangle(style, palette):
    option = with_palette(QStyleOptionFocusRect(), palette, "focused", QRect(0, 0, 40, 16))
    return painted(40, 16, lambda painter: style.drawPrimitive(QStyle.PE_FrameFocusRect, option, painter), "#FFFFFF")


def indicator(style, palette, element, state, checked):
    option = with_palette(QStyleOptionButton(), palette, state, QRect(0, 0, 13, 13))
    option.state |= QStyle.State_On if checked else QStyle.State_Off
    return painted(13, 13, lambda painter: style.drawPrimitive(element, option, painter))


def combo(style, palette, state):
    option = with_palette(QStyleOptionComboBox(), palette, state, QRect(0, 0, 120, 21))
    option.activeSubControls = QStyle.SC_ComboBoxArrow if state in ("hover", "pressed") else QStyle.SC_None
    return painted(120, 21, lambda painter: style.drawComplexControl(QStyle.CC_ComboBox, option, painter))


def spin(style, palette, state):
    option = with_palette(QStyleOptionSpinBox(), palette, state, QRect(0, 0, 80, 21))
    option.subControls = QStyle.SC_SpinBoxUp | QStyle.SC_SpinBoxDown | QStyle.SC_SpinBoxFrame
    option.activeSubControls = QStyle.SC_SpinBoxUp if state in ("hover", "pressed") else QStyle.SC_None
    return painted(80, 21, lambda painter: style.drawComplexControl(QStyle.CC_SpinBox, option, painter))


def scroll_bar(style, palette, state, part):
    option = with_palette(QStyleOptionSlider(), palette, state, QRect(0, 0, 17, 120))
    option.minimum, option.maximum, option.pageStep, option.sliderPosition = 0, 100, 40, 20
    option.orientation = Qt.Vertical
    option.subControls = QStyle.SC_All
    option.activeSubControls = part if state in ("hover", "pressed") else QStyle.SC_None
    return painted(17, 120, lambda painter: style.drawComplexControl(QStyle.CC_ScrollBar, option, painter))


def track_bar(style, palette, state):
    option = with_palette(QStyleOptionSlider(), palette, state, QRect(0, 0, 120, 30))
    option.minimum, option.maximum, option.sliderPosition = 0, 10, 5
    option.orientation = Qt.Horizontal
    option.subControls = QStyle.SC_SliderGroove | QStyle.SC_SliderHandle
    option.activeSubControls = QStyle.SC_SliderHandle if state in ("hover", "pressed") else QStyle.SC_None
    return painted(120, 30, lambda painter: style.drawComplexControl(QStyle.CC_Slider, option, painter))


def tool_button(style, palette, state):
    option = with_palette(QStyleOptionToolButton(), palette, state, QRect(0, 0, 40, 40))
    option.state |= QStyle.State_AutoRaise
    return painted(40, 40, lambda painter: style.drawPrimitive(QStyle.PE_PanelButtonTool, option, painter))


def header_section(style, palette, state):
    option = with_palette(QStyleOptionHeader(), palette, state, QRect(0, 0, 80, 20))
    return painted(80, 20, lambda painter: style.drawControl(QStyle.CE_HeaderSection, option, painter))


def tab(style, palette, state):
    option = with_palette(QStyleOptionTab(), palette, "normal" if state == "selected" else state, QRect(0, 0, 70, 21))
    option.shape = QTabBar.RoundedNorth
    option.position = QStyleOptionTab.TabPosition.Middle
    option.selectedPosition = QStyleOptionTab.SelectedPosition.NotAdjacent
    if state == "selected":
        option.state |= QStyle.State_Selected
    return painted(70, 24, lambda painter: style.drawControl(QStyle.CE_TabBarTabShape, option, painter))


def menu_item(style, palette, state, text="Open"):
    option = with_palette(
        QStyleOptionMenuItem(), palette, "normal" if state == "selected" else state, QRect(0, 0, 160, 21)
    )
    option.menuItemType = QStyleOptionMenuItem.MenuItemType.Normal
    option.text = text
    if state == "selected":
        option.state |= QStyle.State_Selected
    return painted(160, 21, lambda painter: style.drawControl(QStyle.CE_MenuItem, option, painter))


def line_edit(style, palette, state):
    option = with_palette(QStyleOptionFrame(), palette, state, QRect(0, 0, 120, 21))
    option.lineWidth = 1
    return painted(120, 21, lambda painter: style.drawPrimitive(QStyle.PE_PanelLineEdit, option, painter), "#FFFFFF")


def group_box(style, palette, state):
    option = with_palette(QStyleOptionGroupBox(), palette, state, QRect(0, 0, 120, 50))
    option.text = "Group"
    option.subControls = QStyle.SC_GroupBoxFrame | QStyle.SC_GroupBoxLabel
    return painted(120, 50, lambda painter: style.drawComplexControl(QStyle.CC_GroupBox, option, painter))


GALLERY_ROWS = [
    ("push button", ["normal", "hover", "pressed", "disabled"], push_button),
    ("default button", ["normal", "hover", "pressed", "disabled"], lambda s, p, state: push_button(s, p, state, True)),
    (
        "check box on",
        ["normal", "hover", "pressed", "disabled"],
        lambda s, p, state: indicator(s, p, QStyle.PE_IndicatorCheckBox, state, True),
    ),
    (
        "check box off",
        ["normal", "hover", "pressed", "disabled"],
        lambda s, p, state: indicator(s, p, QStyle.PE_IndicatorCheckBox, state, False),
    ),
    (
        "radio on",
        ["normal", "hover", "pressed", "disabled"],
        lambda s, p, state: indicator(s, p, QStyle.PE_IndicatorRadioButton, state, True),
    ),
    (
        "radio off",
        ["normal", "hover", "pressed", "disabled"],
        lambda s, p, state: indicator(s, p, QStyle.PE_IndicatorRadioButton, state, False),
    ),
    ("combo", ["normal", "hover", "pressed", "disabled"], combo),
    ("spin", ["normal", "hover", "pressed", "disabled"], spin),
    ("tab", ["normal", "hover", "selected"], tab),
    (
        "scroll bar",
        ["normal", "hover", "pressed", "disabled"],
        lambda s, p, state: scroll_bar(s, p, state, QStyle.SC_ScrollBarSlider),
    ),
    ("track bar", ["normal", "hover", "pressed", "disabled"], track_bar),
    ("tool button", ["normal", "hover", "pressed"], tool_button),
    ("header", ["normal", "hover", "pressed"], header_section),
    ("menu item", ["normal", "selected", "disabled"], menu_item),
    ("line edit", ["normal", "disabled"], line_edit),
    ("group box", ["normal", "disabled"], group_box),
]
LABEL_WIDTH = 110
MARGIN = 8


def states_gallery_image(style, palette):
    cells = [[renderer(style, palette, state) for state in states] for _name, states, renderer in GALLERY_ROWS]
    row_heights = [max(cell.height() for cell in row) + MARGIN for row in cells]
    width = LABEL_WIDTH + MARGIN + max(sum(cell.width() + MARGIN for cell in row) for row in cells)
    image = QImage(width, sum(row_heights) + MARGIN, QImage.Format_RGB32)
    image.fill(QColor(WINDOW_FACE))
    painter = QPainter(image)
    top = MARGIN
    for (name, _states, _renderer), row, height in zip(GALLERY_ROWS, cells, row_heights, strict=True):
        painter.drawText(QRect(MARGIN, top, LABEL_WIDTH, height - MARGIN), Qt.AlignVCenter, name)
        left = LABEL_WIDTH + MARGIN
        for cell in row:
            painter.drawImage(left, top, cell)
            left += cell.width() + MARGIN
        top += height
    painter.end()
    return image


def save_states_gallery(style, palette):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    states_gallery_image(style, palette).save(str(PREVIEW_DIR / "states-gallery.png"))
