"""Connect a Chicago95 QML decoration to Aurorae and the installed SVG artwork."""

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
    rc.read(artwork / f"{artwork.name}rc")
    layout = {key[0].lower() + key[1:]: int(value) for key, value in rc["Layout"].items()}
    general = rc["General"]
    for state in ("Active", "Inactive"):
        rgb = general[state + "TextColor"].split(",")[:3]
        layout[state.lower() + "TextColor"] = "#" + "".join(f"{int(value):02x}" for value in rgb)
    layout["animationTime"] = general.getint("Animation")
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
        svg = artwork / f"{name.lower()}.svg"
        layout[name + "ButtonPath"] = str(svg) if svg.is_file() else ""
        if name not in ("restore", "maximize"):
            default = layout["buttonWidthMenu"] if name == "appMenu" else layout["buttonWidth"]
            layout.setdefault("buttonWidth" + name[0].upper() + name[1:], default)
    layout.setdefault("buttonWidthMaximizeRestore", layout["buttonWidth"])
    layout.setdefault("buttonMarginTopMaximized", 0)
    if artwork.name != "Chicago95Aero":
        layout["followsScheme"] = artwork.name == "Chicago95"
        layout["useTextShadow"] = general.getboolean("UseTextShadow")
        if layout["useTextShadow"]:
            for state in ("Active", "Inactive"):
                red, green, blue, alpha = map(int, general[f"{state}TextShadowColor"].split(","))
                layout[f"{state.lower()}TextShadowColor"] = f"#{alpha:02x}{red:02x}{green:02x}{blue:02x}"
            layout["textShadowX"] = general.getint("TextShadowOffsetX")
            layout["textShadowY"] = general.getint("TextShadowOffsetY")
        metadata = json.loads((artwork / "metadata.json").read_text())
        metadata["KPackageStructure"] = "KWin/Decoration"
        metadata["KPlugin"]["Id"] = package.name
        (package / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (ui / "Layout.js").write_text(".pragma library\nvar values = " + json.dumps(layout, indent=2) + "\n")


if __name__ == "__main__":
    configure(*(Path(arg) for arg in sys.argv[1:]))
