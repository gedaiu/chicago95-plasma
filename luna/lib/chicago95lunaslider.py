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


def thumb_pixels(width, height, horizontal, state, point=None, scale=1):
    """A green-capped rectangle, or a pointer toward a single row of tick marks.

    ``before`` points up/left and ``after`` down/right. Both-sided or unmarked
    ranges use the rectangular thumb. Transparent pixels preserve the track.
    ``scale`` draws at that many device pixels per logical pixel; the pointer's
    taper still steps one device pixel per row so it stays a straight diagonal.
    """
    across, length = (width, height) if horizontal else (height, width)
    shades = thumb_shades(state, length)
    device_across, device_length = across * scale, length * scale
    pixels = [[None] * device_across for _ in range(device_length)]
    accent = {
        "normal": ("#81DC83", "#49C94B"),
        "hover": THUMB_HOVER_ACCENT,
        "pressed": ("#409D42", "#2D8F30"),
        "disabled": ("#DAD8CD", "#C9C7BA"),
    }[state]
    taper_start = (length - across // 2 - 1) * scale + scale // 2
    for device_y in range(device_length):
        y = device_y // scale
        inset = max(0, device_y - taper_start) if point else 0
        left, right = inset, device_across - 1 - inset
        inner_left, inner_right = left + scale, right - scale
        pixels[device_y][left : right + 1] = [shades[y]] * (right - left + 1)
        pixels[device_y][left:inner_left] = [THUMB_BORDER_LIGHT] * scale
        pixels[device_y][inner_right + 1 : right + 1] = [THUMB_BORDER_DARK] * scale
        if y == 0:
            pixels[device_y][left : inner_right + 1] = [THUMB_BORDER_LIGHT] * (inner_right + 1 - left)
        elif y in (1, 2):
            pixels[device_y][inner_left : inner_right + 1] = [accent[y - 1]] * (inner_right + 1 - inner_left)
        elif inset and inner_right >= inner_left:
            pixels[device_y][inner_left : inner_left + scale] = [accent[0]] * scale
            pixels[device_y][inner_right + 1 - scale : inner_right + 1] = [accent[1]] * scale
        elif not point and y in (length - 3, length - 2):
            pixels[device_y][inner_left : inner_right + 1] = [accent[length - 2 - y]] * (inner_right + 1 - inner_left)
        if y == length - 1:
            pixels[device_y][left : right + 1] = [THUMB_BORDER_DARK] * (right - left + 1)
    if point == "before":
        pixels.reverse()
    return pixels if horizontal else [list(row) for row in zip(*pixels, strict=True)]
