"""Builds the Chicago95 window decoration (Aurorae SVG theme).

    make_chicago95_aurorae.py [--out DIR] [--active "#000080,#1084D0"] [--inactive "#808080,#C0C0C0"]
                              [--inactive-text "#C0C0C0"] [--face C] [--light C] [--shadow C] [--dark C]

A title colour is one colour (solid, like the 1995 desktop) or two separated by a comma
(a left-to-right gradient, like 1998). The bevel colours default to the 1995 and 1998 greys; the 2000
look passes its own (light = the face, #808080 and #404040 shadows). chicago95-sync-colors runs this
with the colour scheme's colours.

The sizes are the originals' (tests/test_window_reference.py): a 4px frame, an 18px title, 16x14
caption buttons 2px below its top, minimize and maximize side by side, close 2px further right and 2px
in from the title's end, the window icon 16px square 1px below the title's top.
"""

import argparse
from pathlib import Path

from bevel import rect, ring_color, run_length_rows, svg

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--out", type=Path, default=Path.home() / ".local/share/aurorae/themes/Chicago95")
parser.add_argument("--active", default="#000080", help="active title colour, or start,end for a gradient")
parser.add_argument("--inactive", default="#808080", help="inactive title colour, or start,end for a gradient")
parser.add_argument("--inactive-text", default="#C0C0C0", help="inactive title text colour")
parser.add_argument("--face", default="#C0C0C0")
parser.add_argument("--light", default="#DFDFDF", help="the outer light line (the face itself on 2000)")
parser.add_argument("--shadow", default="#808080")
parser.add_argument("--dark", default="#000000", help="the outer shadow line (#404040 on 2000)")
parser.add_argument(
    "--gradient-margins",
    default="0,0",
    help="LEFT,RIGHT: pixels at each end of the title that keep the end colours (2000: 18,52, the icon and the buttons)",
)
args = parser.parse_args()

OUT = args.out
OUT.mkdir(parents=True, exist_ok=True)

FACE, LIGHT, SHADOW, DARK, HILIGHT = args.face, args.light, args.shadow, args.dark, "#FFFFFF"
GLYPH = "#000000"  # black on every look, even where the frame's outer shadow is #404040
RAISED_4 = [(LIGHT, DARK), (HILIGHT, SHADOW), (FACE, FACE), (FACE, FACE)]
ACTIVE_TITLE, INACTIVE_TITLE = args.active.split(","), args.inactive.split(",")
TITLE_FILL = "TITLE-FILL"
BORDER, TITLE_H = 4, 18
TOP_H = BORDER + TITLE_H
# A button is 16 wide and 16 tall, like the window icon beside it, with the 14px face drawn 1px down.
BTN_W, BTN_H, FACE_H = 16, 16, 14
FRAME = 64


# The title stretches with the window, so a gradient's end margins are placed for a typical title
# (TYPICAL_TITLE pixels wide); within a few colour levels of exact for other widths.
TYPICAL_TITLE = 442
MARGIN_LEFT, MARGIN_RIGHT = (int(value) for value in args.gradient_margins.split(","))


def title_paint(prefix, colors):
    """(defs, fill) for the title band: a plain colour, or a gradient across the band."""
    if len(colors) == 1:
        return "", colors[0]
    gradient_id = f"{prefix}title-gradient"
    start, end = MARGIN_LEFT / TYPICAL_TITLE, 1 - MARGIN_RIGHT / TYPICAL_TITLE
    stops = "".join(
        f'<stop offset="{start + (end - start) * index / (len(colors) - 1):g}" stop-color="{color}"/>'
        for index, color in enumerate(colors)
    )
    return (
        f'<defs><linearGradient id="{gradient_id}" x1="0" y1="0" x2="1" y2="0">{stops}</linearGradient></defs>',
        f"url(#{gradient_id})",
    )


def frame_pieces(prefix, title_colors, x0):
    defs, title_fill = title_paint(prefix, title_colors)

    def color(px, py):
        def interior(ix, iy):
            return TITLE_FILL if BORDER <= iy < TOP_H else FACE

        return ring_color(px, py, FRAME, RAISED_4, interior)

    def piece(name, fx, fy, w, h):
        body = run_length_rows(x0 + fx, fy, w, h, lambda cx, cy: color(fx + cx, fy + cy))
        return f'<g id="{prefix}{name}">{body.replace(TITLE_FILL, title_fill)}</g>'

    b, s = BORDER, FRAME
    return defs + "\n".join(
        [
            piece("topleft", 0, 0, b, TOP_H),
            piece("top", b, 0, s - 2 * b, TOP_H),
            piece("topright", s - b, 0, b, TOP_H),
            piece("left", 0, TOP_H, b, s - TOP_H - b),
            piece("right", s - b, TOP_H, b, s - TOP_H - b),
            piece("bottomleft", 0, s - b, b, b),
            piece("bottom", b, s - b, s - 2 * b, b),
            piece("bottomright", s - b, s - b, b, b),
            piece("center", b, TOP_H, s - 2 * b, s - TOP_H - b),
            # KWin repeats the edges at their own size unless told to stretch them: the title's gradient
            # must run once across the whole band.
            f'<rect id="{prefix}hint-stretch-borders" x="{x0}" y="0" width="1" height="1" fill="none"/>',
        ]
    )


(OUT / "decoration.svg").write_text(
    svg(
        2 * FRAME + 8,
        FRAME,
        frame_pieces("decoration-", ACTIVE_TITLE, 0)
        + "\n"
        + frame_pieces("decoration-inactive-", INACTIVE_TITLE, FRAME + 8),
    )
)


def button_face(pressed):
    tl1, br1, tl2, br2 = (DARK, HILIGHT, SHADOW, LIGHT) if pressed else (HILIGHT, DARK, LIGHT, SHADOW)
    w, h, y = BTN_W, FACE_H, BTN_H - FACE_H - 1
    return (
        rect(0, y, w, h, FACE)
        + rect(0, y, w, 1, tl1)
        + rect(0, y, 1, h, tl1)
        + rect(0, y + h - 1, w, 1, br1)
        + rect(w - 1, y, 1, h, br1)
        + rect(1, y + 1, w - 2, 1, tl2)
        + rect(1, y + 1, 1, h - 2, tl2)
        + rect(1, y + h - 2, w - 2, 1, br2)
        + rect(w - 2, y + 1, 1, h - 2, br2)
    )


# Glyphs as (x, y, width, height) runs on the 16x14 face, measured from the originals' buttons.
GLYPHS = {
    "close": [
        (4, 3, 2, 1),
        (10, 3, 2, 1),
        (5, 4, 2, 1),
        (9, 4, 2, 1),
        (6, 5, 4, 1),
        (7, 6, 2, 1),
        (6, 7, 4, 1),
        (5, 8, 2, 1),
        (9, 8, 2, 1),
        (4, 9, 2, 1),
        (10, 9, 2, 1),
    ],
    "minimize": [(4, 9, 6, 2)],
    "maximize": [(3, 2, 9, 2), (3, 2, 1, 9), (11, 2, 1, 9), (3, 10, 9, 1)],
    "restore": [(5, 1, 6, 2), (10, 1, 1, 6), (8, 6, 3, 1), (2, 4, 6, 2), (2, 4, 1, 6), (7, 4, 1, 6), (2, 9, 6, 1)],
    "help": [(6, 2, 4, 1), (5, 3, 2, 2), (9, 3, 2, 2), (8, 5, 2, 1), (7, 6, 2, 2), (7, 9, 2, 2)],
    "alldesktops": [(7, 2, 2, 3), (4, 5, 8, 2), (5, 7, 6, 1), (7, 8, 2, 4)],
    "keepabove": [(7, 2, 2, 2), (5, 4, 6, 2), (3, 6, 10, 2), (4, 9, 8, 2)],
    "keepbelow": [(4, 2, 8, 2), (3, 5, 10, 2), (5, 7, 6, 2), (7, 9, 2, 2)],
    "shade": [(3, 3, 10, 2), (3, 6, 10, 2)],
}


def glyph(kind, color, dx=0, dy=0):
    top = BTN_H - FACE_H - 1
    return "".join(rect(x + dx, top + y + dy, w, h, color) for x, y, w, h in GLYPHS[kind])


CLOSE_GAP = 2


def button_svg(kind):
    gap = CLOSE_GAP if kind == "close" else 0
    states = {
        "active-center": (False, GLYPH, 0),
        "hover-center": (False, GLYPH, 0),
        "pressed-center": (True, GLYPH, 1),
        "deactivated-center": (False, SHADOW, 0),
        "inactive-center": (False, GLYPH, 0),
        "hover-inactive-center": (False, GLYPH, 0),
        "pressed-inactive-center": (True, GLYPH, 1),
        "deactivated-inactive-center": (False, SHADOW, 0),
    }
    groups = []
    for idx, (element_id, (pressed, color, shift)) in enumerate(states.items()):
        body = button_face(pressed)
        if color == SHADOW:  # disabled: an etched glyph, white under grey
            body += glyph(kind, HILIGHT, 1, 1)
        body += glyph(kind, color, shift, shift)
        cell = BTN_W + gap + 4
        groups.append(
            f'<g id="{element_id}" transform="translate({idx * cell},0)">'
            f'{rect(0, 0, gap + BTN_W, BTN_H, "none")}<g transform="translate({gap},0)">{body}</g></g>'
        )
    return svg(len(states) * (BTN_W + gap + 4), BTN_H, "\n".join(groups))


for name in ["close", "minimize", "maximize", "restore", "help", "alldesktops", "keepabove", "keepbelow", "shade"]:
    (OUT / f"{name}.svg").write_text(button_svg(name))

# KWin centres the caption in a box TitleEdgeTop down and TitleHeight tall: a pixel lower and shorter
# than the title band puts it on the originals' rows, with the buttons where they were (TitleEdgeTop +
# ButtonMarginTop). It starts a pixel after the icon's gap (TitleBorderLeft), where the originals' font
# begins most capitals; tests/test_plasma_window_reference.py.
(OUT / "Chicago95rc").write_text(f"""[General]
ActiveTextColor=255,255,255,255
InactiveTextColor={",".join(str(int(args.inactive_text.lstrip("#")[i : i + 2], 16)) for i in (0, 2, 4))},255
TitleAlignment=Left
TitleVerticalAlignment=Center
Animation=0
Shadow=false
UseTextShadow=false
HaloActive=false
HaloInactive=false

[Layout]
TitleHeight={TITLE_H - 1}
TitleEdgeTop={BORDER + 1}
TitleEdgeBottom=0
TitleEdgeLeft={BORDER + 2}
TitleEdgeRight={BORDER + 2}
TitleEdgeTopMaximized=0
TitleEdgeBottomMaximized=0
TitleEdgeLeftMaximized=0
TitleEdgeRightMaximized=0
TitleBorderLeft=3
TitleBorderRight=2
ButtonHeight={BTN_H}
ButtonWidth={BTN_W}
ButtonWidthMenu={BTN_W}
ButtonWidthClose={BTN_W + CLOSE_GAP}
ButtonSpacing=0
ButtonMarginTop=0
ExplicitButtonSpacer=4
BorderLeft={BORDER}
BorderRight={BORDER}
BorderBottom={BORDER}
PaddingTop=0
PaddingBottom=0
PaddingLeft=0
PaddingRight=0
""")

(OUT / "metadata.json").write_text("""{
  "KPlugin": {
    "Authors": [{"Name": "Bending Unit 22"}],
    "Id": "Chicago95",
    "License": "GPL-3.0",
    "Name": "Chicago95",
    "Description": "Chicago95 window decoration",
    "Version": "1.0"
  }
}
""")
print("wrote", sorted(p.name for p in OUT.iterdir()))
