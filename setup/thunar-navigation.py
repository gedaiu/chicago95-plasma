"""Set Explorer navigation in Thunar without resetting unrelated preferences."""

import argparse
import os
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile
from xml.etree import ElementTree

TYPES = {"last-location-bar": "string", "last-menubar-visible": "bool", "last-toolbar-items": "string"}
AERO = {
    "last-location-bar": "ThunarLocationButtons",
    "last-menubar-visible": "false",
    "last-toolbar-items": "back:1,forward:1,location-bar:1,search:1,menu:1",
}
STANDARD = {"last-location-bar": "ThunarLocationEntry", "last-menubar-visible": "true", "last-toolbar-items": None}


def navigation_changes(style, current):
    if style == "aero":
        return {name: value for name, value in AERO.items() if current.get(name) != value}
    # Restore Thunar's standard toolbar only if the Aero override is still present.
    if current.get("last-toolbar-items") != AERO["last-toolbar-items"]:
        return {}
    return {name: value for name, value in STANDARD.items() if current.get(name) == AERO[name]}


def update_profile(path, style):
    tree = ElementTree.parse(path)
    root = tree.getroot()
    entries = {element.get("name"): element for element in root.findall("property")}
    changes = navigation_changes(style, {name: element.get("value") for name, element in entries.items()})
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


def update_xfconf(style):
    prefix = ["xfconf-query", "-c", "thunar", "-p"]
    current = {}
    for name in AERO:
        value = subprocess.run([*prefix, f"/{name}"], capture_output=True, text=True, check=False)
        if value.returncode == 0:
            current[name] = value.stdout.rstrip("\n")
    for name, value in navigation_changes(style, current).items():
        arguments = ["-r"] if value is None else ["-n", "-t", TYPES[name], "-s", value]
        subprocess.run([*prefix, f"/{name}", *arguments], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--style", default="aero")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if args.live:
        update_xfconf(args.style)
    else:
        update_profile(args.profile, args.style)
