import configparser
import importlib.util
import xml.etree.ElementTree as ElementTree
from collections import defaultdict

import pytest
from conftest import REPO
from PySide6.QtSvg import QSvgRenderer

GENERATOR = REPO / "luna/kvantum/make_luna_kvantum.py"
COMMITTED = REPO / "luna/kvantum/Chicago95Luna"
SVG_NAMESPACE = "{http://www.w3.org/2000/svg}"
spec = importlib.util.spec_from_file_location("make_luna_kvantum", GENERATOR)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)

PIECES = ("topleft", "top", "topright", "left", "right", "bottomleft", "bottom", "bottomright")
FRAME_STATES = {
    "button": ("normal", "focused", "pressed", "toggled", "disabled"),
    "tbutton": ("normal", "focused", "pressed", "toggled"),
    "lineedit": ("normal", "focused", "disabled"),
    "combo": ("normal", "focused", "pressed", "disabled"),
    "dropdown": ("normal", "focused", "pressed", "disabled"),
    "spin": ("normal", "focused", "pressed", "disabled"),
    "scrollbarbutton": ("normal", "focused", "pressed"),
    "scrollbarslider": ("normal", "focused", "pressed"),
    "tab": ("normal", "focused", "toggled"),
    "header": ("normal", "focused", "pressed"),
    "slider": ("normal", "toggled"),
    "scrollbargroove": ("normal",),
    "tabframe": ("normal",),
    "group": ("normal",),
    "menu": ("normal",),
    "tooltip": ("normal",),
    "toolbar": ("normal",),
    "progress": ("normal",),
}
INTERIORLESS = {"tabframe", "group"}
SINGLE_ELEMENTS = [
    "button-default-indicator",
    "tabpage-normal",
    "dock-normal",
    "titlebar-focused",
    "titlebar-normal",
    "progress-pattern-normal",
    "progress-pattern-disabled",
    "header-separator",
    "toolbar-handle",
    "sizegrip-normal",
    "focus-top",
    "focus-bottom",
    "focus-left",
    "focus-right",
    *(f"{prefix}-{state}" for prefix in ("menuitem", "menubaritem", "itemview") for state in ("pressed", "toggled", "focused")),
    *(f"slidercursor-{state}" for state in ("normal", "focused", "pressed", "disabled")),
    *(f"grip-{state}" for state in ("normal", "focused", "pressed")),
    *(f"arrow-{direction}-{state}" for direction in ("up", "down", "left", "right", "plus", "minus") for state in ("normal", "focused", "pressed", "disabled")),
    *(
        f"{kind}-{state}"
        for kind in ("checkbox", "checkbox-checked", "checkbox-tristate", "radio", "radio-checked")
        for state in ("normal", "focused", "pressed", "disabled")
    ),
]
REQUIRED_IDS = sorted(
    {
        *SINGLE_ELEMENTS,
        *(f"{prefix}-{state}" for prefix, states in FRAME_STATES.items() for state in states if prefix not in INTERIORLESS),
        *(f"{prefix}-{state}-{piece}" for prefix, states in FRAME_STATES.items() for state in states for piece in PIECES),
    }
)
ALLOWED_TAGS = {"svg", "defs", "g", "rect", "path", "circle", "polygon", "linearGradient", "stop"}
TOTAL_BUDGET, GROUP_BUDGET, ELEMENT_BUDGET = 125_000, 14_000, 1_800


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    out = tmp_path_factory.mktemp("kvantum")
    generator.write_theme(out)
    return out


@pytest.fixture(scope="module")
def svg_root():
    return ElementTree.parse(COMMITTED / "Chicago95Luna.svg").getroot()


@pytest.fixture(scope="module")
def element_ids(svg_root):
    return {node.get("id") for node in svg_root.iter(f"{SVG_NAMESPACE}g")}


@pytest.fixture(scope="module")
def kvconfig():
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(COMMITTED / "Chicago95Luna.kvconfig")
    return parser


def test_committed_theme_equals_generator_output(generated):
    assert [(COMMITTED / name).read_text() for name in ("Chicago95Luna.svg", "Chicago95Luna.kvconfig")] == [
        (generated / name).read_text() for name in ("Chicago95Luna.svg", "Chicago95Luna.kvconfig")
    ]


def test_every_required_element_id_is_in_the_svg(element_ids):
    assert [name for name in REQUIRED_IDS if name not in element_ids] == []


def test_svg_uses_only_simple_shapes(svg_root):
    assert {node.tag.removeprefix(SVG_NAMESPACE) for node in svg_root.iter()} - ALLOWED_TAGS == set()


def test_every_element_id_is_unique(svg_root):
    ids = [node.get("id") for node in svg_root.iter(f"{SVG_NAMESPACE}g")]

    assert len(ids) == len(set(ids))


def test_svg_size_is_within_the_total_budget():
    assert (COMMITTED / "Chicago95Luna.svg").stat().st_size < TOTAL_BUDGET


def test_element_groups_stay_within_the_byte_budget(svg_root):
    sizes = defaultdict(int)
    largest = 0
    for node in svg_root.iter(f"{SVG_NAMESPACE}g"):
        size = len(ElementTree.tostring(node))
        sizes[node.get("id").split("-")[0]] += size
        largest = max(largest, size)

    assert (max(sizes.values()) < GROUP_BUDGET, largest < ELEMENT_BUDGET) == (True, True)


def test_corner_pieces_are_drawn_exactly_at_their_frame_size(element_ids):
    renderer = QSvgRenderer(str(COMMITTED / "Chicago95Luna.svg"))
    sizes = {prefix: spec["size"] for prefix, spec in generator.stops.FRAMES.items()}
    drawn = {
        prefix: (renderer.boundsOnElement(f"{prefix}-{FRAME_STATES[prefix][0]}-bottomright").width(), renderer.boundsOnElement(f"{prefix}-{FRAME_STATES[prefix][0]}-topleft").height())
        for prefix in sizes
    }

    assert drawn == {prefix: (size, size) for prefix, size in sizes.items()}


def test_every_required_element_renders_in_qt(element_ids):
    renderer = QSvgRenderer(str(COMMITTED / "Chicago95Luna.svg"))

    assert [name for name in REQUIRED_IDS if not renderer.elementExists(name)] == []


def test_svg_carries_the_measured_luna_colours():
    text = (COMMITTED / "Chicago95Luna.svg").read_text()

    assert [colour in text for colour in ("#003C74", "#FFC73C", "#7F9DB9", "#919B9C", "#ACA899", "#316AC5", "#FFFFE1", "#ECE9D8", "#1C5180", "#21A121", "#0058EE", "#E68B2C")] == [True] * 12


def test_button_gradient_runs_from_white_to_the_bottom_row_colour(svg_root):
    gradient = next(node for node in svg_root.iter(f"{SVG_NAMESPACE}linearGradient") if node.get("id") == "button-body")
    colours = [stop.get("stop-color") for stop in gradient]

    assert (colours[0], colours[-1]) == ("#FFFFFF", "#D6D0C5")


def test_kvconfig_names_the_theme_and_turns_effects_off(kvconfig):
    assert {key: kvconfig["%General"][key] for key in ("comment", "composite", "animate_states", "translucent_windows", "menu_shadow_depth")} == {
        "comment": "Windows XP Luna",
        "composite": "false",
        "animate_states": "false",
        "translucent_windows": "false",
        "menu_shadow_depth": "0",
    }


def test_kvconfig_sizes_are_the_measured_ones(kvconfig):
    assert (
        kvconfig["%General"]["scroll_width"],
        kvconfig["PanelButtonCommand"]["min_height"],
        kvconfig["Tab"]["min_height"],
        kvconfig["CheckBox"]["indicator.size"],
        kvconfig["RadioButton"]["indicator.size"],
    ) == ("17", "23", "21", "13", "13")


def test_kvconfig_palette_is_the_luna_one(kvconfig):
    assert {key: kvconfig["GeneralColors"][key] for key in ("window.color", "base.color", "highlight.color", "tooltip.base.color", "highlight.text.color")} == {
        "window.color": "#ECE9D8",
        "base.color": "#FFFFFF",
        "highlight.color": "#316AC5",
        "tooltip.base.color": "#FFFFE1",
        "highlight.text.color": "#FFFFFF",
    }


def test_kvconfig_sections_cover_every_styled_widget(kvconfig):
    widgets = {"PanelButtonCommand", "PanelButtonTool", "LineEdit", "ComboBox", "DropDownButton", "IndicatorSpinBox", "Tab", "TabFrame", "CheckBox", "RadioButton", "Scrollbar", "ScrollbarSlider", "ScrollbarGroove", "Slider", "SliderCursor", "Progressbar", "ProgressbarContents", "Menu", "MenuItem", "MenuBarItem", "ToolTip", "HeaderSection", "TitleBar", "GroupBox", "Toolbar", "ItemView", "Focus"}

    assert widgets - set(kvconfig.sections()) == set()


def test_every_element_a_kvconfig_section_names_exists_in_the_svg(kvconfig, element_ids):
    states = ("normal", "pressed", "focused", "toggled")
    missing = []
    for section in kvconfig.sections():
        entries = kvconfig[section]
        frame, interior = entries.get("frame.element"), entries.get("interior.element")
        if frame and entries.get("frame") != "false" and f"{frame}-normal-topleft" not in element_ids and f"{frame}-top" not in element_ids:
            missing.append((section, frame))
        if interior and entries.get("interior") != "false" and not any(f"{interior}-{state}" in element_ids for state in states):
            missing.append((section, interior))

    assert missing == []


def test_stops_agree_with_the_qt_style_constants():
    import chicago95luna as style

    stops = generator.stops
    assert (
        stops.BORDER,
        stops.FIELD_BORDER,
        stops.PAGE_BORDER,
        stops.MENU_BORDER,
        stops.CHECK_BORDER,
        stops.CHECK_MARK,
        stops.CHECK_MARK_DISABLED,
        stops.CHECK_BORDER_DISABLED,
        stops.DISABLED_BORDER,
        stops.DISABLED_TEXT,
        list(stops.HOVER_RING_LIGHT),
        list(stops.HOVER_RING_DARK[::-1]),
        stops.GROUP_BORDER,
        [colour for _, colour in stops.GRADIENTS["button-pressed"]],
        stops.HOVER_BORDER,
    ) == (
        style.BUTTON_BORDER,
        style.FIELD_BORDER,
        style.TAB_BORDER,
        style.MENU_FRAME,
        style.INDICATOR_BORDER,
        style.INDICATOR_MARK,
        style.INDICATOR_MARK_DISABLED,
        style.INDICATOR_BORDER_DISABLED,
        style.BUTTON_BORDER_DISABLED,
        style.DISABLED_TEXT,
        style.HOVER_RING_LIGHT,
        style.HOVER_RING_DARK,
        style.GROUP_FRAME,
        style.BUTTON_PRESSED_GRADIENT,
        style.DROP_BUTTON_HOVER_BORDER,
    )
