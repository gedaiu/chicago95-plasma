"""The Chicago95Aero decoration laid out as KWin's Aurorae lays it out (tests/aurorae_model.py)."""

from aurorae_model import Window
from conftest import REPO

AERO_THEME = REPO / "aero/aurorae/theme"
REFERENCE_DESKTOP = "#4395D1"


def reference_session(**options):
    """plasma_session's options for the Luna look with the Aero frames and superbar, laid out as win7screenres.png
    is (three pinned programs and Control Panel running without the focus, there its context menu's, here
    minimized) over the plain blue desktop of Windows 7's references, so its glass shows what theirs does; with
    any further options."""
    return {
        "settings": [("DECORATION", "aero"), ("BACKGROUND_MODE", "color"), ("BACKGROUND_COLOR", REFERENCE_DESKTOP)],
        "components": ["background"],
        "taskbar_style": "aero",
        "windows": [("Control Panel", "qt", "minimized")],
        "launchers": 3,
        "screen": (1024, 768),  # the references' size: DWM's streaks stretch over the screen
        **options,
    }


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


def bar_under_streaks(name, streaks):
    """Windows 7's bar under DWM's streaks in reference <name>: each row's median over its empty columns of the glass
    solved through the streaks drawn there (streaks: the reflection map as an RGBA image of the screen's size)."""
    import statistics

    from reference import screenshot

    image = screenshot(name)

    def pixel(x, y):
        return image.getpixel((x, 728 + y))

    empty = [
        x
        for x in range(320, 800)
        if all(sum(abs(a - b) for a, b in zip(pixel(x, y), pixel(x, 20), strict=True)) < 25 for y in range(4, 37))
    ]

    def under(x, y, channel):
        *colour, alpha = streaks.getpixel((x, 728 + y))
        opacity = alpha / 255
        return (pixel(x, y)[channel] - colour[channel] * opacity) / (1 - opacity)

    return [tuple(round(statistics.median(under(x, y, c) for x in empty)) for c in range(3)) for y in range(40)]


def streaked_glass(name):
    """Windows 7's glass at each pixel of the bar in reference <name>, with DWM's streaks over it as the Aero style
    draws them: a function of (x, y), y counted from the bar's top row. Needs a running Qt application."""
    import importlib.util

    from conftest import REPO
    from test_aero_buttons import rendered

    spec = importlib.util.spec_from_file_location(
        "make_aero_plasmastyle", REPO / "aero/plasma-style/make_aero_plasmastyle.py"
    )
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    streaks = rendered(generator.reflection_svg(), (1024, 768))
    rows = bar_under_streaks(name, streaks)

    def at(x, y):
        *colour, alpha = streaks.getpixel((x, 728 + y))
        opacity = alpha / 255
        return tuple(c * opacity + g * (1 - opacity) for c, g in zip(colour, rows[y], strict=True))

    return at
