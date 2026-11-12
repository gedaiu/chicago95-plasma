"""The Luna Plasma theme's controls: scroll bars, sliders, headings, frames, arrows, radio buttons, meters,
switches and the pager, each a few vector shapes.

The colours are measured from tests/references: the scroll bar from xpappearance.png (the list's bar at x 277..293, rows
264..377: track #F9F9F7 between #EEEDE5 lines, blue buttons and thumb #C5D5FC inside a white ring and a #7C9FD3 outline,
arrows #4D6185), the field and frame blue #7F9DB9 from the same screenshot; hover and pressed states follow the Luna
pictures of the B00merang Windows XP theme (a lighter body when hot, #9CBCE9 when pressed). A frame's pieces come from
frames.py; the other elements are groups placed below the frames.
"""

import sys

frames = sys.modules["luna_frames"]
primitives = sys.modules["luna_primitives"]
FrameSpec, frames_svg, strip_height = frames.FrameSpec, frames.frames_svg, frames.strip_height
hidden = primitives.hidden

WHITE, FACE, FIELD_BORDER, ARROW = "#FFFFFF", "#ECE9D8", "#7F9DB9", "#4D6185"
TRACK, TRACK_EDGE = "#F9F9F7", "#EEEDE5"
BLUE_RING = {"left": TRACK_EDGE, "right": "#9FB5D2", "top": "#7C9FD3", "bottom": "#7C9FD3"}
BLUE_BODY = {
    "normal": [(0, "#D0DDFC"), (2, "#C5D5FC"), (12, "#C3D3FD"), (16, "#B9C9F3")],
    "hover": [(0, "#E6EEFF"), (2, "#DCE7FE"), (12, "#D5E3F6"), (16, "#C4D5F5")],
    "pressed": [(0, "#A9C3EE"), (2, "#9CBCE9"), (12, "#98B8E8"), (16, "#8BADE3")],
}
BUTTON_SIZE = 17
THUMB_EDGE = 3
TAB_BORDER = "#919B9C"
HEADING_BORDER = "#ACA899"
CHECK_GREEN = ("#5CE05C", "#21A121")
RADIO_BORDER = "#1C5180"
PROGRESS_BORDER = "#686868"
SELECTION = "#316AC5"
HOT_BORDER = "#F5B700"
GROOVE_DARK = "#ACA899"


def sides(colour):
    return {side: colour for side in frames.SIDES}


def ring(left=None, right=None, top=None, bottom=None):
    return {"left": left, "right": right, "top": top, "bottom": bottom}


def square_spec(border, fill):
    return FrameSpec(10, 10, (1, 1, 1, 1), (0,) * 4, body=fill, rings=(sides(border),))


def track_spec(vertical):
    edge = TRACK_EDGE
    rings = (ring(edge, edge, TRACK, TRACK),) if vertical else (ring(TRACK, TRACK, edge, edge),)
    return FrameSpec(10, 10, (1, 1, 0, 0) if vertical else (0, 0, 1, 1), (0,) * 4, body=TRACK, rings=rings)


def thumb_spec(state):
    return FrameSpec(
        2 * THUMB_EDGE + 4,
        BUTTON_SIZE,
        (THUMB_EDGE,) * 4,
        (0,) * 4,
        radii=(2,) * 4,
        body=BLUE_BODY[state],
        rings=(BLUE_RING, sides(WHITE)),
    )


def arrow_glyph(turn):
    path = "M3.5 11.5L8.5 5.5L13.5 11.5H10.5L8.5 9L6.5 11.5Z"
    return f'<path d="{path}" fill="{ARROW}" transform="rotate({turn} 8.5 8.5)"/>'


def button_face(state):
    body = BLUE_BODY[state]
    gradient = (
        f'<linearGradient id="{state}-stepper" x2="0" y2="1"><stop offset="0" stop-color="{body[0][1]}"/>'
        f'<stop offset=".15" stop-color="{body[1][1]}"/><stop offset="1" stop-color="{body[-1][1]}"/></linearGradient>'
    )
    layers = (
        f'<rect width="1" height="17" fill="{TRACK_EDGE}"/>'
        f'<rect x="16" width="1" height="17" fill="{BLUE_RING["right"]}"/>'
        f'<rect x="1" width="15" height="17" fill="{WHITE}"/>'
        f'<rect x="2" y="1" width="13" height="15" rx="1" fill="url(#{state}-stepper)"/>'
    )
    return gradient, f'<g id="{state}-stepper-face">{layers}</g>'


def stepper_elements(strip_bottom):
    definitions, faces = zip(*(button_face(state) for state in BLUE_BODY), strict=True)
    parts = [f"<defs>{''.join(definitions)}</defs>", *faces]
    prefixes = {"arrow-": "normal", "mouseover-arrow-": "hover", "sunken-arrow-": "pressed"}
    for row, (prefix, state) in enumerate(prefixes.items()):
        for column, (name, turn) in enumerate({"up": 0, "down": 180, "left": 270, "right": 90}.items()):
            place = f"translate({column * 24} {strip_bottom + row * 24})"
            use = f'<use xlink:href="#{state}-stepper-face"/>'
            parts.append(f'<g id="{prefix}{name}" transform="{place}">{use}{arrow_glyph(turn)}</g>')
    parts.append(hidden("hint-scrollbar-size", 0, strip_bottom + 72, BUTTON_SIZE, BUTTON_SIZE))
    return "\n".join(parts)


def scrollbar_svg():
    specs = [
        ("background-vertical-", track_spec(True)),
        ("background-horizontal-", track_spec(False)),
        ("slider-", thumb_spec("normal")),
        ("mouseover-slider-", thumb_spec("hover")),
        ("sunken-slider-", thumb_spec("pressed")),
    ]
    bottom = strip_height(specs)
    return frames_svg(specs, stepper_elements(bottom), extra_height=3 * 24 + BUTTON_SIZE + 8)


def groove_spec(body):
    return FrameSpec(5, 4, (1, 1, 1, 1), (0,) * 4, body=body, rings=(ring(GROOVE_DARK, WHITE, GROOVE_DARK, WHITE),))


def slider_handle(element_id, border, top, bottom, y):
    gradient = (
        f'<linearGradient id="{element_id}-body" x2="0" y2="1"><stop offset="0" stop-color="{top}"/>'
        f'<stop offset="1" stop-color="{bottom}"/></linearGradient>'
    )
    layers = (
        f'<rect y="{y}" width="12" height="22" rx="2" fill="{border}"/>'
        f'<rect x="1" y="{y + 1}" width="10" height="20" rx="1" fill="url(#{element_id}-body)"/>'
    )
    return gradient, f'<g id="{element_id}">{layers}</g>'


def slider_svg():
    specs = [("groove-", groove_spec(FACE)), ("groove-highlight-", groove_spec("#C6D9F3"))]
    bottom = strip_height(specs)
    handles = [
        slider_handle("horizontal-slider-handle", TAB_BORDER, WHITE, "#D6D0C5", bottom),
        slider_handle("horizontal-slider-hover", SELECTION, WHITE, "#C6D9F3", bottom + 28),
    ]
    definitions, groups = zip(*handles, strict=True)
    extra = f"<defs>{''.join(definitions)}</defs>\n" + "\n".join(groups)
    extra += "\n" + hidden("hint-handle-size", 0, bottom + 56, 12, 22)
    return frames_svg(specs, extra, extra_height=82)


def heading_spec(header):
    border = ring(None, None, None, HEADING_BORDER) if header else ring(None, None, HEADING_BORDER, None)
    body = [(0, WHITE), (19, FACE)] if header else [(0, FACE), (19, WHITE)]
    return FrameSpec(10, 20, (1, 1, 1, 1), (2, 2, 2, 2), body=body, rings=(border,))


def plasmoidheading_svg():
    return frames_svg([("header-", heading_spec(True)), ("footer-", heading_spec(False))])


def frame_svg():
    return frames_svg([("plain-", FrameSpec(10, 10, (1, 1, 1, 1), (5,) * 4, rings=(sides(FIELD_BORDER),)))])


def arrow_triangle(element_id, points, x, y):
    return (
        f'<path id="{element_id}" d="M{points[0]}L{points[1]}L{points[2]}Z" fill="{ARROW}" '
        f'transform="translate({x} {y})"/>'
    )


def arrows_svg():
    triangles = {
        "up-arrow": ("0 4", "3.5 0", "7 4"),
        "down-arrow": ("0 0", "7 0", "3.5 4"),
        "left-arrow": ("4 0", "4 7", "0 3.5"),
        "right-arrow": ("0 0", "4 3.5", "0 7"),
    }
    parts = [arrow_triangle(name, points, 8 + 16 * index, 8) for index, (name, points) in enumerate(triangles.items())]
    return primitives.linked_svg(72, 24, "\n".join(parts))


def radio_element(element_id, border):
    gradient = (
        f'<radialGradient id="{element_id}-body" cx=".4" cy=".35" r=".8"><stop offset="0" stop-color="{WHITE}"/>'
        f'<stop offset="1" stop-color="#D6D0C5"/></radialGradient>'
    )
    circles = (
        f'<circle cx="6.5" cy="6.5" r="6.5" fill="{border}"/>'
        f'<circle cx="6.5" cy="6.5" r="5.5" fill="url(#{element_id}-body)"/>'
    )
    return gradient, circles


def radiobutton_svg():
    normal, normal_circles = radio_element("normal", RADIO_BORDER)
    hover, hover_circles = radio_element("hover", HOT_BORDER)
    symbol = (
        f'<radialGradient id="symbol-body" cx=".4" cy=".35" r=".8"><stop offset="0" stop-color="{CHECK_GREEN[0]}"/>'
        f'<stop offset="1" stop-color="{CHECK_GREEN[1]}"/></radialGradient>'
    )
    parts = [
        f"<defs>{normal}{hover}{symbol}</defs>",
        hidden("hint-size", 0, 32, 15, 15),
        f'<g id="normal" transform="translate(1 1)">{normal_circles}</g>',
        f'<g id="hover" transform="translate(17 1)">{hover_circles}</g>',
        '<circle id="symbol" cx="6.5" cy="22" r="2.5" fill="url(#symbol-body)"/>',
    ]
    return primitives.linked_svg(32, 48, "\n".join(parts))


def meter_specs():
    inactive = FrameSpec(
        10,
        15,
        (2, 2, 2, 2),
        (0,) * 4,
        radii=(2,) * 4,
        body=WHITE,
        rings=(sides(PROGRESS_BORDER), sides(WHITE)),
    )
    chunk = [(0, "#D0F8C8"), (3, "#4BD94B"), (9, "#25BD25"), (14, "#B8F0B0")]
    active = FrameSpec(
        10, 15, (2, 2, 2, 2), (0,) * 4, radii=(2,) * 4, body=chunk, rings=(sides(WHITE), sides("#8EE88E"))
    )
    return [("bar-inactive-", inactive), ("bar-active-", active)]


def bar_meter_svg():
    specs = meter_specs()
    return frames_svg(specs, hidden("hint-bar-size", 0, strip_height(specs), 15, 15), extra_height=15)


def switch_groove(fill, border):
    return FrameSpec(24, 16, (8, 8, 8, 8), (0,) * 4, radii=(8, 8, 8, 8), body=fill, rings=(sides(border),))


def switch_handle(element_id, x, fill):
    gradient = (
        f'<linearGradient id="{element_id}-body" x2="0" y2="1"><stop offset="0" stop-color="{WHITE}"/>'
        f'<stop offset="1" stop-color="{fill}"/></linearGradient>'
    )
    circles = (
        f'<circle cx="{x + 9}" cy="9" r="9" fill="{FIELD_BORDER}"/>'
        f'<circle cx="{x + 9}" cy="9" r="8" fill="url(#{element_id}-body)"/>'
    )
    return gradient, f'<g id="{element_id}">{circles}</g>'


def switch_svg():
    specs = [("inactive-", switch_groove(FACE, FIELD_BORDER)), ("active-", switch_groove("#3C81F3", "#0C2E85"))]
    bottom = strip_height(specs)
    handles = [switch_handle("handle", 0, "#D6D0C5"), switch_handle("handle-hover", 20, "#C6D9F3")]
    pressed = switch_handle("handle-pressed", 40, "#ACA899")
    definitions, groups = zip(*handles, pressed, strict=True)
    shadow = '<circle id="handle-shadow" cx="70" cy="10" r="10" fill="#000000" fill-opacity=".2"/>'
    extra = f"<defs>{''.join(definitions)}</defs>\n" + "\n".join(
        group.replace("<g id", f'<g transform="translate(0 {bottom})" id', 1) for group in groups
    )
    extra += "\n" + shadow.replace('cy="10"', f'cy="{bottom + 10}"')
    extra += "\n" + hidden("hint-bar-size", 0, bottom + 24, 36, 16)
    return frames_svg(specs, extra, extra_height=44)


def pager_svg():
    specs = [
        ("normal-", square_spec(FIELD_BORDER, FACE)),
        ("active-", square_spec(SELECTION, "#C6D9F3")),
        ("hover-", square_spec(HOT_BORDER, WHITE)),
    ]
    return frames_svg(specs)


GENERATED = {
    "widgets/scrollbar.svg": scrollbar_svg,
    "widgets/slider.svg": slider_svg,
    "widgets/plasmoidheading.svg": plasmoidheading_svg,
    "widgets/frame.svg": frame_svg,
    "widgets/arrows.svg": arrows_svg,
    "widgets/radiobutton.svg": radiobutton_svg,
    "widgets/bar_meter_horizontal.svg": bar_meter_svg,
    "widgets/switch.svg": switch_svg,
    "widgets/pager.svg": pager_svg,
}
