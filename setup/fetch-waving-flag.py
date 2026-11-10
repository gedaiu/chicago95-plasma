#!/usr/bin/env python3
"""Downloads the public-domain horizontal logo of the 2000 edition from Wikimedia Commons and keeps only
its waving flag, on a transparent background, for the "2000" login and loading screens' mark.

    fetch-waving-flag.py OUTPUT.png

The logo is not bundled with Chicago95 (it is a trademark); Setup fetches it on the user's own machine
when they pick it. The file is found by its Commons page id and checked against its SHA-1, so the
cut-out coordinates below always match the picture.
"""
import hashlib
import json
import sys
import urllib.request

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_PAGE_ID = 200014766
COMMONS_SHA1 = "538bfea0f3beb60e881f206835642691ee8f9efd"
USER_AGENT = "chicago95-plasma-setup (https://github.com/gedaiu/chicago95-plasma)"

# In the 1778x524 logo: the inside of the orange frame, and the strip of frame the flag's right edge
# overlaps; in that strip only the flag's black outline is kept.
INSIDE_FRAME = (72, 79, 399, 402)
FRAME_OVERLAP = (399, 79, 416, 402)
REGISTERED_MARK = (349, 358, 361, 368)
PAPER = 248
PAPER_NOISE = 0.03  # the paper isn't perfectly even; fainter than this is paper
# The flag on the original start-up screen is 139x113 pixels: flatter than this redrawing, so the
# cut-out is squeezed to that shape.
ORIGINAL_ASPECT = 139 / 113


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def download_logo():
    query = f"{COMMONS_API}?action=query&pageids={COMMONS_PAGE_ID}&prop=imageinfo&iiprop=url|sha1&format=json"
    info = json.loads(fetch(query))["query"]["pages"][str(COMMONS_PAGE_ID)]["imageinfo"][0]
    picture = fetch(info["url"])
    if hashlib.sha1(picture).hexdigest() != COMMONS_SHA1:
        raise SystemExit("The Commons file has changed since Setup was written; pick another logo.")
    return picture


def without_paper(red, green, blue):
    """Colour to alpha: the pixel as a colour over the logo's paper white, so anti-aliased edges stay soft."""
    alpha = max(PAPER - red, PAPER - green, PAPER - blue, 0) / PAPER
    if alpha < PAPER_NOISE:
        return 0, 0, 0, 0
    unblend = [min(255, max(0, round((value - PAPER * (1 - alpha)) / alpha))) for value in (red, green, blue)]
    return (*unblend, round(alpha * 255))


def inside(box, x, y):
    return box[0] <= x < box[2] and box[1] <= y < box[3]


def flag_pixel(x, y, red, green, blue):
    """The flag layer's RGBA at (x, y) of the logo: transparent outside the flag."""
    if inside(REGISTERED_MARK, x, y):
        return 0, 0, 0, 0
    if inside(INSIDE_FRAME, x, y):
        return without_paper(red, green, blue)
    if inside(FRAME_OVERLAP, x, y) and red + green + blue < 150:
        return red, green, blue, 255
    return 0, 0, 0, 0


def cut_flag(image):
    """The flag alone, cropped to its pixels, from a QImage of the whole logo."""
    from PySide6.QtGui import QColor, QImage
    left, top, right, bottom = INSIDE_FRAME[0], INSIDE_FRAME[1], FRAME_OVERLAP[2], INSIDE_FRAME[3]
    flag = QImage(right - left, bottom - top, QImage.Format_ARGB32)
    for y in range(top, bottom):
        for x in range(left, right):
            colour = image.pixelColor(x, y)
            red, green, blue, alpha = flag_pixel(x, y, colour.red(), colour.green(), colour.blue())
            flag.setPixelColor(x - left, y - top, QColor(red, green, blue, alpha))
    from PySide6.QtCore import Qt
    flag = flag.copy(opaque_bounds(flag))
    return flag.scaled(flag.width(), round(flag.width() / ORIGINAL_ASPECT), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)


def opaque_bounds(image):
    from PySide6.QtCore import QRect
    xs, ys = [], []
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha():
                xs.append(x)
                ys.append(y)
    return QRect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)


def main(output):
    from PySide6.QtGui import QImage
    logo = QImage.fromData(download_logo())
    if not cut_flag(logo).save(output):
        raise SystemExit(f"Could not write {output}")


if __name__ == "__main__":
    main(sys.argv[1])
