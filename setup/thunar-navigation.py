"""Set Explorer navigation in Thunar without resetting unrelated preferences."""

import argparse
import os
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile
from xml.etree import ElementTree

TYPES = {
    "last-location-bar": "string", "last-menubar-visible": "bool",
    "last-toolbar-items": "string", "misc-small-toolbar-icons": "bool",
}
AERO = {
    "last-location-bar": "ThunarLocationButtons",
    "last-menubar-visible": "false",
    "last-toolbar-items": "back:1,forward:1,location-bar:1,search:1,menu:1",
}
STANDARD = {"last-location-bar": "ThunarLocationEntry", "last-menubar-visible": "true", "last-toolbar-items": None}
WIN95 = {
    "last-toolbar-items": (
        "location-bar:1,open-parent:1,undo:1,view-as-icons:1,view-as-compact-list:1,view-as-detailed-list:1,menu:1"
    ),
    "misc-small-toolbar-icons": "true",
}


def navigation_changes(style, current, look=""):
    toolbar = current.get("last-toolbar-items")
    from_aero = toolbar == AERO["last-toolbar-items"]
    from_win95 = toolbar == WIN95["last-toolbar-items"]
    changes = {}
    if style == "aero":
        changes.update(AERO)
    elif from_aero:
        # Keep preferences that the user changed while the Aero look was active.
        changes.update((name, value) for name, value in STANDARD.items() if current.get(name) == AERO[name])
    win95 = style == "classic" and look == "1995"
    if win95 and (toolbar is None or from_aero):
        changes.update(WIN95)
    elif from_win95 and not win95:
        if style != "aero":
            changes["last-toolbar-items"] = None
        if current.get("misc-small-toolbar-icons") == WIN95["misc-small-toolbar-icons"]:
            changes["misc-small-toolbar-icons"] = None
    return {name: value for name, value in changes.items() if current.get(name) != value}


def update_profile(path, style, look=""):
    tree = ElementTree.parse(path)
    root = tree.getroot()
    entries = {element.get("name"): element for element in root.findall("property")}
    changes = navigation_changes(style, {name: element.get("value") for name, element in entries.items()}, look)
    if not changes:
        return
    for name, value in changes.items():
        element = entries.get(name)
        if value is None:
            root.remove(element)
            continue
        if element is None:
            element = ElementTree.SubElement(root, "property", name=name)
        element.set("type", TYPES[name])
        element.set("value", value)
    with NamedTemporaryFile(dir=path.parent, delete=False) as output:
        tree.write(output, encoding="utf-8", xml_declaration=True)
    os.replace(output.name, path)


def update_xfconf(style, look=""):
    prefix = ["xfconf-query", "-c", "thunar", "-p"]
    current = {}
    for name in TYPES:
        value = subprocess.run([*prefix, f"/{name}"], capture_output=True, text=True, check=False)
        if value.returncode == 0:
            current[name] = value.stdout.rstrip("\n")
    for name, value in navigation_changes(style, current, look).items():
        arguments = ["-r"] if value is None else ["-n", "-t", TYPES[name], "-s", value]
        subprocess.run([*prefix, f"/{name}", *arguments], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--style", default="aero")
    parser.add_argument("--look", default="")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if args.live:
        update_xfconf(args.style, args.look)
    else:
        update_profile(args.profile, args.style, args.look)
