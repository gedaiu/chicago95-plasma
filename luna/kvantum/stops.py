"""Colours, gradients and sizes of the Chicago95Luna Kvantum theme, taken from LunaStyle (luna/lib/chicago95luna.py)
and the fits in luna/plasma-style/stops.py; the generator turns every row of this table into SVG.

A gradient is a list of (offset, colour) from top to bottom of an element. The push button body is the BUTTON fit of
luna/plasma-style/stops.py (xpdisplayprop-1x.png) and is added by the generator as "button-body", the title bar
gradients are the palette's title_active and title_inactive columns ("title-active", "title-inactive").

Measured in tests/references (see LunaStyle): button border, hover ring, default ring, tab rows, field frame, drop
button, check box border and tick, progress frame and chunk, header colours. Approximated because the references do not
show them: the scroll bar thumb and its arrow buttons (the blue of the drop button), the slider thumb, the group box
title-less frame, the focus rectangle.

A frame is a nine-piece set (-topleft -top -topright -left -right -bottomleft -bottom -bottomright and the interior
under the bare name): "size" is the width of the pieces in pixels, "radius" the corner radius (0 or size), and a state
gives for each side the one pixel rings from the outside in, and the interior gradient (None for a transparent one).
"""

BORDER = "#003C74"
HOVER_RING_LIGHT = ("#FFF0CF", "#FDD889")
HOVER_RING_DARK = ("#E59700", "#F8B330")
HOVER_BORDER = "#FFC73C"
DEFAULT_RING_TOP = ("#CEE7FF", "#BCD4F6")
DEFAULT_RING_BOTTOM = ("#89ADE4", "#6982EE")
DEFAULT_RING_SIDES = ("#BAD2F5", "#89ADE4")
FIELD_BORDER = "#7F9DB9"
PAGE_BORDER = "#919B9C"
MENU_BORDER = "#ACA899"
GROUP_BORDER = "#D0D0BF"
CHECK_BORDER = "#1C5180"
CHECK_MARK = "#21A121"
CHECK_MARK_DISABLED = "#CAC8BB"
CHECK_BORDER_DISABLED = "#CAC8BB"
CHECK_GLOW = ("#FDDFA2", "#FAC45D")
DISABLED_BORDER = "#C9C7BA"
DISABLED_TEXT = "#A1A192"
ARROW = "#4D6185"
ARROW_DISABLED = "#ACA899"
ARROW_PRESSED = "#1C2B4B"
TREE_BOX_BORDER = "#919B9C"
TREE_BOX_FILL = "#FFFFFF"
FOCUS_DOTS = "#000000"

GRADIENTS = {
    "button-pressed": [(0, "#D0CBBF"), (1 / 3, "#E2E0D8"), (2 / 3, "#DFDFD6"), (1, "#F0F0EC")],
    "default-ring": [(0, DEFAULT_RING_TOP[0]), (0.15, DEFAULT_RING_TOP[1]), (0.8, DEFAULT_RING_BOTTOM[0]), (1, DEFAULT_RING_BOTTOM[1])],
    "white": [(0, "#FFFFFF"), (1, "#FFFFFF")],
    "face": [(0, "#ECE9D8"), (1, "#ECE9D8")],
    "face-hover": [(0, "#F5F3E9"), (1, "#F5F3E9")],
    "face-pressed": [(0, "#D6D2C2"), (1, "#D6D2C2")],
    "tab": [(0, "#FFFFFF"), (0.9, "#F0F0EA"), (1, "#ECEBE6")],
    "tab-selected": [(0, "#FCFCFE"), (1, "#FCFCFE")],
    "tab-page": [(0, "#FCFCFE"), (1, "#F4F3EE")],
    "tooltip": [(0, "#FFFFE1"), (1, "#FFFFE1")],
    "blue-button": [(0, "#C9D8FC"), (1, "#B7C9F3")],
    "blue-button-hover": [(0, "#E1EAFE"), (1, "#CBDAFA")],
    "blue-button-pressed": [(0, "#B7C9F3"), (1, "#C9D8FC")],
    "thumb": [(0, "#DCE6FD"), (0.45, "#C0D0F8"), (1, "#A9BEF2")],
    "thumb-hover": [(0, "#EAF0FE"), (0.45, "#D1DDFA"), (1, "#B7CAF5")],
    "thumb-pressed": [(0, "#B7C9F3"), (0.5, "#A5B9EE"), (1, "#93A9E8")],
    "scrollbar-groove": [(0, "#E6E3D3"), (0.5, "#F6F4EC"), (1, "#FFFFFF")],
    "slider-groove": [(0, "#E3E1D5"), (1, "#E3E1D5")],
    "slider-filled": [(0, "#B7C9F3"), (1, "#B7C9F3")],
    "disabled-face": [(0, "#F5F4EA"), (1, "#F5F4EA")],
    "check": [(0, "#DCDCD7"), (1, "#FFFFFF")],
    "check-pressed": [(0, "#C3C1B7"), (1, "#DEDECF")],
    "white-disabled": [(0, "#FFFFFF"), (1, "#FFFFFF")],
    "progress-chunk": [(0, "#B9F2B4"), (0.3, "#39E63A"), (1, "#1FBF22")],
    "slider-thumb": [(0, "#FFFFFF"), (1, "#F0F0EA")],
    "selection": [(0, "#316AC5"), (1, "#316AC5")],
}


def sides(*rings, top=None, right=None, bottom=None, left=None):
    return {
        "top": list(rings if top is None else top),
        "right": list(rings if right is None else right),
        "bottom": list(rings if bottom is None else bottom),
        "left": list(rings if left is None else left),
    }


HOVER_SIDES = sides(
    top=[BORDER, *HOVER_RING_LIGHT],
    left=[BORDER, *HOVER_RING_LIGHT],
    right=[BORDER, *HOVER_RING_DARK],
    bottom=[BORDER, *HOVER_RING_DARK],
)
BUTTON = {"size": 3, "radius": 3}
FIELD = {"size": 2, "radius": 0}
BLUE_BUTTON = {"size": 2, "radius": 2}
SCROLL_THUMB = {"size": 3, "radius": 3}
TAB_UNSELECTED_TOP = "#91A7B4"
TAB_ORANGE = ("#E68B2C", "#FFC83C", "#FFC73C")

FRAMES = {
    "button": {
        **BUTTON,
        "states": {
            "disabled": {"sides": sides(DISABLED_BORDER), "fill": "disabled-face"},
            "normal": {"sides": sides(BORDER), "fill": "button-body"},
            "focused": {"sides": HOVER_SIDES, "fill": "button-body"},
            "pressed": {"sides": sides(BORDER), "fill": "button-pressed"},
            "toggled": {"sides": sides(BORDER), "fill": "button-pressed"},
        },
    },
    "tbutton": {
        **BUTTON,
        "states": {
            "normal": {"sides": sides("#ECE9D8"), "fill": "face"},
            "focused": {"sides": sides(BORDER), "fill": "button-body"},
            "pressed": {"sides": sides(BORDER), "fill": "button-pressed"},
            "toggled": {"sides": sides(BORDER), "fill": "button-pressed"},
        },
    },
    "lineedit": {
        **FIELD,
        "states": {
            "disabled": {"sides": sides(DISABLED_BORDER, "#ECE9D8"), "fill": "face"},
            "normal": {"sides": sides(FIELD_BORDER, "#FFFFFF"), "fill": "white"},
            "focused": {"sides": sides(FIELD_BORDER, "#FFFFFF"), "fill": "white"},
        },
    },
    "combo": {
        **FIELD,
        "states": {
            "disabled": {"sides": sides(DISABLED_BORDER, "#ECE9D8"), "fill": "face"},
            "normal": {"sides": sides(FIELD_BORDER, "#FFFFFF"), "fill": "white"},
            "focused": {"sides": sides(FIELD_BORDER, "#FFFFFF"), "fill": "white"},
            "pressed": {"sides": sides(FIELD_BORDER, "#FFFFFF"), "fill": "white"},
        },
    },
    "dropdown": {
        **BLUE_BUTTON,
        "states": {
            "disabled": {"sides": sides(DISABLED_BORDER), "fill": "disabled-face"},
            "normal": {"sides": sides("#B2C7F5"), "fill": "blue-button"},
            "focused": {"sides": sides(HOVER_BORDER), "fill": "blue-button-hover"},
            "pressed": {"sides": sides("#B2C7F5"), "fill": "blue-button-pressed"},
        },
    },
    "spin": {
        **BLUE_BUTTON,
        "states": {
            "disabled": {"sides": sides(DISABLED_BORDER), "fill": "disabled-face"},
            "normal": {"sides": sides("#B2C7F5"), "fill": "blue-button"},
            "focused": {"sides": sides(HOVER_BORDER), "fill": "blue-button-hover"},
            "pressed": {"sides": sides("#B2C7F5"), "fill": "blue-button-pressed"},
        },
    },
    "scrollbarbutton": {
        **BLUE_BUTTON,
        "states": {
            "normal": {"sides": sides("#B2C7F5"), "fill": "blue-button"},
            "focused": {"sides": sides(HOVER_BORDER), "fill": "blue-button-hover"},
            "pressed": {"sides": sides("#B2C7F5"), "fill": "blue-button-pressed"},
        },
    },
    "scrollbarslider": {
        **SCROLL_THUMB,
        "states": {
            "normal": {"sides": sides("#8AA3E6"), "fill": "thumb"},
            "focused": {"sides": sides("#8AA3E6"), "fill": "thumb-hover"},
            "pressed": {"sides": sides("#6F8DDB"), "fill": "thumb-pressed"},
        },
    },
    "scrollbargroove": {
        "size": 1,
        "radius": 0,
        "states": {"normal": {"sides": sides(), "fill": "scrollbar-groove"}},
    },
    "slider": {
        "size": 2,
        "radius": 0,
        "states": {
            "normal": {"sides": sides(top=["#ACA899"], left=["#ACA899"], right=["#FFFFFF"], bottom=["#FFFFFF"]), "fill": "slider-groove"},
            "toggled": {"sides": sides(top=["#ACA899"], left=["#ACA899"], right=["#FFFFFF"], bottom=["#FFFFFF"]), "fill": "slider-filled"},
        },
    },
    "tab": {
        "size": 3,
        "radius": 3,
        "states": {
            "normal": {
                "sides": sides(top=[TAB_UNSELECTED_TOP], left=[PAGE_BORDER], right=[PAGE_BORDER], bottom=[]),
                "fill": "tab",
            },
            "focused": {
                "sides": sides(top=list(TAB_ORANGE), left=[PAGE_BORDER], right=[PAGE_BORDER], bottom=[]),
                "fill": "tab",
            },
            "toggled": {
                "sides": sides(top=list(TAB_ORANGE), left=[PAGE_BORDER], right=[PAGE_BORDER], bottom=[]),
                "fill": "tab-selected",
            },
        },
    },
    "tabframe": {
        "size": 1,
        "radius": 0,
        "states": {"normal": {"sides": sides(PAGE_BORDER), "fill": None}},
    },
    "group": {
        "size": 4,
        "radius": 4,
        "states": {"normal": {"sides": sides(GROUP_BORDER), "fill": None}},
    },
    "menu": {
        "size": 1,
        "radius": 0,
        "states": {"normal": {"sides": sides(MENU_BORDER), "fill": "white"}},
    },
    "tooltip": {
        "size": 1,
        "radius": 0,
        "states": {"normal": {"sides": sides("#000000"), "fill": "tooltip"}},
    },
    "toolbar": {
        "size": 1,
        "radius": 0,
        "states": {"normal": {"sides": sides(), "fill": "face"}},
    },
    "header": {
        "size": 2,
        "radius": 0,
        "states": {
            "normal": {"sides": sides(top=[], left=[], bottom=[MENU_BORDER], right=[MENU_BORDER]), "fill": "face"},
            "focused": {"sides": sides(top=[], left=[], bottom=[MENU_BORDER], right=[MENU_BORDER]), "fill": "face-hover"},
            "pressed": {"sides": sides(top=[], left=[], bottom=[MENU_BORDER], right=[MENU_BORDER]), "fill": "face-pressed"},
        },
    },
    "progress": {
        "size": 2,
        "radius": 2,
        "states": {"normal": {"sides": sides("#68A3C6", "#FFFFFF"), "fill": "white"}},
    },
}

SOLIDS = {
    "menuitem": ("pressed", "toggled", "focused"),
    "menubaritem": ("pressed", "toggled", "focused"),
    "itemview": ("pressed", "toggled", "focused"),
}

BOXES = {
    "tabpage-normal": "tab-page",
    "dock-normal": "face",
}

ARROW_STATES = {"normal": ARROW, "focused": ARROW, "pressed": ARROW_PRESSED, "disabled": ARROW_DISABLED}
ARROW_DIRECTIONS = ("up", "down", "left", "right", "plus", "minus")
GLYPH_SIZE = 9
INDICATOR_SIZE = 13
CHECK_TICK = (
    ".....##",
    "....###",
    "#..###.",
    "##.##..",
    ".###...",
    "..##...",
    "...#...",
)
CHECK_KINDS = {"checkbox": ("", "checked", "tristate"), "radio": ("", "checked")}
CHECK_LOOK = {
    "normal": {"border": CHECK_BORDER, "fill": "check", "glow": None},
    "focused": {"border": CHECK_BORDER, "fill": "check", "glow": CHECK_GLOW},
    "pressed": {"border": CHECK_BORDER, "fill": "check-pressed", "glow": None},
    "disabled": {"border": CHECK_BORDER_DISABLED, "fill": "white-disabled", "glow": None},
}
PROGRESS_CHUNK_WIDTH, PROGRESS_CHUNK_GAP, PROGRESS_CHUNK_HEIGHT = 8, 2, 8

SIZES = {
    "button_height": 23,
    "tab_height": 21,
    "scrollbar": 17,
    "check": 13,
    "field_height": 21,
    "menu_item_height": 23,
    "header_height": 20,
    "spin_button_width": 17,
    "slider_groove": 4,
    "slider_handle_width": 11,
    "slider_handle_length": 21,
    "splitter": 5,
}

KVCONFIG_GENERAL = {
    "author": "Chicago95 Plasma",
    "comment": "Windows XP Luna",
    "x11drag": "all",
    "alt_mnemonic": "true",
    "composite": "false",
    "translucent_windows": "false",
    "blurring": "false",
    "popup_blurring": "false",
    "animate_states": "false",
    "menu_shadow_depth": "0",
    "tooltip_shadow_depth": "0",
    "spread_menuitems": "false",
    "scroll_arrows": "true",
    "scrollbar_in_view": "false",
    "transient_scrollbar": "false",
    "scroll_min_extent": "36",
    "button_contents_shift": "true",
    "fill_rubberband": "true",
    "tree_branch_line": "true",
    "layout_spacing": "6",
    "layout_margin": "9",
    "submenu_overlap": "0",
    "no_window_pattern": "true",
    "respect_DE": "true",
}

KVCONFIG_COLORS = {
    "window.color": "face",
    "base.color": "#FFFFFF",
    "alt.base.color": "#F5F4EA",
    "button.color": "face",
    "light.color": "#FFFFFF",
    "mid.light.color": "#F1EFE2",
    "dark.color": "#ACA899",
    "mid.color": "#D6D2C2",
    "highlight.color": "selection",
    "inactive.highlight.color": "selection",
    "text.color": "#000000",
    "window.text.color": "#000000",
    "button.text.color": "#000000",
    "disabled.text.color": "#A1A192",
    "tooltip.base.color": "#FFFFE1",
    "tooltip.text.color": "#000000",
    "highlight.text.color": "#FFFFFF",
    "link.color": "#0000FF",
    "link.visited.color": "#800080",
}

PANEL_BUTTON = {
    "frame": "true",
    "frame.element": "button",
    "interior": "true",
    "interior.element": "button",
    "frame.top": "3",
    "frame.bottom": "3",
    "frame.left": "3",
    "frame.right": "3",
    "indicator.size": "9",
    "indicator.element": "arrow",
    "text.normal.color": "#000000",
    "text.focus.color": "#000000",
    "text.press.color": "#000000",
    "text.toggle.color": "#000000",
    "text.shadow": "false",
    "text.margin": "1",
    "text.iconspacing": "4",
    "text.margin.top": "3",
    "text.margin.bottom": "3",
    "text.margin.left": "6",
    "text.margin.right": "6",
    "min_height": str(SIZES["button_height"]),
}

FIELD_FRAME = {"frame.top": "2", "frame.bottom": "2", "frame.left": "2", "frame.right": "2"}
BLUE_FRAME = {"frame": "true", "interior": "true", "indicator.element": "arrow", **FIELD_FRAME}
ONE_PIXEL_FRAME = {"frame.top": "1", "frame.bottom": "1", "frame.left": "1", "frame.right": "1"}
SELECTION_ONLY = {"frame": "false", "interior": "true", "text.focus.color": "#FFFFFF", "text.press.color": "#FFFFFF", "text.toggle.color": "#FFFFFF"}

SECTIONS = {
    "PanelButtonCommand": PANEL_BUTTON,
    "PanelButtonTool": {"inherits": "PanelButtonCommand", "frame.element": "tbutton", "interior.element": "tbutton", "min_height": "0"},
    "Dock": {"inherits": "PanelButtonCommand", "frame": "false", "interior": "false"},
    "DockTitle": {"inherits": "PanelButtonCommand", "frame": "false", "interior": "true", "interior.element": "dock", "text.bold": "true"},
    "IndicatorSpinBox": {"inherits": "PanelButtonCommand", "frame.element": "spin", "interior.element": "spin", "indicator.element": "arrow", "indicator.size": "7", **FIELD_FRAME, "min_height": "0"},
    "RadioButton": {"inherits": "PanelButtonCommand", "frame": "false", "interior.element": "radio", "indicator.size": str(SIZES["check"]), "min_height": "0", "text.margin.left": "3"},
    "CheckBox": {"inherits": "PanelButtonCommand", "frame": "false", "interior.element": "checkbox", "indicator.size": str(SIZES["check"]), "min_height": "0", "text.margin.left": "3"},
    "Focus": {"inherits": "PanelButtonCommand", "interior": "false", "frame": "true", "frame.element": "focus", **ONE_PIXEL_FRAME, "frame.patternsize": "20"},
    "GenericFrame": {"inherits": "PanelButtonCommand", "frame": "true", "interior": "false", "frame.element": "lineedit", **FIELD_FRAME, "min_height": "0"},
    "LineEdit": {"inherits": "PanelButtonCommand", "frame.element": "lineedit", "interior.element": "lineedit", **FIELD_FRAME, "min_height": str(SIZES["field_height"])},
    "ComboBox": {"inherits": "PanelButtonCommand", "frame.element": "combo", "interior.element": "combo", **FIELD_FRAME, "min_height": str(SIZES["field_height"])},
    "DropDownButton": {"inherits": "PanelButtonCommand", "frame.element": "dropdown", "interior.element": "dropdown", "indicator.element": "arrow-down", **FIELD_FRAME, "min_height": "0"},
    "IndicatorArrow": {"indicator.element": "arrow", "indicator.size": "9"},
    "ToolboxTab": {"inherits": "PanelButtonCommand"},
    "Tab": {"inherits": "PanelButtonCommand", "frame.element": "tab", "interior.element": "tab", "indicator.element": "tab", "frame.top": "3", "frame.bottom": "0", "frame.left": "3", "frame.right": "3", "text.margin.left": "8", "text.margin.right": "8", "text.toggle.color": "#000000", "min_height": str(SIZES["tab_height"])},
    "TabFrame": {"inherits": "PanelButtonCommand", "frame.element": "tabframe", "interior.element": "tabpage", **ONE_PIXEL_FRAME, "min_height": "0"},
    "TabBarFrame": {"inherits": "GenericFrame", "frame": "false", "interior": "false"},
    "TreeExpander": {"inherits": "PanelButtonCommand", "frame": "false", "interior": "false", "indicator.size": "9", "indicator.element": "arrow"},
    "HeaderSection": {"inherits": "PanelButtonCommand", "frame.element": "header", "interior.element": "header", **FIELD_FRAME, "text.margin.left": "6", "min_height": str(SIZES["header_height"])},
    "SizeGrip": {"indicator.element": "sizegrip"},
    "Toolbar": {"inherits": "PanelButtonCommand", "indicator.element": "toolbar", "indicator.size": "6", "frame.element": "toolbar", "interior.element": "toolbar", **ONE_PIXEL_FRAME, "min_height": "0"},
    "Slider": {"inherits": "PanelButtonCommand", "frame.element": "slider", "interior.element": "slider", **FIELD_FRAME, "min_height": "0"},
    "SliderCursor": {"inherits": "PanelButtonCommand", "frame": "false", "interior.element": "slidercursor", "min_height": "0"},
    "Progressbar": {"inherits": "PanelButtonCommand", "frame.element": "progress", "interior.element": "progress", **FIELD_FRAME, "text.focus.color": "#000000", "min_height": "0"},
    "ProgressbarContents": {"inherits": "PanelButtonCommand", "frame": "false", "interior.element": "progress-pattern", "interior.x.patternsize": "10", "min_height": "0"},
    "ItemView": {"inherits": "PanelButtonCommand", "text.margin": "0", "frame": "false", "interior.element": "itemview", **SELECTION_ONLY, "min_height": "0"},
    "Splitter": {"inherits": "PanelButtonCommand", "frame": "false", "interior": "false", "min_height": "0"},
    "Scrollbar": {"inherits": "PanelButtonCommand", **BLUE_FRAME, "frame.element": "scrollbarbutton", "interior.element": "scrollbarbutton", "indicator.size": "7", "min_height": "0"},
    "ScrollbarSlider": {"inherits": "PanelButtonCommand", "frame.element": "scrollbarslider", "interior.element": "scrollbarslider", "frame.top": "3", "frame.bottom": "3", "frame.left": "3", "frame.right": "3", "indicator.element": "grip", "indicator.size": "13", "min_height": "0"},
    "ScrollbarGroove": {"inherits": "PanelButtonCommand", "frame.element": "scrollbargroove", "interior.element": "scrollbargroove", **ONE_PIXEL_FRAME, "frame": "false", "min_height": "0"},
    "MenuItem": {"inherits": "PanelButtonCommand", "interior.element": "menuitem", "indicator.element": "menuitem", "min_height": str(SIZES["menu_item_height"]), "text.margin.left": "4", **SELECTION_ONLY},
    "MenuBarItem": {"inherits": "PanelButtonCommand", "interior.element": "menubaritem", "min_height": "0", **SELECTION_ONLY},
    "MenuBar": {"inherits": "PanelButtonCommand", "frame": "false", "interior": "false", "min_height": "0"},
    "TitleBar": {"inherits": "PanelButtonCommand", "frame": "false", "interior.element": "titlebar", "text.normal.color": "#D8E4F8", "text.focus.color": "#FFFFFF", "text.bold": "true", "text.shadow": "true", "text.shadow.color": "#0A246A", "min_height": "0"},
    "Menu": {"inherits": "PanelButtonCommand", "frame.element": "menu", "interior.element": "menu", **ONE_PIXEL_FRAME, "min_height": "0"},
    "GroupBox": {"inherits": "GenericFrame", "frame": "true", "frame.element": "group", "interior": "false", "text.margin": "0", "frame.top": "4", "frame.bottom": "4", "frame.left": "4", "frame.right": "4", "text.normal.color": "#0046D5", "text.focus.color": "#0046D5", "text.bold": "false"},
    "ToolTip": {"inherits": "GenericFrame", "frame.element": "tooltip", "interior": "true", "interior.element": "tooltip", **ONE_PIXEL_FRAME, "text.margin": "2"},
    "Window": {"interior": "false"},
}
