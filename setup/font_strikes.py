"""Build TrueType outlines and metrics from native monochrome glyphs."""

from collections import defaultdict

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen


def draw_strike_contours(pen, pixels, grid):
    # Follow the exposed edges clockwise, keeping ink on the right. Internal
    # scanline edges cause the monochrome rasterizer to drop parts of stems.
    edges = defaultdict(set)
    for x, y in sorted(pixels):
        if (x - 1, y) not in pixels:
            edges[x, y].add((x, y + 1))
        if (x, y + 1) not in pixels:
            edges[x, y + 1].add((x + 1, y + 1))
        if (x + 1, y) not in pixels:
            edges[x + 1, y + 1].add((x + 1, y))
        if (x, y - 1) not in pixels:
            edges[x + 1, y].add((x, y))

    while edges:
        previous = current = next(iter(edges))
        path = {}
        while current not in path:
            options = edges[current]
            x, y = current
            dx, dy = x - previous[0], y - previous[1]
            right_turn = (x + dy, y - dx)
            # At a diagonal contact, turn around this pixel to keep the two
            # strokes separate. Everywhere else there is just one way onward.
            following = right_turn if right_turn in options else min(options)
            path[current] = following
            previous, current = current, following

        # Two outlines can touch at a corner. Consume just the closed loop,
        # leaving any leading edges for the other contour.
        contour = []
        while current in path:
            contour.append(current)
            following = path.pop(current)
            edges[current].remove(following)
            if not edges[current]:
                del edges[current]
            current = following

        corners = []
        for i, (x, y) in enumerate(contour):
            before, after = contour[i - 1], contour[(i + 1) % len(contour)]
            if before[0] != after[0] and before[1] != after[1]:
                corners.append((x * grid, y * grid))
        pen.moveTo(corners[0])
        for point in corners[1:]:
            pen.lineTo(point)
        pen.closePath()


def strike_glyph(pixels, width, grid):
    pen = TTGlyphPen(None)
    draw_strike_contours(pen, pixels, grid)
    bearing = min((x for x, _ in pixels), default=0)
    return pen.glyph(), (width * grid, bearing * grid)


def save_font(destination, family, bold, glyphs, characters, metrics, em, top, bottom, grid, copyright_text):
    builder = FontBuilder(em, isTTF=True)
    builder.font["head"].macStyle = int(bold)
    builder.setupGlyphOrder(list(glyphs))
    builder.setupCharacterMap(characters)
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics(metrics)
    builder.setupHorizontalHeader(ascent=top, descent=bottom)
    style = "Bold" if bold else "Regular"
    builder.setupNameTable(
        {
            "familyName": family,
            "styleName": style,
            "uniqueFontIdentifier": f"{family} {style}",
            "fullName": f"{family} {style}",
            "psName": f"{family.replace(' ', '')}-{style}",
            "copyright": copyright_text,
        }
    )
    builder.setupOS2(
        sTypoAscender=top,
        sTypoDescender=bottom,
        usWinAscent=top,
        usWinDescent=-bottom,
        usWeightClass=700 if bold else 400,
        fsSelection=32 if bold else 64,
    )
    builder.setupPost(underlinePosition=-grid, underlineThickness=grid)
    builder.save(destination)
