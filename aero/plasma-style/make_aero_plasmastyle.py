#!/usr/bin/env python3
"""Builds the Chicago95Aero Plasma style: the Windows 7 superbar's glass and its task buttons.

usage: python3 aero/plasma-style/make_aero_plasmastyle.py [--out DIR]

With compositing Plasma draws the panel from translucent/widgets/panel-background.svg and blurs behind its mask, as
DWM blurred behind the taskbar; without it, widgets/panel-background.svg is the same bar over the references'
desktop. The task buttons are vector faces fitted to aero.msstyles' TASKITEM (stops.py, written by
tests/aero/fit_aero_stops.py) and drawn with the decoration's face model.
"""

import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


palette = load("aero_palette", HERE.parent / "palette.py")
stops = load("aero_plasma_stops", HERE / "stops.py")
traybutton = load("aero_tray_button", HERE / "traybutton.py")
orb = load("aero_orb", HERE / "orb.py")
tray_shade = load("aero_tray_shade", HERE / "trayshade.py")
reflection = load("aero_reflection", HERE.parent / "reflection.py")
faces = load("aero_faces", HERE.parent / "aurorae/make_aero_aurorae.py")

PANEL_WIDTH = 10
GAP = 8
METADATA = {
    "KPlugin": {
        "Authors": [{"Name": "Bending Unit 22"}],
        "Description": "Chicago95 Windows 7 Aero superbar",
        "Id": "Chicago95Aero",
        "License": "GPL-3.0",
        "Name": "Chicago95 Aero",
        "Version": "1.0",
    },
    "X-Plasma-API": "5.0",
}


def rgb(colour):
    return bytes.fromhex(colour[1:])


def hex_colour(channels):
    return "#" + "".join(f"{min(255, max(0, round(channel))):02X}" for channel in channels)


def solved_fill(seen, alpha):
    """The fill that, drawn at alpha over the references' desktop, shows as seen there."""
    desktop, opacity = rgb(palette.REFERENCE_DESKTOP), alpha / 255
    return hex_colour((s - d * (1 - opacity)) / opacity for s, d in zip(rgb(seen), desktop, strict=True))


def over(top, bottom):
    """A translucent colour drawn over another, as one colour and alpha."""
    (top_colour, top_alpha), (bottom_colour, bottom_alpha) = top, bottom
    a, b = top_alpha / 255, bottom_alpha / 255
    alpha = a + b * (1 - a)
    colour = hex_colour(
        (t * a + u * b * (1 - a)) / alpha for t, u in zip(rgb(top_colour), rgb(bottom_colour), strict=True)
    )
    return colour, round(alpha * 255)


def bar_rows(translucent):
    """The bar's 40 rows as (colour, alpha): over whatever lies behind, or as the references show it."""
    _, glass_alpha = palette.GLASS["active"]
    edge = list(palette.TASKBAR_EDGE)
    if translucent:  # the edge lines are drawn over the streaks, as DWM draws them (bar_edge_svg)
        glass = [(solved_fill(seen, glass_alpha), glass_alpha) for seen in palette.TASKBAR_GLASS]
        return [glass[0]] * len(edge) + glass
    behind = palette.TASKBAR_GLASS[0]
    blended = [
        hex_colour(c * a / 255 + b * (1 - a / 255) for c, b in zip(rgb(colour), rgb(behind), strict=True))
        for colour, a in edge
    ]
    return [(colour, 255) for colour in blended + list(palette.TASKBAR_GLASS)]


def hint_margins(prefix):
    dash = f"{prefix}-" if prefix else ""
    return "".join(
        f'<rect id="{dash}hint-{side}-margin" x="0" y="0" width="0" height="0" fill="none"/>'
        for side in ("top", "bottom", "left", "right")
    )


def panel_svg(translucent):
    rows = bar_rows(translucent)
    height = len(rows)
    gradient = faces.vertical_gradient("bar", rows)
    mask = (
        f'<rect id="mask-center" x="{PANEL_WIDTH + GAP}" y="0" width="{PANEL_WIDTH}" height="{height}"/>'
        + hint_margins("mask")
        if translucent
        else ""
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{2 * PANEL_WIDTH + GAP}" height="{height}">'
        f"<defs>{gradient}</defs>"
        f'<rect id="center" x="0" y="0" width="{PANEL_WIDTH}" height="{height}" fill="url(#bar)"/>'
        f"{hint_margins('')}{mask}</svg>\n"
    )


def row_gradient(gradient_id, row, x0):
    """One row's colours across the face's inner columns, from x0."""
    return (
        f'<linearGradient id="{gradient_id}" x1="{x0}" y1="0" x2="{x0 + len(row)}" y2="0" '
        f'gradientUnits="userSpaceOnUse">{faces.held_stops(row, lambda value: faces.paint(*value))}</linearGradient>'
    )


def glossy_face_markup(face, prefix, origin):
    """A superbar button face: each inner row's base colour, a white gloss over its top left bounded by a quadratic
    curve and fading out from an elliptical highlight, the face's top and bottom rows across, and its edge columns
    down."""
    number = faces.number
    width, height = face["size"]
    edge, top, bottom = len(face["left"]), len(face["top"]), len(face["bottom"])
    x0, y0 = origin
    inner_left, inner_right = x0 + edge, x0 + width - edge
    gloss = face["gloss"]
    (start, curve_x, curve_y, end), (centre_x, centre_y), (radius_x, radius_y) = (
        gloss["curve"],
        gloss["centre"],
        gloss["radii"],
    )
    base = "".join(
        f'<stop offset="{number(round((top + edge_row) / height, 4))}" {faces.paint(*colour)}/>'
        for row, colour in enumerate(face["rows"])
        for edge_row in (row, row + 1)
    )
    definitions = [
        f'<linearGradient id="{prefix}b" x1="0" y1="{y0}" x2="0" y2="{y0 + height}" gradientUnits="userSpaceOnUse">'
        f"{base}</linearGradient>",
        f'<radialGradient id="{prefix}g" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" '
        f'gradientTransform="translate({number(x0 + centre_x)} {number(y0 + centre_y)}) '
        f'scale({number(radius_x)} {number(radius_y)})">'
        + "".join(
            f'<stop offset="{offset}" stop-color="#FFFFFF" stop-opacity="{number(opacity)}"/>'
            for offset, opacity in zip((0, 0.5, 1), gloss["opacity"], strict=True)
        )
        + "</radialGradient>",
    ]
    shapes = [
        f'<rect x="{inner_left}" y="{y0 + top}" width="{inner_right - inner_left}" '
        f'height="{height - top - bottom}" fill="url(#{prefix}b)"/>',
        f'<path d="M{inner_left},{y0 + top}H{inner_right}V{number(y0 + end)}'
        f'Q{number(x0 + curve_x)},{number(y0 + curve_y)} {inner_left},{number(y0 + start)}z" fill="url(#{prefix}g)"/>',
    ]
    for index, (row, y) in enumerate(
        [(row, y0 + y) for y, row in enumerate(face["top"])]
        + [(row, y0 + height - bottom + y) for y, row in enumerate(face["bottom"])]
    ):
        definitions.append(row_gradient(f"{prefix}h{index}", row, inner_left))
        shapes.append(
            f'<rect x="{inner_left}" y="{y}" width="{inner_right - inner_left}" height="1" '
            f'fill="url(#{prefix}h{index})"/>'
        )
    for side, offset in (("left", 0), ("right", width - edge)):
        for index, column in enumerate(face[side]):
            gradient_id = f"{prefix}{side[0]}{index}"
            definitions.append(faces.vertical_gradient(gradient_id, column))
            shapes.append(
                f'<rect x="{x0 + offset + index}" y="{y0}" width="1" height="{height}" fill="url(#{gradient_id})"/>'
            )
    return "".join(definitions), "".join(shapes)


def glossy_face_svg(face):
    width, height = face["size"]
    definitions, shapes = glossy_face_markup(face, "f", (0, 0))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f"<defs>{definitions}</defs>{shapes}</svg>"
    )


def task_face_svg(state):
    return glossy_face_svg(stops.TASK_FACES[state])


def group_face_svg(state):
    return faces.face_svg(stops.GROUP_FACES[state])


def show_desktop_face_svg(state):
    return faces.face_svg(stops.SHOW_DESKTOP_FACES[state])


def faces_svg(faces_by_state, markup=faces.face_markup):
    """Each state's face as the centre of a frame without borders, laid out side by side."""
    definitions, groups = [], []
    width, height = next(iter(faces_by_state.values()))["size"]
    for index, (state, face) in enumerate(faces_by_state.items()):
        face_definitions, shapes = markup(face, f"t{index}", (index * (width + GAP), 0))
        definitions.append(face_definitions)
        groups.append(f'<g id="{state}-center">{shapes}</g>{hint_margins(state)}')
    total = len(faces_by_state) * (width + GAP)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="{height}">'
        f"<defs>{''.join(definitions)}</defs>\n" + "\n".join(groups) + "\n</svg>\n"
    )


def tasks_svg():
    """The superbar's buttons are 60 by 40, the TASKITEM states as they are."""
    return faces_svg(stops.TASK_FACES, glossy_face_markup)


# The Start orb's sphere, 38 pixels across at (27, 20) in a 58 by 40 bar slot (win7dragedge.png's at x 27,
# y 748): a navy body darkening outwards, cyan light pooling at its foot, a white gloss over its upper half, and a
# rim of white glass; outside the logo the glass is orb.py's fitted shell. The program logo Setup chose is laid
# over its middle, never drawn here.
ORB = {"centre": (27, 20)}
ORB_BODY = (("#1590CB", 0), ("#0063A1", 0.07), ("#083E6C", 0.16), ("#024973", 1))
ORB_GLOW = (("#03E5FF", 1), ("#1DBCFF", 0.6), ("#0094FF", 0))
ORB_GLOSS = (("#FFFFFF", 0.88), ("#FFFFFF", 0))
ORB_GLOSS_SHAPE = {"chord": -0.5, "sag": 7, "fade": 0}  # the cap ends this far above the centre, bowing down
# this far; its white fades out this far below the centre
ORB_GLOW_SHAPE = {"drop": 15, "radius": 18}  # where the cyan light pools below the centre, and how far it spreads
ORB_RIM = {"inner": 18, "outer": 19, "opacity": 0.3}  # white glass round the body: the bar shows through it


def gloss_path(cx, cy, radius):
    """The gloss: the body's upper arc, closed by a curve bowing down between its ends, so it stays on the body."""
    chord, sag = ORB_GLOSS_SHAPE["chord"], ORB_GLOSS_SHAPE["sag"]
    half = (radius**2 - chord**2) ** 0.5
    number = faces.number
    left, right, y = number(round(cx - half, 3)), number(round(cx + half, 3)), number(cy - chord)
    return (
        f"M{left},{y}A{number(radius)},{number(radius)} 0 0 1 {right},{y}"
        f"Q{number(cx)},{number(cy - chord + 2 * sag)} {left},{y}z"
    )


def shell_markup(cx, cy):
    """Glass rings catch the same overhead light on the left and right of the sphere."""
    defs, shapes = [], []
    for index, colours in enumerate(orb.SHELL):
        radius = orb.SHELL_FROM + (index + 0.5) * orb.RING_WIDTH
        stops = []
        for sector in range(-orb.SECTORS // 4, orb.SECTORS // 4):
            angle = (sector + 0.5) * math.tau / orb.SECTORS
            offset = (1 + math.sin(angle)) / 2
            right = colours[sector % orb.SECTORS]
            left = colours[(orb.SECTORS // 2 - 1 - sector) % orb.SECTORS]
            colour = "#" + "".join(f"{(int(right[i:i+2],16) + int(left[i:i+2],16)) // 2:02x}" for i in (1,3,5))
            stops.append(f'<stop offset="{offset:.5f}" stop-color="{colour}"/>')
        defs.append(f'<linearGradient id="shell{index}" x1="0" x2="0" y1="{cy-radius}" y2="{cy+radius}" '
                    f'gradientUnits="userSpaceOnUse">{"".join(stops)}</linearGradient>')
        rings = []
        for edge in (radius - orb.RING_WIDTH / 2, radius + orb.RING_WIDTH / 2):
            rings.append(f"M{cx-edge},{cy}a{edge},{edge} 0 1 0 {2*edge},0a{edge},{edge} 0 1 0 {-2*edge},0z")
        shapes.append(f'<path fill-rule="evenodd" d="{"".join(rings)}" fill="url(#shell{index})"/>')
    return "".join(defs), "".join(shapes)


def orb_svg():
    (cx, cy) = ORB["centre"]
    radius = ORB_RIM["inner"]
    rim_width = ORB_RIM["outer"] - ORB_RIM["inner"]
    shell_definitions, shell_shapes = shell_markup(cx, cy)
    number = faces.number
    body = "".join(f'<stop offset="{number(round(offset, 3))}" stop-color="{colour}"/>' for colour, offset in ORB_BODY)
    glow = "".join(
        f'<stop offset="{number(offset)}" stop-color="{colour}" stop-opacity="{number(opacity)}"/>'
        for (colour, opacity), offset in zip(ORB_GLOW, (0, 0.5, 1), strict=True)
    )
    gloss = "".join(
        f'<stop offset="{number(offset)}" stop-color="{colour}" stop-opacity="{number(opacity)}"/>'
        for (colour, opacity), offset in zip(ORB_GLOSS, (0, 1), strict=True)
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="58" height="40"><defs>'
        f'<radialGradient id="orb-body" cx="{number(cx)}" cy="{number(cy)}" r="{number(radius)}" '
        f'gradientUnits="userSpaceOnUse">{body}</radialGradient>'
        f'<radialGradient id="orb-glow" cx="{number(cx)}" cy="{number(cy + ORB_GLOW_SHAPE["drop"])}" '
        f'r="{number(ORB_GLOW_SHAPE["radius"])}" '
        f'gradientUnits="userSpaceOnUse">{glow}</radialGradient>'
        f'<linearGradient id="orb-gloss" x1="0" y1="{number(cy - radius)}" x2="0" '
        f'y2="{number(cy + ORB_GLOSS_SHAPE["fade"])}" '
        f'gradientUnits="userSpaceOnUse">{gloss}</linearGradient>{shell_definitions}</defs>'
        f'<g id="orb"><circle cx="{number(cx)}" cy="{number(cy)}" r="{number(radius)}" fill="url(#orb-body)"/>'
        f'<circle cx="{number(cx)}" cy="{number(cy)}" r="{number(radius - 1)}" fill="url(#orb-glow)"/>'
        f'<path d="{gloss_path(cx, cy, radius)}" fill="url(#orb-gloss)"/>'
        f"{shell_shapes}"
        f'<circle cx="{number(cx)}" cy="{number(cy)}" r="{number(radius + rim_width / 2)}" fill="none" '
        f'stroke="#FFFFFF" stroke-opacity="{number(ORB_RIM["opacity"])}" stroke-width="{number(rim_width)}"/>'
        "</g></svg>\n"
    )


def start_shade_svg():
    """The bar's darkening behind the orb (palette.START_SHADE), from the screen's edge."""
    shade = palette.START_SHADE
    width, height = shade["reach"], palette.TASKBAR_HEIGHT - palette.START_SHADE_TOP
    number = faces.number
    opacity = number(round(shade["opacity"] / 255, 3))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><defs>'
        f'<radialGradient id="shade" cx="0" cy="{height}" r="{shade["reach"]}" gradientUnits="userSpaceOnUse" '
        f'gradientTransform="translate(0 {height}) scale(1 {number(round(1 / shade["height_scale"], 4))}) '
        f'translate(0 {-height})">'
        f'<stop offset="0" stop-color="#000000" stop-opacity="{opacity}"/>'
        f'<stop offset="{number(round(shade["flat"] / shade["reach"], 4))}" stop-color="#000000" '
        f'stop-opacity="{opacity}"/><stop offset="1" stop-color="#000000" stop-opacity="0"/></radialGradient></defs>'
        f'<rect id="shade" x="0" y="0" width="{width}" height="{height}" fill="url(#shade)"/></svg>\n'
    )


def tray_shade_svg():
    """The bar at the notification area (trayshade.py), its last WIDTH columns below the top line and highlight: a
    band of rows each, black's opacity running through a point every STEP columns up to the Show desktop strip, and
    white's behind the strip, where Windows 7's bar is lighter."""
    number = faces.number
    width, height = tray_shade.WIDTH, palette.TASKBAR_HEIGHT - palette.START_SHADE_TOP
    dark = width - tray_shade.STRIP
    definitions, shapes = [], []
    for index, (row, light) in enumerate(zip(tray_shade.OPACITY, tray_shade.LIGHT, strict=True)):
        knots = "".join(
            f'<stop offset="{number(round((column * tray_shade.STEP + tray_shade.STEP / 2) / dark, 4))}" '
            f'stop-color="#000000" stop-opacity="{number(round(alpha / 255, 3))}"/>'
            for column, alpha in enumerate(row)
        )
        definitions.append(f'<linearGradient id="tray{index}" x1="0" y1="0" x2="1" y2="0">{knots}</linearGradient>')
        top = index * tray_shade.BAND
        rows = min(tray_shade.BAND, height - top)
        shapes.append(f'<rect x="0" y="{top}" width="{dark}" height="{rows}" fill="url(#tray{index})"/>')
        shapes.append(
            f'<rect x="{dark}" y="{top}" width="{tray_shade.STRIP}" height="{rows}" fill="#FFFFFF" '
            f'fill-opacity="{number(round(light / 255, 3))}"/>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f"<defs>{''.join(definitions)}</defs>{''.join(shapes)}</svg>\n"
    )


def reflection_svg():
    """DWM's glass streaks (reflection.py): one gradient across bands leaning ANGLE degrees from vertical, over the
    map's own size; it stretches to whatever size it is drawn, as DWM stretches the map over the screen."""
    number = faces.number
    width, height = reflection.MAP_SIZE
    lean = math.radians(reflection.ANGLE)
    first, last = reflection.STOPS[0][0], reflection.STOPS[-1][0]

    def point(position):
        return f"{number(round(position * math.cos(lean), 3))}", f"{number(round(-position * math.sin(lean), 3))}"

    (x1, y1), (x2, y2) = point(first), point(last)
    stops_markup = "".join(
        f'<stop offset="{number(round((position - first) / (last - first), 5))}" '
        f'stop-color="#{grey:02X}{grey:02X}{grey:02X}" '
        f'stop-opacity="{number(round(alpha / 255 * reflection.OPACITY / 100, 4))}"/>'
        for position, grey, alpha in reflection.STOPS
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" preserveAspectRatio="none"><defs>'
        f'<linearGradient id="streaks" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" gradientUnits="userSpaceOnUse">'
        f"{stops_markup}</linearGradient></defs>"
        f'<rect id="streaks" x="0" y="0" width="{width}" height="{height}" fill="url(#streaks)"/></svg>\n'
    )


def bar_edge_svg():
    """The bar's dark line and highlight along its top, drawn over the glass and its streaks."""
    lines = "".join(
        f'<rect x="0" y="{row}" width="{PANEL_WIDTH}" height="1" fill="{colour}" '
        f'fill-opacity="{faces.number(round(alpha / 255, 3))}"/>'
        for row, (colour, alpha) in enumerate(palette.TASKBAR_EDGE)
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{PANEL_WIDTH}" height="{len(palette.TASKBAR_EDGE)}" '
        f'viewBox="0 0 {PANEL_WIDTH} {len(palette.TASKBAR_EDGE)}" preserveAspectRatio="none">{lines}</svg>\n'
    )


# TaskBand2Composited::ScrollBar ARROWBTN (aero.msstyles IMAGE_1006/1007): its states in the strips' order. The
# strips hold four more, repeating the hover states.
ARROW_DIRECTIONS = ("up", "down", "left", "right")
SCROLL_ARROW_STATES = [
    f"{direction}-{state}" for direction in ARROW_DIRECTIONS for state in ("normal", "hot", "pressed", "disabled")
] + [f"{direction}-hover" for direction in ARROW_DIRECTIONS]
# The face is two lines, black outside and white inside, both at 50% and open towards the other arrow of the pair;
# a disabled up or down arrow has no white line, while the sprite keeps it on disabled left and right ones. The
# glyph is white, at full strength when hot or under the pointer.
LINE_OPACITY = round(128 / 255, 4)  # the sprites' alpha 128, which 0.5 would round to 127
GLYPH_OPACITY = {"normal": LINE_OPACITY, "hot": 1, "pressed": LINE_OPACITY, "disabled": LINE_OPACITY, "hover": 1}
GLYPH_SIZE = (9, 7)
# Each direction's triangle in its glyph cell, apex then base, in pixels: the sprite's 1-3-5-7 stair is a triangle
# whose apex and base corners stand a quarter pixel out of it, the closest a straight edge comes to the stair.
GLYPH_TRIANGLES = {
    "up": ((4.5, 0.75), (0.75, 5), (8.25, 5)),
    "down": ((4.5, 6.25), (0.75, 2), (8.25, 2)),
    "left": ((1.75, 3.5), (6, -0.25), (6, 7.25)),
    "right": ((7.25, 3.5), (3, -0.25), (3, 7.25)),
}
OPEN_SIDE = {"up": "bottom", "down": "top", "left": "right", "right": "left"}


def frame_lines(inset, width, height, open_side):
    """The rectangles of a one-pixel frame `inset` from the button's edge, running out through its open side. The
    left and right lines stop short of the top and bottom ones, so no corner is drawn twice."""
    top, bottom = (0 if open_side == "top" else inset + 1), (height if open_side == "bottom" else height - inset - 1)
    left, right = (0 if open_side == "left" else inset), (width if open_side == "right" else width - inset)
    sides = {
        "top": (left, inset, right - left, 1),
        "bottom": (left, height - inset - 1, right - left, 1),
        "left": (inset, top, 1, bottom - top),
        "right": (width - inset - 1, top, 1, bottom - top),
    }
    return [rect for side, rect in sides.items() if side != open_side]


def scroll_arrow_markup(state, size, origin=(0, 0)):
    direction, look = state.split("-")
    width, height = size
    x0, y0 = origin
    lines = [("#000000", rect) for rect in frame_lines(0, width, height, OPEN_SIDE[direction])]
    if look != "disabled" or direction in ("left", "right"):
        lines += [("#FFFFFF", rect) for rect in frame_lines(1, width, height, OPEN_SIDE[direction])]
    line_opacity = faces.number(LINE_OPACITY)
    rects = "".join(
        f'<rect x="{x0 + x}" y="{y0 + y}" width="{w}" height="{h}" fill="{colour}" fill-opacity="{line_opacity}"/>'
        for colour, (x, y, w, h) in lines
    )
    gx, gy = x0 + (width - GLYPH_SIZE[0]) // 2, y0 + (height - GLYPH_SIZE[1]) // 2
    points = " ".join(f"{faces.number(gx + x)},{faces.number(gy + y)}" for x, y in GLYPH_TRIANGLES[direction])
    opacity = faces.number(GLYPH_OPACITY[look])
    return f'{rects}<polygon points="{points}" fill="#FFFFFF" fill-opacity="{opacity}"/>'


def scroll_arrow_svg(state, size):
    width, height = size
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f"{scroll_arrow_markup(state, size)}</svg>\n"
    )


def scroll_arrows_svg(size=(17, 20)):
    """Every arrow state as its own element, one under another, for the superbar's paging arrows."""
    width, height = size
    groups = "".join(
        f'<g id="{state}">{scroll_arrow_markup(state, size, (0, index * height))}</g>'
        for index, state in enumerate(SCROLL_ARROW_STATES)
    )
    total = height * len(SCROLL_ARROW_STATES)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{total}" viewBox="0 0 {width} {total}">'
        f"{groups}</svg>\n"
    )


# The notification area's "show hidden icons" button (TrayNotifyHoriz::Button, and its Open variant while the popup
# shows), 21 by 20: a glass face when hot or pressed (traybutton.FACES), and a white triangle shaded row by row with a
# soft black shadow, the triangle grown and moved for each layer of it (traybutton.SHADOW), all fitted by
# tests/aero/fit_aero_tray_button.py. The triangles stand a quarter pixel out of the sprite's 1-3-5-7 stair.
TRAY_BUTTON_SIZE = (21, 20)
TRAY_GLYPHS = {
    "": ((10.5, 7.75), (14.25, 12), (6.75, 12)),  # points up: the hidden icons are above
    "open-": ((6.75, 8), (14.25, 8), (10.5, 12.25)),
}


def outset(points, distance):
    """A convex polygon (clockwise on screen) grown by distance on every side: each corner where its two neighbouring
    edges, moved outwards, meet."""

    def moved_line(start, end):
        (x0, y0), (x1, y1) = start, end
        length = math.hypot(x1 - x0, y1 - y0)
        normal = ((y1 - y0) / length, (x0 - x1) / length)
        return (x0 + normal[0] * distance, y0 + normal[1] * distance), (x1 - x0, y1 - y0)

    lines = [moved_line(points[index], points[(index + 1) % len(points)]) for index in range(len(points))]
    corners = []
    for index in range(len(points)):
        (px, py), (dx, dy) = lines[index - 1]
        (qx, qy), (ex, ey) = lines[index]
        along = ((qx - px) * ey - (qy - py) * ex) / (dx * ey - dy * ex)
        corners.append((px + along * dx, py + along * dy))
    return corners


def polygon_points(points, origin):
    x0, y0 = origin
    return " ".join(f"{faces.number(round(x0 + x, 4))},{faces.number(round(y0 + y, 4))}" for x, y in points)


def tray_button_markup(state, origin=(0, 0), shadow=None):
    kind = "open-" if state.startswith("open-") else ""
    look = state.removeprefix(kind)
    prefix = f"tb{kind}{look}".replace("-", "")
    definitions, shapes = ("", "")
    if f"{kind}{look}" in traybutton.FACES:
        definitions, shapes = faces.face_markup(traybutton.FACES[f"{kind}{look}"], prefix, origin)
    triangle = TRAY_GLYPHS[kind]
    for dy, distance, opacity in shadow if shadow is not None else traybutton.SHADOW:
        grown = [(x, y + dy) for x, y in outset(triangle, distance)]
        shapes += (
            f'<polygon points="{polygon_points(grown, origin)}" fill="#000000" fill-opacity="{faces.number(opacity)}"/>'
        )
    top, bottom = min(y for _, y in triangle), max(y for _, y in triangle)
    gradient = (
        f'<linearGradient id="{prefix}g" gradientUnits="userSpaceOnUse" x1="0" y1="{faces.number(origin[1] + top)}" '
        f'x2="0" y2="{faces.number(origin[1] + bottom)}">'
        + "".join(
            f'<stop offset="{faces.number(round((row + 0.5 - top) / (bottom - top), 4))}" stop-color="{colour}"/>'
            for row, colour in traybutton.GLYPH_ROWS[kind]
        )
        + "</linearGradient>"
    )
    shapes += f'<polygon points="{polygon_points(triangle, origin)}" fill="url(#{prefix}g)"/>'
    return definitions + gradient, shapes


def tray_button_svg(state, shadow=None):
    width, height = TRAY_BUTTON_SIZE
    definitions, shapes = tray_button_markup(state, shadow=shadow)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f"<defs>{definitions}</defs>{shapes}</svg>\n"
    )


def tray_buttons_svg():
    """Every state of the "show hidden icons" button as its own element, side by side."""
    width, height = TRAY_BUTTON_SIZE
    states = [f"{kind}{look}" for kind in TRAY_GLYPHS for look in ("normal", "hot", "pressed")]
    definitions, groups = [], []
    for index, state in enumerate(states):
        state_definitions, shapes = tray_button_markup(state, (index * (width + GAP), 0))
        definitions.append(state_definitions)
        # A clear rectangle the button's size: an element's bounds are what KSvg stretches to the item.
        bounds = f'<rect x="{index * (width + GAP)}" y="0" width="{width}" height="{height}" fill="none"/>'
        groups.append(f'<g id="{state}">{bounds}{shapes}</g>')
    total = len(states) * (width + GAP)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="{height}">'
        f"<defs>{''.join(definitions)}</defs>\n" + "\n".join(groups) + "\n</svg>\n"
    )


def grip_svg(height=40):
    """The grip an unlocked taskbar shows before its band: the gripper's dots down the bar, as 1-pixel squares."""
    rows = range(palette.GRIP_FIRST_ROW, height - palette.GRIP_MARGIN - 1, palette.GRIP_ROW_PITCH)
    squares = "".join(
        f'<rect x="{x + dx}" y="{y + dy}" width="1" height="1" fill="{colour}" '
        f'fill-opacity="{faces.number(round(alpha / 255, 4))}"/>'
        for x in palette.GRIP_COLUMNS
        for y in rows
        for dy, dot_row in enumerate(palette.GRIP_DOT)
        for dx, (colour, alpha) in enumerate(dot_row)
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{palette.GRIP_WIDTH}" height="{height}">'
        f'<g id="grip"><rect width="{palette.GRIP_WIDTH}" height="{height}" fill="none"/>{squares}</g></svg>\n'
    )


def write_theme(out):
    (out / "widgets").mkdir(parents=True, exist_ok=True)
    (out / "translucent/widgets").mkdir(parents=True, exist_ok=True)
    (out / "widgets/panel-background.svg").write_text(panel_svg(translucent=False))
    (out / "translucent/widgets/panel-background.svg").write_text(panel_svg(translucent=True))
    (out / "widgets/tasks.svg").write_text(tasks_svg())
    (out / "widgets/startbutton.svg").write_text(orb_svg())
    (out / "widgets/startshade.svg").write_text(start_shade_svg())
    (out / "widgets/trayshade.svg").write_text(tray_shade_svg())
    (out / "widgets/reflection.svg").write_text(reflection_svg())
    (out / "widgets/baredge.svg").write_text(bar_edge_svg())
    (out / "widgets/showdesktop.svg").write_text(faces_svg(stops.SHOW_DESKTOP_FACES))
    (out / "widgets/taskgroup.svg").write_text(faces_svg(stops.GROUP_FACES))
    (out / "widgets/scrollarrow.svg").write_text(scroll_arrows_svg())
    (out / "widgets/trayarrow.svg").write_text(tray_buttons_svg())
    (out / "widgets/grip.svg").write_text(grip_svg())
    (out / "metadata.json").write_text(json.dumps(METADATA, indent=2) + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=HERE / "theme")
    destination = parser.parse_args().out
    write_theme(destination)
    print("wrote", destination)
