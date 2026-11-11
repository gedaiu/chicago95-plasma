"""The smaller Windows XP Luna controls of LunaStyle: tool buttons, tool tips, menu bar items, status bars, size
grips, frames, tree branch boxes and focus rectangles.

  tool button   hover: white face, 1px #7A98AF; pressed: #DCDAD1 .. #E1E0D8 .. #EBEAE5, 1px #9D9D92; radius 3
                (gtk-2.0/Buttons/button-toolbar-active and -pressed of the B00merang Luna theme)
  tool tip      #FFFFE1 face, 1px #000000
  menu bar      face #ECE9D8; the open or hovered item #316AC5 with white text
  status bar    face #ECE9D8, a 1px #ACA899 line on top
  size grip     three diagonals of 2px #ACA899 dots, each with a white dot below and right
  frame         1px #7F9DB9 (fields, lists, text areas)
  branch box    9x9, border #7898B5 with rounded corners, white .. #D2CCBF face, black + or -
  focus         1px dotted #000000
"""

from chicago95luna import (
    FIELD_BORDER,
    blend_rows,
    fill_rows,
    gradient_rows,
    rounded_path,
    stroke_rect,
    stroke_rounded,
)
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPalette, QPen
from PySide6.QtWidgets import QStyle

TOOL_HOVER_FACE, TOOL_HOVER_BORDER = "#FFFFFF", "#7A98AF"
TOOL_PRESSED_FACE = ["#DCDAD1", "#E1E0D8", "#EBEAE5"]
TOOL_PRESSED_BORDER = "#9D9D92"
TOOL_RADIUS = 3
TIP_FACE, TIP_BORDER = "#FFFFE1", "#000000"
BAR_FACE, BAR_LINE = "#ECE9D8", "#ACA899"
GRIP_DOT, GRIP_SHADOW = "#ACA899", "#FFFFFF"
BRANCH_BORDER = "#7898B5"
BRANCH_FACE = ("#FFFFFF", "#D2CCBF")
BRANCH_SIZE = 9
FOCUS_COLOUR = "#000000"


def paint_tool_button(painter, option):
    pressed = bool(option.state & (QStyle.State_Sunken | QStyle.State_On))
    hovered = bool(option.state & QStyle.State_MouseOver)
    if not (pressed or hovered) or not option.state & QStyle.State_Enabled:
        return
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setClipPath(rounded_path(option.rect, TOOL_RADIUS), Qt.IntersectClip)
    painter.setRenderHint(QPainter.Antialiasing, False)
    if pressed:
        fill_rows(painter, option.rect, gradient_rows(TOOL_PRESSED_FACE, option.rect.height()))
    else:
        painter.fillRect(option.rect, QColor(TOOL_HOVER_FACE))
    painter.restore()
    stroke_rounded(painter, option.rect, TOOL_RADIUS, TOOL_PRESSED_BORDER if pressed else TOOL_HOVER_BORDER)


def paint_tip_label(painter, option):
    painter.fillRect(option.rect, QColor(TIP_FACE))
    stroke_rect(painter, option.rect, TIP_BORDER)


def paint_menu_bar_area(painter, option):
    painter.fillRect(option.rect, QColor(BAR_FACE))


def paint_menu_bar_item(painter, option):
    selected = bool(option.state & (QStyle.State_Selected | QStyle.State_Sunken)) and bool(
        option.state & QStyle.State_Enabled
    )
    painter.fillRect(option.rect, option.palette.brush(QPalette.Highlight if selected else QPalette.Window))
    colour = QColor(option.palette.color(QPalette.HighlightedText if selected else QPalette.WindowText))
    if not option.state & QStyle.State_Enabled:
        colour = QColor("#ACA899")
    painter.setPen(colour)
    painter.setFont(option.font)
    painter.drawText(option.rect, Qt.AlignCenter | Qt.TextShowMnemonic | Qt.TextSingleLine, option.text)


def paint_status_bar(painter, option):
    painter.fillRect(option.rect, QColor(BAR_FACE))
    painter.fillRect(option.rect.left(), option.rect.top(), option.rect.width(), 1, QColor(BAR_LINE))


def paint_size_grip(painter, option):
    right, bottom = option.rect.right(), option.rect.bottom()
    for diagonal in range(3):
        for dot in range(diagonal + 1):
            x, y = right - 2 - 4 * dot, bottom - 2 - 4 * (diagonal - dot)
            painter.fillRect(x + 1, y + 1, 2, 2, QColor(GRIP_SHADOW))
            painter.fillRect(x, y, 2, 2, QColor(GRIP_DOT))


def paint_frame(painter, option):
    stroke_rect(painter, option.rect, FIELD_BORDER)


def branch_box(rect):
    return QRect(
        rect.left() + (rect.width() - BRANCH_SIZE) // 2,
        rect.top() + (rect.height() - BRANCH_SIZE) // 2,
        BRANCH_SIZE,
        BRANCH_SIZE,
    )


def paint_branch(painter, option):
    if not option.state & QStyle.State_Children:
        return
    box = branch_box(option.rect)
    inner = box.adjusted(1, 1, -1, -1)
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, False)
    fill_rows(painter, inner, blend_rows(*BRANCH_FACE, inner.height()))
    painter.restore()
    stroke_rounded(painter, box, 2, BRANCH_BORDER)
    painter.fillRect(box.left() + 2, box.center().y(), BRANCH_SIZE - 4, 1, QColor("#000000"))
    if not option.state & QStyle.State_Open:
        painter.fillRect(box.center().x(), box.top() + 2, 1, BRANCH_SIZE - 4, QColor("#000000"))


def paint_focus_rect(painter, option):
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, False)
    painter.setPen(QPen(QColor(FOCUS_COLOUR), 1, Qt.DotLine))
    painter.setBrush(Qt.NoBrush)
    painter.drawRect(option.rect.adjusted(0, 0, -1, -1))
    painter.restore()


PRIMITIVE_PAINTERS = {
    QStyle.PE_PanelButtonTool: paint_tool_button,
    QStyle.PE_PanelTipLabel: paint_tip_label,
    QStyle.PE_PanelMenuBar: paint_menu_bar_area,
    QStyle.PE_PanelStatusBar: paint_status_bar,
    QStyle.PE_Frame: paint_frame,
    QStyle.PE_IndicatorBranch: paint_branch,
    QStyle.PE_FrameFocusRect: paint_focus_rect,
}
CONTROL_PAINTERS = {
    QStyle.CE_MenuBarItem: paint_menu_bar_item,
    QStyle.CE_MenuBarEmptyArea: paint_menu_bar_area,
    QStyle.CE_SizeGrip: paint_size_grip,
}
