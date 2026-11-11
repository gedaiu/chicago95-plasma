"""Pixel artwork shared by Luna's Qt and GTK track bars (no toolkit dependency)."""

GROOVE_ROWS = ("#838383", "#ECECE7", "#F5F4EF", "#FFFFFF")
THUMB_STOPS = ("#F7F7F4", "#F3F3EF", "#DCDCD9", "#C3C3C0")
THUMB_BORDER_LIGHT, THUMB_BORDER_DARK = "#B5C4CD", "#778892"
THUMB_HOVER_ACCENT = ("#FBCB74", "#FAC158")
THUMB_DISABLED = ("#F5F4EA", "#BFBCAD")
THUMB_SIZE = (11, 21)


def thumb_shades(state, length):
    stops = THUMB_DISABLED if state == "disabled" else THUMB_STOPS
    if state == "pressed":
        stops = stops[::-1]
    colours = [tuple(bytes.fromhex(colour[1:])) for colour in stops]
    rows = []
    for index in range(length):
        position = index * (len(colours) - 1) / max(length - 1, 1)
        segment = min(int(position), len(colours) - 2)
        weight = position - segment
        rgb = [round(a + (b - a) * weight) for a, b in zip(colours[segment], colours[segment + 1], strict=True)]
        rows.append("#" + bytes(rgb).hex())
    return rows


def thumb_pixels(width, height, horizontal, state):
    shades = thumb_shades(state, height if horizontal else width)
    pixels = [[shades[y if horizontal else x] for x in range(width)] for y in range(height)]
    for y in range(height):
        pixels[y][0] = THUMB_BORDER_LIGHT
        pixels[y][-1] = THUMB_BORDER_DARK
    for x in range(width - 1):
        pixels[0][x] = THUMB_BORDER_LIGHT
        pixels[-1][x] = THUMB_BORDER_DARK
    if state == "hover":
        for band, colour in enumerate(THUMB_HOVER_ACCENT, 1):
            for along in range(1, (width if horizontal else height) - 1):
                pixels[band if horizontal else along][along if horizontal else band] = colour
    return pixels
