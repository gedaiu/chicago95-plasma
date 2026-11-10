"""Writes the Chicago95 Plasma style's generated SVGs (taskbar, task buttons, popups, buttons, fields,
scroll bars) with a look's bevel colours.

    make_chicago95_plasmastyle.py [--out THEME] [--face C] [--light C] [--shadow C] [--dark C] [--base THEME]

THEME is an installed copy of plasma-style/theme, rewritten in place; chicago95-sync-colors runs this
with the colour scheme's face and the look's bevel (2000: light = the face, #808080 and #404040).
--base copies another Plasma style into THEME first (how the theme was first made from React Plus).
The task buttons are measured from the originals' taskbars (tests/test_taskbar_reference.py).
"""
import argparse
import shutil
import sys
from pathlib import Path

# bevel.py sits next to this file once installed, and in ../aurorae in the repository.
sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parent.parent / "aurorae")]
from bevel import hidden, nine_slice, rect, ring_color, run_length_rows, svg  # noqa: E402

HOME = Path.home()
parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--out", type=Path, default=HOME / ".local/share/plasma/desktoptheme/Chicago95")
parser.add_argument("--base", type=Path, help="a Plasma style to copy into --out first")
parser.add_argument("--face", default="#C0C0C0")
parser.add_argument("--light", default="#DFDFDF", help="the light line inside a button's white one (the face itself on 2000)")
parser.add_argument("--shadow", default="#808080")
parser.add_argument("--dark", default="#000000", help="the outer shadow line (#404040 on 2000)")
args = parser.parse_args()
OUT = args.out

FACE, LIGHT, SHADOW, DARK, HILIGHT = args.face, args.light, args.shadow, args.dark, "#FFFFFF"
GLYPH = "#000000"
# Buttons: white and dark outside, light and shadow inside; pressed, the other way round.
RAISED_2 = [(HILIGHT, DARK), (LIGHT, SHADOW)]
SUNKEN_2 = [(DARK, HILIGHT), (SHADOW, LIGHT)]
# Windows and popups: light and dark outside, white and shadow inside, then the face.
RAISED_4 = [(LIGHT, DARK), (HILIGHT, SHADOW), (FACE, FACE), (FACE, FACE)]

BTN = 24
DITHER = 1


def flat(px, py):
    return FACE


def dither(px, py):
    return HILIGHT if ((px // DITHER) + (py // DITHER)) % 2 == 0 else FACE


def pressed_task(prefix, x0):
    """The active window's button: sunken 2px, a white row along the top inside, then a white and face
    checkerboard (the centre tile, 2px square, tiled)."""
    size = BTN

    def color(px, py):
        depth = min(px, py, size - 1 - px, size - 1 - py)
        if depth < 2:
            return ring_color(px, py, size, SUNKEN_2, flat)
        return HILIGHT if py == 2 else dither(px, py)

    def piece(name, fx, fy, w, h):
        return f'<g id="{prefix}{name}">{run_length_rows(x0 + fx, fy, w, h, lambda cx, cy: color(fx + cx, fy + cy))}</g>'

    top, side = 3, 2
    parts = [piece("topleft", 0, 0, side, top), piece("top", side, 0, size - 2 * side, top), piece("topright", size - side, 0, side, top),
             piece("left", 0, top, side, size - top - side), piece("right", size - side, top, side, size - top - side),
             piece("bottomleft", 0, size - side, side, side), piece("bottom", side, size - side, size - 2 * side, side),
             piece("bottomright", size - side, size - side, side, side),
             f'<g id="{prefix}center">{rect(x0 + side, top, 1, 1, HILIGHT)}{rect(x0 + side + 1, top, 1, 1, FACE)}'
             f'{rect(x0 + side, top + 1, 1, 1, FACE)}{rect(x0 + side + 1, top + 1, 1, 1, HILIGHT)}</g>']
    for name in ("top", "bottom", "left", "right"):
        parts.append(hidden(f"{prefix}hint-{name}-margin", x0, size + 2, 2, 2))
    parts.append(hidden(f"{prefix}hint-tile-center", x0, size + 8, 1, 1))
    return "\n".join(parts)


def tasks_svg():
    raised = ["normal-", "hover-", "minimized-", "attention-", "progress-"]
    parts = [nine_slice(prefix, idx * (BTN + 16), 0, BTN, 2, RAISED_2, flat, 2) for idx, prefix in enumerate(raised)]
    parts.append(pressed_task("focus-", len(raised) * (BTN + 16)))
    return svg((len(raised) + 1) * (BTN + 16), BTN + 24, "\n".join(parts))


def panel_svg():
    size = 24
    bar_rings = [(LIGHT, FACE), (HILIGHT, FACE)]
    black = [("#000000", "#000000"), ("#000000", "#000000")]
    parts = [
        nine_slice("", 0, 0, size, 2, bar_rings, flat, 2),
        nine_slice("mask-", size + 16, 0, size, 2, black, lambda px, py: "#000000", 2),
    ]
    return svg(2 * size + 32, size + 12, "\n".join(parts))


def viewitem_svg():
    size = 24
    navy = [("#000080", "#000080"), ("#000080", "#000080")]
    clear = [("none", "none"), ("none", "none")]
    outline = [("#000000", "#000000"), ("none", "none")]
    parts = []
    for idx, (prefix, rings, fill) in enumerate([
        ("normal-", clear, "none"), ("hover-", navy, "#000080"), ("focus-", navy, "#000080"),
        ("selected-", navy, "#000080"), ("selected+hover-", navy, "#000080")]):
        parts.append(nine_slice(prefix, idx * (size + 16), 0, size, 2, rings, lambda px, py, f=fill: f, 0))
    return svg(5 * (size + 16), size + 12, "\n".join(parts))


def white(px, py):
    return HILIGHT


SB = 16


def button_svg():
    size = 24
    clear = [("none", "none"), ("none", "none")]
    states = [("normal-", RAISED_2, flat), ("hover-", RAISED_2, flat), ("focus-", RAISED_2, flat), ("pressed-", SUNKEN_2, flat),
              ("toolbutton-hover-", clear, lambda px, py: "none"), ("toolbutton-pressed-", SUNKEN_2, flat)]
    parts = [nine_slice(prefix, idx * (size + 16), 0, size, 2, rings, fill, 4) for idx, (prefix, rings, fill) in enumerate(states)]
    return svg(len(states) * (size + 16), size + 12, "\n".join(parts))


def lineedit_svg():
    size = 24
    clear = [("none", "none"), ("none", "none")]
    parts = [nine_slice("base-", 0, 0, size, 2, SUNKEN_2, white, 3)]
    parts += [nine_slice(prefix, idx * (size + 16), 0, size, 2, clear, lambda px, py: "none", 3)
              for idx, prefix in enumerate(["focus-", "hover-"], start=1)]
    return svg(3 * (size + 16), size + 12, "\n".join(parts))


def triangle(direction, x0, y0, size, color):
    # 7px wide classic scrollbar arrow drawn as rows of rects, centred in a size x size button.
    rows = [(3, 1), (2, 3), (1, 5), (0, 7)]
    if direction in ("down", "right"):
        rows = rows[::-1]
    cx, cy = x0 + size // 2, y0 + size // 2
    out = []
    for i, (offset, length) in enumerate(rows):
        if direction in ("up", "down"):
            out.append(rect(cx - 3 + offset, cy - 2 + i, length, 1, color))
        else:
            out.append(rect(cx - 2 + i, cy - 3 + offset, 1, length, color))
    return "".join(out)


def arrow_button(element_id, direction, x0, y0, rings):
    body = run_length_rows(x0, y0, SB, SB, lambda px, py: ring_color(px, py, SB, rings, flat))
    shift = 1 if rings is SUNKEN_2 else 0
    return f'<g id="{element_id}">{body}{triangle(direction, x0 + shift, y0 + shift, SB, GLYPH)}</g>'


def scrollbar_svg():
    size = 24
    parts = []
    col = 0
    for prefix in ("background-vertical-", "background-horizontal-"):
        parts.append(nine_slice(prefix, col * (size + 16), 0, size, 1, [(FACE, FACE)], dither, 0, tile_center=True))
        col += 1
    for prefix, rings in (("slider-", RAISED_2), ("mouseover-slider-", RAISED_2), ("sunken-slider-", SUNKEN_2)):
        parts.append(nine_slice(prefix, col * (size + 16), 0, size, 2, rings, flat, 0))
        col += 1
    y = size + 20
    for state, rings in (("", RAISED_2), ("mouseover-", RAISED_2), ("sunken-", SUNKEN_2)):
        for i, direction in enumerate(("up", "down", "left", "right")):
            parts.append(arrow_button(f"{state}arrow-{direction}", direction, i * (SB + 8), y, rings))
        y += SB + 8
    parts.append(hidden("hint-scrollbar-size", 0, y, SB, SB))
    return svg(col * (size + 16), y + SB + 4, "\n".join(parts))


def popup_background_svg(with_insets):
    size = 32
    opaque = [("#000000", "#000000")] * 4
    # Margin equals the 4px bevel: Plasma insets content by the margin hint, so a larger value
    # leaves a see-through ring between the frame and the items (seen on context menus).
    parts = [nine_slice("", 0, 0, size, 4, RAISED_4, flat, 4),
             nine_slice("mask-", size + 16, 0, size, 4, opaque, lambda px, py: "#000000", 4),
             nine_slice("shadow-", 2 * (size + 16), 0, size, 4, [("none", "none")] * 4, lambda px, py: "none", 0)]
    if with_insets:
        for side in ("top", "bottom", "left", "right"):
            parts.append(hidden(f"hint-{side}-inset", 0, size + 20, 0, 0))
    return svg(3 * (size + 16), size + 28, "\n".join(parts))


def line_svg():
    # classic etched separator: 1px shadow over 1px white.
    parts = [f'<g id="horizontal-line">{rect(0, 0, 32, 1, SHADOW)}{rect(0, 1, 32, 1, HILIGHT)}</g>',
             f'<g id="vertical-line">{rect(40, 0, 1, 32, SHADOW)}{rect(41, 0, 1, 32, HILIGHT)}</g>']
    return svg(48, 32, "\n".join(parts))


def heading_svg():
    size = 24
    clear = [("none", "none")] * 2
    parts = [nine_slice("header-", 0, 0, size, 2, clear, lambda px, py: "none", 2),
             nine_slice("footer-", size + 16, 0, size, 2, clear, lambda px, py: "none", 2)]
    return svg(2 * (size + 16), size + 12, "\n".join(parts))


def tooltip_svg():
    # Plasma's QML menus and tooltips draw "widgets/tooltip" (and "solid/widgets/tooltip") with a
    # "shadow" frame outside it. classic menus: 2px raised bevel, margin equal to the bevel, no shadow.
    size = 24
    none = [("none", "none"), ("none", "none")]
    parts = [nine_slice("", 0, 0, size, 2, RAISED_2, flat, 2),
             nine_slice("shadow-", size + 16, 0, size, 2, none, lambda px, py: "none", 0),
             nine_slice("mask-", 2 * (size + 16), 0, size, 2, [("#000000", "#000000")] * 2, lambda px, py: "#000000", 2)]
    return svg(3 * (size + 16), size + 12, "\n".join(parts))


if args.base:
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(args.base, OUT, symlinks=True)
    shutil.rmtree(OUT / "icons", ignore_errors=True)
    for stale in ("colors~", "metadata.desktop"):
        (OUT / stale).unlink(missing_ok=True)
    (OUT / "metadata.json").write_text("""{
  "KPackageStructure": "Plasma/Theme",
  "KPlugin": {
    "Authors": [{"Name": "Bending Unit 22"}],
    "Category": "Plasma Theme",
    "Description": "Chicago95 taskbar and widgets, built on React Plus",
    "Id": "Chicago95",
    "License": "GPL-2.0+",
    "Name": "Chicago95",
    "Version": "1.0"
  },
  "X-Plasma-API": "5.0"
}
""")
for folder in ("widgets", "dialogs", "solid/widgets", "solid/dialogs"):
    (OUT / folder).mkdir(parents=True, exist_ok=True)
(OUT / "widgets/tasks.svg").write_text(tasks_svg())
(OUT / "widgets/panel-background.svg").write_text(panel_svg())
(OUT / "widgets/viewitem.svg").write_text(viewitem_svg())
(OUT / "widgets/background.svg").write_text(popup_background_svg(True))
(OUT / "dialogs/background.svg").write_text(popup_background_svg(False))
(OUT / "widgets/line.svg").write_text(line_svg())
(OUT / "widgets/tooltip.svg").write_text(tooltip_svg())
(OUT / "solid/widgets/tooltip.svg").write_text(tooltip_svg())
(OUT / "solid/widgets/background.svg").write_text(popup_background_svg(True))
(OUT / "solid/dialogs/background.svg").write_text(popup_background_svg(False))
(OUT / "widgets/plasmoidheading.svg").write_text(heading_svg())
(OUT / "widgets/button.svg").write_text(button_svg())
(OUT / "widgets/lineedit.svg").write_text(lineedit_svg())
(OUT / "widgets/scrollbar.svg").write_text(scrollbar_svg())
print("wrote", OUT)
