"""Geometry and colours of the Blue Luna selection marks in the XP SP3 resources."""

RADIO_RADIUS = {13: 2.125, 16: 4, 25: 6.5}
# Light position, radius and the three colours of the gloss in each native size.
RADIO_GLOSS = {
    13: (0.23, 0.23, 0.7, ("#59d955", "#3cbc39", "#139211")),
    16: (0.23, 0.21, 0.64, ("#69e364", "#54d150", "#34ab30")),
    25: (0.43, 0.35, 1.0, ("#6aea66", "#169413", "#0a8c08")),
}
RADIO_DISABLED = "#c0bfb5"


def native_size(scale):
    dpi = 96 * scale
    return 25 if dpi >= 185 else 16 if dpi >= 118 else 13


def tick_arms(size):
    left, top, short, long, thickness = {
        13: (3, 4.5, 3, 5, 3),
        16: (3, 5.5, 4, 7, 4),
        25: (5, 8.5, 6, 10, 6),
    }[size]
    elbow = left + short
    right = elbow - 1 + long
    middle = top + short
    return (
        ((left, top), (elbow, middle), (elbow, middle + thickness), (left, top + thickness)),
        (
            (elbow - 1, middle),
            (right, middle - long),
            (right, middle - long + thickness),
            (elbow - 1, middle + thickness),
        ),
    )


def tick_svg(size, colour):
    polygons = []
    for arm in tick_arms(size):
        points = " ".join(f"{x:g},{y:g}" for x, y in arm)
        polygons.append(f'<polygon points="{points}" fill="{colour}"/>')
    return "".join(polygons)


def radio_gradient(size):
    x, y, radius, colours = RADIO_GLOSS[size]
    stops = "".join(f'<stop offset="{i / 2:g}" stop-color="{colour}"/>' for i, colour in enumerate(colours))
    return f'<radialGradient id="radioMark" cx="{x:g}" cy="{y:g}" r="{radius:g}">{stops}</radialGradient>'


# XP ships a separate face at each DPI. The centres of their diagonal
# gradients are at 50%. Each entry gives the two end stops and three colours.
RADIO_FACES = {
    13: {
        "normal": (0.27, 0.73, "#dfdfdb", "#f1f1ef", "#fdfdfc"),
        "checked": (0.19, 0.71, "#e1e1dc", "#f1f2ef", "#fdfdfc"),
        "pressed": (0.27, 0.71, "#b7b7ad", "#d7d6c9", "#eceadb"),
        "hover": (0.25, 0.71, "#fee09e", "#fbc861", "#f9b93f"),
    },
    16: {
        "normal": (0.25, 0.63, "#ededeb", "#fbfbfb", "#ffffff"),
        "pressed": (0.27, 0.73, "#b3b3aa", "#d4d2c5", "#ebe9da"),
        "hover": (0.23, 0.79, "#fee8b5", "#fcc964", "#f8b639"),
    },
    25: {
        "normal": (0.11, 0.79, "#e2e2de", "#f3f3f1", "#fcfcfb"),
        "checked": (0.17, 0.79, "#e1e1dc", "#f0f0ee", "#fafaf9"),
        "pressed": (0.21, 0.77, "#b4b4ab", "#d8d6c9", "#edecdc"),
        "hover": (0.37, 0.79, "#fff0ce", "#fede99", "#fac457"),
    },
}


def radio_face(size, state):
    """Return SVG paint definitions and circles in native SP3 resource coordinates."""
    centre = size / 2
    radius = centre - 0.5
    border = "#1c5180"
    fill = "none"
    definitions = ""
    inner = ""
    if state == "disabled":
        border = RADIO_DISABLED if size == 25 else "#cac8bb"
    else:
        face = "normal" if size == 16 and state == "checked" else state
        start, end, dark, middle, light = RADIO_FACES[size][face]
        if state == "hover":
            inset = {13: 3, 16: 3, 25: 5}[size]
            inner_colour = "#ffffff" if size == 16 else "#f1efdf"
            inner = f'<circle cx="{centre}" cy="{centre}" r="{centre - inset}" fill="{inner_colour}"/>'
        name = "radioFace" + state.title()
        stops = "".join(
            f'<stop offset="{at}" stop-color="{c}"/>' for at, c in ((start, dark), (0.5, middle), (end, light))
        )
        definitions = f'<linearGradient id="{name}" x2="100%" y2="100%">{stops}</linearGradient>'
        fill = f"url(#{name})"
    # At 96 DPI the SP3 rim tapers at the four cardinal points.
    if size == 13 and state != "disabled":
        outline = '<path d="M6.5 .5q5.5 .5 6 6q-.5 5.5-6 6q-5.5-.5-6-6q.5-5.5 6-6z" stroke-linejoin="round"'
    else:
        outline = f'<circle cx="{centre}" cy="{centre}" r="{radius}"'
    return definitions, f'{outline} stroke="{border}" fill="{fill}"/>{inner}'



def radio_face_svg(size, state, physical):
    definitions, shapes = radio_face(size, state)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{physical}" height="{physical}" '
        f'viewBox="0 0 {size} {size}"><defs>{definitions}</defs>{shapes}</svg>\n'
    )
