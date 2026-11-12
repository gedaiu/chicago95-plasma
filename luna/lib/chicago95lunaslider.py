"""Pixel artwork shared by Luna's Qt and GTK track bars (no toolkit dependency)."""

GROOVE_ROWS = ("#9D9C96",)
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


def thumb_pixels(width, height, horizontal, state, point=None):
    """A green-capped rectangle, or a pointer toward a single row of tick marks.

    ``before`` points up/left and ``after`` down/right. Both-sided or unmarked
    ranges use the rectangular thumb. Transparent pixels preserve the track.
    """
    across, length = (width, height) if horizontal else (height, width)
    shades = thumb_shades(state, length)
    pixels = [[None] * across for _ in range(length)]
    accent = {
        "normal": ("#81DC83", "#49C94B"),
        "hover": THUMB_HOVER_ACCENT,
        "pressed": ("#409D42", "#2D8F30"),
        "disabled": ("#DAD8CD", "#C9C7BA"),
    }[state]
    taper = across // 2
    for y in range(length):
        inset = max(0, y - (length - taper - 1)) if point else 0
        left, right = inset, across - 1 - inset
        for x in range(left, right + 1):
            pixels[y][x] = shades[y]
        pixels[y][left] = THUMB_BORDER_LIGHT
        pixels[y][right] = THUMB_BORDER_DARK
        if y == 0:
            for x in range(left, right):
                pixels[y][x] = THUMB_BORDER_LIGHT
        elif y in (1, 2):
            for x in range(left + 1, right):
                pixels[y][x] = accent[y - 1]
        elif inset and right - left > 1:
            pixels[y][left + 1] = accent[0]
            pixels[y][right - 1] = accent[1]
        elif not point and y in (length - 3, length - 2):
            for x in range(left + 1, right):
                pixels[y][x] = accent[length - 2 - y]
        if y == length - 1:
            for x in range(left, right + 1):
                pixels[y][x] = THUMB_BORDER_DARK
    if point == "before":
        pixels.reverse()
    return pixels if horizontal else [list(row) for row in zip(*pixels, strict=True)]
