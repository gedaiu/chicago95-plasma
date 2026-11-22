"""Connect the Aero caption to the installed Aurorae renderer and the theme's SVG artwork."""

import configparser
import json
import sys
from pathlib import Path


def configure(package, artwork, renderer):
    ui = package / "contents/ui"
    (ui / "qmldir").write_text(
        f"SystemAurorae 1.0 {renderer.resolve().as_uri()}\n"
        f"SystemDecorationButton 1.0 {renderer.with_name('DecorationButton.qml').resolve().as_uri()}\n"
    )
    rc = configparser.ConfigParser()
    rc.optionxform = str
    rc.read(artwork / "Chicago95Aerorc")
    layout = {key[0].lower() + key[1:]: int(value) for key, value in rc["Layout"].items()}
    for state in ("Active", "Inactive"):
        rgb = rc["General"][state + "TextColor"].split(",")[:3]
        layout[state.lower() + "TextColor"] = "#" + "".join(f"{int(value):02x}" for value in rgb)
    layout["animationTime"] = rc["General"].getint("Animation")
    layout["decorationPath"] = str(artwork / "decoration.svg")
    for name in (
        "minimize",
        "maximize",
        "restore",
        "close",
        "help",
        "shade",
        "appMenu",
        "keepAbove",
        "keepBelow",
        "allDesktops",
    ):
        svg = artwork / f"{name}.svg"
        layout[name + "ButtonPath"] = str(svg) if svg.is_file() else ""
        if name not in ("restore", "maximize"):
            layout.setdefault("buttonWidth" + name[0].upper() + name[1:], layout["buttonWidth"])
    (ui / "Layout.js").write_text(".pragma library\nvar values = " + json.dumps(layout, indent=2) + "\n")


if __name__ == "__main__":
    configure(*(Path(arg) for arg in sys.argv[1:]))
