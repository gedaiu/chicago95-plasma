"""Wine's controls in the look: its classic controls coloured from the colour scheme.

    wine_look.py OUTPUT.reg

Wine draws the classic Windows controls itself and colours them from Control Panel\\Colors, as Windows did; its own
visual theme paints over them, so it is switched off. The colours come from the same colour scheme as the window
decoration (chicago95ui.read_scheme), the 3D lines from the look's bevel. The file is imported with `wine regedit`.
Wine keeps its own interface font: it does not take MS W98 UI as a substitute for Tahoma or MS Shell Dlg.
"""

import sys
from pathlib import Path

import chicago95ui

WHITE, BLACK = "255 255 255", "0 0 0"
INFO_BACKGROUND = "255 255 225"


def rgb(colour):
    return f"{colour.red()} {colour.green()} {colour.blue()}"


def wine_colours(scheme, bevel):
    face = rgb(scheme["face"])
    lines = {name: rgb(colour) for name, colour in chicago95ui.bevel_colors(scheme["face"], bevel).items()}
    return {
        "ButtonFace": face,
        "ButtonHilight": WHITE,
        "ButtonLight": lines["light"],
        "ButtonShadow": lines["shadow"],
        "ButtonDkShadow": lines["dark"],
        "ButtonText": BLACK,
        "ButtonAlternateFace": face,
        "Menu": face,
        "MenuBar": face,
        "MenuText": BLACK,
        "MenuHilight": rgb(scheme["selection"]),
        "Scrollbar": lines["light"],
        "Window": WHITE,
        "WindowText": BLACK,
        "WindowFrame": BLACK,
        "AppWorkspace": lines["shadow"],
        "ActiveBorder": face,
        "InactiveBorder": face,
        "GrayText": lines["shadow"],
        "Hilight": rgb(scheme["selection"]),
        "HilightText": rgb(scheme["selection_text"]),
        "HotTrackingColor": rgb(scheme["selection"]),
        "ActiveTitle": rgb(scheme["title_active"]),
        "GradientActiveTitle": rgb(scheme["title_active_blend"]),
        "TitleText": rgb(scheme["title_active_text"]),
        "InactiveTitle": rgb(scheme["title_inactive"]),
        "GradientInactiveTitle": rgb(scheme["title_inactive_blend"]),
        "InactiveTitleText": rgb(scheme["title_inactive_text"]),
        "InfoWindow": INFO_BACKGROUND,
        "InfoText": BLACK,
    }


def registry(scheme, bevel):
    colours = "".join(f'"{name}"="{value}"\n' for name, value in wine_colours(scheme, bevel).items())
    return (
        "REGEDIT4\n\n"
        "[HKEY_CURRENT_USER\\Control Panel\\Colors]\n"
        f"{colours}\n"
        "[HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\ThemeManager]\n"
        '"ThemeActive"="0"\n'
    )


def main():
    text = registry(chicago95ui.read_scheme(), chicago95ui.look_settings()["bevel"])
    Path(sys.argv[1]).write_text(text)


if __name__ == "__main__":
    main()
