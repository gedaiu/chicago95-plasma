"""The Chicago95Aero decoration laid out as KWin's Aurorae lays it out (tests/aurorae_model.py)."""

from aurorae_model import Window
from conftest import REPO

AERO_THEME = REPO / "aero/aurorae/theme"
REFERENCE_DESKTOP = "#4395D1"


class AeroWindow(Window):
    RC_NAME = "Chicago95Aerorc"

    def __init__(self, width, height, active=True, caption="", left="M", right="IAX", pressed=()):
        super().__init__(AERO_THEME, width, height, active, caption, left, right, pressed)


def plain_bar(name):
    """Windows 7's bar without DWM's streaks: each of its 40 rows' median over the columns no icon, button or tray
    reaches (x 320..999 where rows 4..36 stay within 25 levels of the middle row), in reference <name>."""
    import statistics

    from reference import screenshot

    image = screenshot(name)

    def pixel(x, y):
        return image.getpixel((x, 728 + y))

    empty = [
        x
        for x in range(320, 1000)
        if all(sum(abs(a - b) for a, b in zip(pixel(x, y), pixel(x, 20), strict=True)) < 25 for y in range(4, 37))
    ]
    return [tuple(round(statistics.median(pixel(x, y)[c] for x in empty)) for c in range(3)) for y in range(40)]
