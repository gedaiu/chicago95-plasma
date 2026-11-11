"""Builds the Chicago95Luna Plasma desktop theme: the Windows XP taskbar, task and Start buttons, popups, widgets.

    make_luna_plasmastyle.py [--out DIR] [--base DIR]

Every frame is vector geometry (frames.py): a rounded rectangle with a fitted gradient body, one pixel rings and washes,
cut into the nine pieces KSvg expects. The gradients, ring colours and radii are fitted to the screenshots in
tests/references and documented in stops.py: the taskbar (xptaskbar-1x.png), the task buttons (xprunning.png), the Start
pill (xptaskbar-1x.png) and the push button (xpdisplayprop-1x.png). The popup, tooltip, line edit and menu colours are
the Luna values: popup border #ACA899, tooltip #FFFFE1 with a black border, fields #7F9DB9, list selection #316AC5, menu
separators #C6D7F1.

The scroll bars, sliders, headings, frames, arrows, radio buttons, meters, switches and the pager are drawn by
controls.py. The other files (the clock, the busy indicator, the action overlays) come from --base (default
plasma-style/theme, the React Plus based flat theme) unchanged. XP panels have no inset and no shadow.
"""

import argparse
import dataclasses
import importlib.util
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LUNA_ROOT = HERE.parent
FLAT_THEME = LUNA_ROOT.parent / "plasma-style" / "theme"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


primitives = load_module("luna_primitives", LUNA_ROOT / "aurorae/luna.py")
palette = load_module("luna_palette", LUNA_ROOT / "palette.py")
frames = load_module("luna_frames", HERE / "frames.py")
stops = load_module("luna_plasma_stops", HERE / "stops.py")
controls = load_module("luna_controls", HERE / "controls.py")
hidden, linked_svg, rect, svg = primitives.hidden, primitives.linked_svg, primitives.rect, primitives.svg
FrameSpec = frames.FrameSpec

FACE = palette.PALETTE["face"]
SELECTION = palette.PALETTE["selection"]
WHITE, BLACK = "#FFFFFF", "#000000"
POPUP_BORDER = "#ACA899"
TOOLTIP_FILL = "#FFFFE1"
BUTTON_BORDER = "#003C74"
BUTTON_PRESSED = "#E3E3DB"
BUTTON_HOVER_RING, BUTTON_FOCUS_RING = "#FFC73C", "#C1D2EE"
FIELD_BORDER = "#7F9DB9"
MENU_LINE = "#C6D7F1"
ATTENTION_TOP, ATTENTION_BOTTOM = "#F8B048", "#E09020"
HOVER_LIFT, PRESSED_DARKEN, ATTENTION_OUTLINE_DARKEN = 0.12, 0.18, 0.3
MIDDLE = 8
TASK_EDGE, TASK_HEIGHT, TASK_RADIUS = 4, 25, 3
TASK_LABEL_LEFT, TASK_LABEL_RIGHT, TASK_LABEL_VERTICAL = 25, 6, 3
START_WIDTH, START_HEIGHT, START_LEFT_EDGE, START_RIGHT_EDGE = 98, 30, 3, 16
START_RADII = (0, (6, 15), (6, 15), 0)
BUTTON_HEIGHT, BUTTON_RADIUS = 23, 4
SQUARE_SIZE = 1 + MIDDLE + 1
FACE_GROUPS = ("[Colors:Window]", "[Colors:Button]", "[Colors:Complementary]", "[Colors:Header]")
BACKGROUND_KEYS = ("BackgroundNormal", "BackgroundAlternate")

METADATA = {
    "KPackageStructure": "Plasma/Theme",
    "KPlugin": {
        "Authors": [{"Name": "Bending Unit 22"}],
        "Category": "Plasma Theme",
        "Description": "Chicago95 Windows XP Luna taskbar and widgets, built on React Plus",
        "Id": "Chicago95Luna",
        "License": "GPL-2.0+",
        "Name": "Chicago95 Luna",
        "Version": "1.0",
    },
    "X-Plasma-API": "5.0",
}


def to_rgb(colour):
    return tuple(int(colour[index : index + 2], 16) for index in (1, 3, 5))


def blend(colour, target, amount):
    mixed = (a + (b - a) * amount for a, b in zip(to_rgb(colour), to_rgb(target), strict=True))
    return "#" + "".join(f"{max(0, min(255, round(value))):02X}" for value in mixed)


frames_svg = frames.frames_svg


def uniform(value):
    return (value, value, value, value)


def all_sides(colour):
    return {side: colour for side in frames.SIDES}


def panel_svg():
    width, edges = 1 + MIDDLE + 1, (0, 0, 0, 0)
    panel = FrameSpec(width, 30, edges, uniform(0), body=stops.TASKBAR)
    mask = FrameSpec(width, 30, edges, uniform(0), body=BLACK)
    return frames_svg([("", panel), ("mask-", mask)])


def task_margins():
    return (TASK_LABEL_VERTICAL, TASK_LABEL_VERTICAL, TASK_LABEL_LEFT, TASK_LABEL_RIGHT)


def task_spec(look, body=None, ring=None):
    return FrameSpec(
        2 * TASK_EDGE + MIDDLE,
        TASK_HEIGHT,
        (TASK_EDGE, TASK_EDGE, 0, 0),
        task_margins(),
        radii=(TASK_RADIUS,) * 4,
        body=body or look["body"],
        rings=tuple(ring for ring in (ring or look["ring"], look.get("bevel")) if ring),
    )


def tabbar_svg():
    """Plasma draws the system tray's current item and its tabs with the active tab: the pressed task pill, in every place."""
    pressed = dataclasses.replace(task_spec(stops.TASK_PRESSED), margins=(2, 2, 2, 2))
    prefixes = [f"{place}-active-tab-" for place in ("north", "south", "west", "east")]
    aliases = {prefix: (prefixes[0], None) for prefix in prefixes[1:]}
    return frames_svg([(prefix, pressed) for prefix in prefixes], aliases=aliases)


def attention_spec():
    top_edge, bottom_edge = (
        blend(colour, BLACK, ATTENTION_OUTLINE_DARKEN) for colour in (ATTENTION_TOP, ATTENTION_BOTTOM)
    )
    ring = {"left": blend(top_edge, bottom_edge, 0.5), "right": blend(top_edge, bottom_edge, 0.5)}
    ring |= {"top": top_edge, "bottom": bottom_edge}
    body = [(0, ATTENTION_TOP), (TASK_HEIGHT - 1, ATTENTION_BOTTOM)]
    return task_spec(stops.TASK_NORMAL, body=body, ring=ring)


def tasks_svg():
    normal = task_spec(stops.TASK_NORMAL)
    states = [
        ("normal-", normal),
        ("hover-", normal),
        ("focus-", task_spec(stops.TASK_PRESSED)),
        ("minimized-", normal),
        ("attention-", attention_spec()),
        ("progress-", normal),
    ]
    aliases = {
        "hover-": ("normal-", (WHITE, HOVER_LIFT)),
        "minimized-": ("normal-", None),
        "progress-": ("normal-", None),
    }
    return frames_svg(states, aliases=aliases)


def start_spec():
    look = stops.START
    return FrameSpec(
        START_WIDTH,
        START_HEIGHT,
        (START_LEFT_EDGE, START_RIGHT_EDGE, 0, 0),
        uniform(0),
        radii=START_RADII,
        body=look["body"],
        rings=(look["ring"],),
        halo=look["halo"],
        glow=look["glow"],
        shade=look["shade"],
    )


def startbutton_svg():
    states = [("normal-", start_spec()), ("hover-", start_spec()), ("pressed-", start_spec())]
    aliases = {"hover-": ("normal-", (WHITE, HOVER_LIFT)), "pressed-": ("normal-", (BLACK, PRESSED_DARKEN))}
    return frames_svg(states, aliases=aliases)


def box_spec(border, fill, margin):
    rings = (all_sides(border),) if border else ()
    return FrameSpec(SQUARE_SIZE, SQUARE_SIZE, (1, 1, 1, 1), uniform(margin), body=fill, rings=rings)


def popup_svg(with_insets):
    frames_list = [
        ("", box_spec(POPUP_BORDER, WHITE, 2)),
        ("mask-", box_spec(BLACK, BLACK, 2)),
        ("shadow-", box_spec(None, None, 0)),
    ]
    insets = "\n".join(hidden(f"hint-{side}-inset", 0, 40, 0, 0) for side in ("top", "bottom", "left", "right"))
    return frames_svg(frames_list, f"\n{insets}" if with_insets else "")


def tooltip_svg():
    return frames_svg(
        [
            ("", box_spec(BLACK, TOOLTIP_FILL, 3)),
            ("shadow-", box_spec(None, None, 0)),
            ("mask-", box_spec(BLACK, BLACK, 3)),
        ]
    )


def button_spec(ring, fill=None):
    rings = ({side: ring for side in frames.SIDES} if ring else {}, all_sides(BUTTON_BORDER))
    return FrameSpec(
        2 * BUTTON_RADIUS + MIDDLE,
        BUTTON_HEIGHT,
        (4, 4, 4, 4),
        uniform(4),
        radii=(BUTTON_RADIUS,) * 4,
        body=fill or stops.BUTTON["body"],
        rings=rings,
    )


def button_svg():
    hover, pressed = button_spec(BUTTON_HOVER_RING), button_spec(None, fill=BUTTON_PRESSED)
    states = [
        ("normal-", button_spec(None)),
        ("hover-", hover),
        ("focus-", button_spec(BUTTON_FOCUS_RING)),
        ("pressed-", pressed),
        ("toolbutton-hover-", hover),
        ("toolbutton-pressed-", pressed),
    ]
    aliases = {"toolbutton-hover-": ("hover-", None), "toolbutton-pressed-": ("pressed-", None)}
    return frames_svg(states, aliases=aliases)


def lineedit_svg():
    return frames_svg(
        [
            ("base-", box_spec(FIELD_BORDER, WHITE, 3)),
            ("focus-", box_spec(SELECTION, None, 3)),
            ("hover-", box_spec(FIELD_BORDER, None, 3)),
        ]
    )


def viewitem_svg():
    states = [
        ("normal-", box_spec(None, None, 0)),
        ("hover-", box_spec(SELECTION, None, 0)),
        ("focus-", box_spec(SELECTION, None, 0)),
        ("selected-", box_spec(SELECTION, SELECTION, 0)),
        ("selected+hover-", box_spec(SELECTION, SELECTION, 0)),
    ]
    aliases = {"focus-": ("hover-", None), "selected+hover-": ("selected-", None)}
    return frames_svg(states, aliases=aliases)


def line_svg():
    parts = [
        f'<g id="horizontal-line">{rect(0, 0, 32, 1, MENU_LINE)}</g>',
        f'<g id="vertical-line">{rect(40, 0, 1, 32, MENU_LINE)}</g>',
    ]
    return svg(48, 32, "\n".join(parts))


def with_values(colours, values):
    """The colour file with the given {(group, key): "r,g,b"} values set."""
    group, lines = None, []
    for line in colours.splitlines():
        group = line if line.startswith("[") else group
        key = line.split("=", 1)[0]
        lines.append(f"{key}={values[group, key]}" if (group, key) in values else line)
    return "\n".join(lines) + "\n"


def rgb_text(colour):
    return ",".join(str(channel) for channel in to_rgb(colour))


def luna_colour_values():
    values = {(group, key): rgb_text(FACE) for group in FACE_GROUPS for key in BACKGROUND_KEYS}
    values["[Colors:Complementary]", "ForegroundNormal"] = rgb_text(WHITE)
    values.update({("[Colors:Selection]", key): rgb_text(SELECTION) for key in BACKGROUND_KEYS})
    return values


GENERATED = {
    "widgets/tabbar.svg": tabbar_svg,
    "widgets/panel-background.svg": panel_svg,
    "widgets/tasks.svg": tasks_svg,
    "widgets/startbutton.svg": startbutton_svg,
    "widgets/tooltip.svg": tooltip_svg,
    "solid/widgets/tooltip.svg": tooltip_svg,
    "widgets/background.svg": lambda: popup_svg(True),
    "solid/widgets/background.svg": lambda: popup_svg(True),
    "dialogs/background.svg": lambda: popup_svg(False),
    "solid/dialogs/background.svg": lambda: popup_svg(False),
    "widgets/button.svg": button_svg,
    "widgets/lineedit.svg": lineedit_svg,
    "widgets/viewitem.svg": viewitem_svg,
    "widgets/line.svg": line_svg,
}


def actionbutton_svg():
    hover, pressed = button_spec(BUTTON_HOVER_RING), button_spec(None, fill=BUTTON_PRESSED)
    return frames_svg([("normal-", button_spec(None)), ("hover-", hover), ("pressed-", pressed)])


GENERATED["widgets/actionbutton.svg"] = actionbutton_svg
GENERATED.update(controls.GENERATED)


def write_theme(out, base):
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(base, out, symlinks=True)
    for name, make in GENERATED.items():
        (out / name).parent.mkdir(parents=True, exist_ok=True)
        (out / name).write_text(make())
    (out / "colors").write_text(with_values((out / "colors").read_text(), luna_colour_values()))
    (out / "metadata.json").write_text(json.dumps(METADATA, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=HERE / "theme")
    parser.add_argument("--base", type=Path, default=FLAT_THEME)
    options = parser.parse_args()
    write_theme(options.out, options.base)
    print("wrote", options.out)
