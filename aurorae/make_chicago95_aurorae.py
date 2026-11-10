from pathlib import Path

from bevel import DARK, FACE, HILIGHT, LIGHT, RAISED_4, SHADOW, rect, ring_color, run_length_rows, svg

OUT = Path.home() / ".local/share/aurorae/themes/Chicago95"
OUT.mkdir(parents=True, exist_ok=True)

ACTIVE_TITLE, INACTIVE_TITLE = "#000080", "#808080"
BORDER, TITLE_H = 4, 21
TOP_H = BORDER + TITLE_H
BTN_W, BTN_H = 18, 16
GLYPH_OFF_X, GLYPH_OFF_Y = (BTN_W - 18) // 2, (BTN_H - 16) // 2
FRAME = 64


def frame_pieces(prefix, title_color, x0):
    def color(px, py):
        def interior(ix, iy):
            return title_color if BORDER <= iy < TOP_H else FACE
        return ring_color(px, py, FRAME, RAISED_4, interior)

    def piece(name, fx, fy, w, h):
        body = run_length_rows(x0 + fx, fy, w, h, lambda cx, cy: color(fx + cx, fy + cy))
        return f'<g id="{prefix}{name}">{body}</g>'

    b, s = BORDER, FRAME
    return "\n".join([
        piece("topleft", 0, 0, b, TOP_H),
        piece("top", b, 0, s - 2 * b, TOP_H),
        piece("topright", s - b, 0, b, TOP_H),
        piece("left", 0, TOP_H, b, s - TOP_H - b),
        piece("right", s - b, TOP_H, b, s - TOP_H - b),
        piece("bottomleft", 0, s - b, b, b),
        piece("bottom", b, s - b, s - 2 * b, b),
        piece("bottomright", s - b, s - b, b, b),
        piece("center", b, TOP_H, s - 2 * b, s - TOP_H - b),
    ])


(OUT / "decoration.svg").write_text(svg(
    2 * FRAME + 8, FRAME,
    frame_pieces("decoration-", ACTIVE_TITLE, 0) + "\n" + frame_pieces("decoration-inactive-", INACTIVE_TITLE, FRAME + 8)))


def button_face(pressed):
    tl1, br1, tl2, br2 = (DARK, HILIGHT, SHADOW, LIGHT) if pressed else (HILIGHT, DARK, LIGHT, SHADOW)
    w, h = BTN_W, BTN_H
    return (rect(0, 0, w, h, FACE)
            + rect(0, 0, w, 1, tl1) + rect(0, 0, 1, h, tl1)
            + rect(0, h - 1, w, 1, br1) + rect(w - 1, 0, 1, h, br1)
            + rect(1, 1, w - 2, 1, tl2) + rect(1, 1, 1, h - 2, tl2)
            + rect(1, h - 2, w - 2, 1, br2) + rect(w - 2, 1, 1, h - 2, br2))


def glyph(kind, color, dx=0, dy=0):
    def r(x, y, w, h):
        return rect(x + dx + GLYPH_OFF_X, y + dy + GLYPH_OFF_Y, w, h, color)
    if kind == "close":
        return "".join(r(5 + i, 3 + i, 2, 1) + r(11 - i, 3 + i, 2, 1) for i in range(7))
    if kind == "minimize":
        return r(5, 10, 6, 2)
    if kind == "maximize":
        return r(4, 3, 10, 2) + r(4, 3, 1, 9) + r(13, 3, 1, 9) + r(4, 11, 10, 1)
    if kind == "restore":
        return (r(6, 3, 8, 2) + r(13, 3, 1, 6) + r(11, 8, 3, 1)
                + r(4, 6, 7, 2) + r(4, 6, 1, 7) + r(10, 6, 1, 7) + r(4, 12, 7, 1))
    if kind == "help":
        return (r(6, 3, 5, 1) + r(5, 4, 2, 2) + r(10, 4, 2, 2) + r(9, 6, 2, 1)
                + r(8, 7, 2, 2) + r(8, 11, 2, 2))
    if kind == "alldesktops":
        return r(8, 3, 2, 3) + r(5, 6, 8, 2) + r(6, 8, 6, 1) + r(8, 9, 2, 4)
    if kind == "keepabove":
        return r(8, 3, 2, 2) + r(6, 5, 6, 2) + r(4, 7, 10, 2) + r(5, 10, 8, 2)
    if kind == "keepbelow":
        return r(5, 3, 8, 2) + r(4, 6, 10, 2) + r(6, 8, 6, 2) + r(8, 10, 2, 2)
    if kind == "shade":
        return r(4, 4, 10, 2) + r(4, 7, 10, 2)
    raise ValueError(kind)


CLOSE_GAP = 2


def button_svg(kind):
    gap = CLOSE_GAP if kind == "close" else 0
    states = {
        "active-center": (False, DARK, 0),
        "hover-center": (False, DARK, 0),
        "pressed-center": (True, DARK, 1),
        "deactivated-center": (False, SHADOW, 0),
        "inactive-center": (False, DARK, 0),
        "hover-inactive-center": (False, DARK, 0),
        "pressed-inactive-center": (True, DARK, 1),
        "deactivated-inactive-center": (False, SHADOW, 0),
    }
    groups = []
    for idx, (element_id, (pressed, color, shift)) in enumerate(states.items()):
        body = button_face(pressed) + glyph(kind, color, shift, shift)
        if color == SHADOW:
            body += glyph(kind, HILIGHT, 1, 1) + glyph(kind, SHADOW, 0, 0)
        cell = BTN_W + gap + 4
        groups.append(f'<g id="{element_id}" transform="translate({idx * cell},0)">'
                      f'{rect(0, 0, gap + BTN_W, BTN_H, "none")}<g transform="translate({gap},0)">{body}</g></g>')
    return svg(len(states) * (BTN_W + gap + 4), BTN_H, "\n".join(groups))


for name in ["close", "minimize", "maximize", "restore", "help", "alldesktops", "keepabove", "keepbelow", "shade"]:
    (OUT / f"{name}.svg").write_text(button_svg(name))

(OUT / "Chicago95rc").write_text(f"""[General]
ActiveTextColor=255,255,255,255
InactiveTextColor=192,192,192,255
TitleAlignment=Left
TitleVerticalAlignment=Center
Animation=0
Shadow=false
UseTextShadow=false
HaloActive=false
HaloInactive=false

[Layout]
TitleHeight={TITLE_H}
TitleEdgeTop={BORDER}
TitleEdgeBottom=0
TitleEdgeLeft={BORDER}
TitleEdgeRight={BORDER + 2}
TitleEdgeTopMaximized=0
TitleEdgeBottomMaximized=0
TitleEdgeLeftMaximized=0
TitleEdgeRightMaximized=0
TitleBorderLeft=6
TitleBorderRight=2
ButtonHeight={BTN_H}
ButtonWidth={BTN_W}
ButtonWidthMenu=18
ButtonWidthClose={BTN_W + CLOSE_GAP}
ButtonSpacing=0
ButtonMarginTop=3
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
