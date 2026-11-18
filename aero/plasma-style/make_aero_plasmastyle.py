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
orb = load("aero_orb", HERE / "orb.py")
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
    if translucent:
        glass = [(solved_fill(seen, glass_alpha), glass_alpha) for seen in palette.TASKBAR_GLASS]
        return [over(line, glass[0]) for line in edge] + glass
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
    """The glass outside the logo: rings orb.RING_WIDTH wide, cut into orb.SECTORS arcs of orb.SHELL's colours."""
    number = faces.number
    step = math.tau / orb.SECTORS

    def point(radius, angle):
        return f"{number(round(cx + radius * math.cos(angle), 3))},{number(round(cy + radius * math.sin(angle), 3))}"

    shapes = []
    for index, colours in enumerate(orb.SHELL):
        inner, outer = orb.SHELL_FROM + index * orb.RING_WIDTH, orb.SHELL_FROM + (index + 1) * orb.RING_WIDTH
        for sector, colour in enumerate(colours):
            start, end = sector * step, (sector + 1) * step
            shapes.append(
                f'<path d="M{point(inner, start)}L{point(outer, start)}A{number(outer)},{number(outer)} 0 0 1 '
                f"{point(outer, end)}L{point(inner, end)}A{number(inner)},{number(inner)} 0 0 0 "
                f'{point(inner, start)}z" fill="{colour}"/>'
            )
    return "", "".join(shapes)


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


def write_theme(out):
    (out / "widgets").mkdir(parents=True, exist_ok=True)
    (out / "translucent/widgets").mkdir(parents=True, exist_ok=True)
    (out / "widgets/panel-background.svg").write_text(panel_svg(translucent=False))
    (out / "translucent/widgets/panel-background.svg").write_text(panel_svg(translucent=True))
    (out / "widgets/tasks.svg").write_text(tasks_svg())
    (out / "widgets/startbutton.svg").write_text(orb_svg())
    (out / "widgets/startshade.svg").write_text(start_shade_svg())
    (out / "widgets/showdesktop.svg").write_text(faces_svg(stops.SHOW_DESKTOP_FACES))
    (out / "metadata.json").write_text(json.dumps(METADATA, indent=2) + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=HERE / "theme")
    destination = parser.parse_args().out
    write_theme(destination)
    print("wrote", destination)
