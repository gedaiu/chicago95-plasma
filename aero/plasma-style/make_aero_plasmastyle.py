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
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


palette = load("aero_palette", HERE.parent / "palette.py")
stops = load("aero_plasma_stops", HERE / "stops.py")
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


def task_face_svg(state):
    return faces.face_svg(stops.TASK_FACES[state])


def show_desktop_face_svg(state):
    return faces.face_svg(stops.SHOW_DESKTOP_FACES[state])


def faces_svg(faces_by_state):
    """Each state's face as the centre of a frame without borders, laid out side by side."""
    definitions, groups = [], []
    width, height = next(iter(faces_by_state.values()))["size"]
    for index, (state, face) in enumerate(faces_by_state.items()):
        face_definitions, shapes = faces.face_markup(face, f"t{index}", (index * (width + GAP), 0))
        definitions.append(face_definitions)
        groups.append(f'<g id="{state}-center">{shapes}</g>{hint_margins(state)}')
    total = len(faces_by_state) * (width + GAP)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="{height}">'
        f"<defs>{''.join(definitions)}</defs>\n" + "\n".join(groups) + "\n</svg>\n"
    )


def tasks_svg():
    """The superbar's buttons are 60 by 40, the TASKITEM states as they are."""
    return faces_svg(stops.TASK_FACES)


# The Start orb's sphere, 39 pixels across at (27.5, 20) in a 58 by 40 bar slot (win7dragedge.png's at x 27.5,
# y 748): a navy body darkening outwards, cyan light pooling at its foot, a white gloss over its upper half, and a
# dark ring inside a light rim. The program logo Setup chose is laid over its middle, never drawn here.
ORB = {"centre": (27.5, 20), "radius": 19.5}
ORB_BODY = (("#1590CB", 0), ("#117BB9", 0.55), ("#0B4A78", 0.7), ("#02436D", 0.88))
ORB_GLOW = (("#03DFFD", 1), ("#0BB6E6", 0.6), ("#0B94C1", 0))
ORB_GLOSS = (("#FFFFFF", 0.85), ("#FFFFFF", 0))
ORB_GLOSS_SHAPE = {"rise": 7, "inset": 2, "height": 10}  # the gloss ellipse: above the centre, inside the rim, tall
ORB_GLOW_SHAPE = {"drop": 13, "radius": 16}  # where the cyan light pools below the centre, and how far it spreads
ORB_RINGS = (("#1D5480", 18), ("#6789A4", 19))


def orb_svg():
    (cx, cy), radius = ORB["centre"], ORB["radius"]
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
    rings = "".join(
        f'<circle cx="{number(cx)}" cy="{number(cy)}" r="{number(ring - 0.5)}" fill="none" stroke="{colour}"/>'
        for colour, ring in ORB_RINGS
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="58" height="40"><defs>'
        f'<radialGradient id="orb-body" cx="{number(cx)}" cy="{number(cy)}" r="{number(radius)}" '
        f'gradientUnits="userSpaceOnUse">{body}</radialGradient>'
        f'<radialGradient id="orb-glow" cx="{number(cx)}" cy="{number(cy + ORB_GLOW_SHAPE["drop"])}" '
        f'r="{number(ORB_GLOW_SHAPE["radius"])}" '
        f'gradientUnits="userSpaceOnUse">{glow}</radialGradient>'
        f'<linearGradient id="orb-gloss" x1="0" y1="{number(cy - radius)}" x2="0" y2="{number(cy)}" '
        f'gradientUnits="userSpaceOnUse">{gloss}</linearGradient></defs>'
        f'<g id="orb"><circle cx="{number(cx)}" cy="{number(cy)}" r="{number(radius)}" fill="url(#orb-body)"/>'
        f'<circle cx="{number(cx)}" cy="{number(cy)}" r="{number(radius - 1)}" fill="url(#orb-glow)"/>'
        f'<ellipse cx="{number(cx)}" cy="{number(cy - ORB_GLOSS_SHAPE["rise"])}" '
        f'rx="{number(radius - ORB_GLOSS_SHAPE["inset"])}" ry="{number(ORB_GLOSS_SHAPE["height"])}" '
        'fill="url(#orb-gloss)"/>'
        f"{rings}</g></svg>\n"
    )


def write_theme(out):
    (out / "widgets").mkdir(parents=True, exist_ok=True)
    (out / "translucent/widgets").mkdir(parents=True, exist_ok=True)
    (out / "widgets/panel-background.svg").write_text(panel_svg(translucent=False))
    (out / "translucent/widgets/panel-background.svg").write_text(panel_svg(translucent=True))
    (out / "widgets/tasks.svg").write_text(tasks_svg())
    (out / "widgets/startbutton.svg").write_text(orb_svg())
    (out / "widgets/showdesktop.svg").write_text(faces_svg(stops.SHOW_DESKTOP_FACES))
    (out / "metadata.json").write_text(json.dumps(METADATA, indent=2) + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=HERE / "theme")
    destination = parser.parse_args().out
    write_theme(destination)
    print("wrote", destination)
