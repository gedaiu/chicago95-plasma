#!/usr/bin/env python3
"""Builds the Explorer toolbar icons in data/toolbar-icons/ from the Navigation Buttons archive.

    python3 -I setup/make_toolbar_icons.py ~/Downloads/"Navigation Buttons.zip"

The Windows 95 buttons carry their raised bevel inside the picture; it is cut off so the widget style
draws the button. Every glyph is centred, unscaled, on a 22x22 canvas: the size of a Dolphin toolbar icon.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / "data/toolbar-icons"
ICON_SIZE = "22x22"

WINDOWS_95_ICONS = {
    "Up2": ["go-up"],
    "cut": ["edit-cut"],
    "copy": ["edit-copy"],
    "paste": ["edit-paste"],
    "delete": ["edit-delete"],
    "open": ["document-open"],
    "search": ["edit-find", "system-search"],
}

WINDOWS_2000_ICONS = {
    "Back": ["go-previous"],
    "Forward": ["go-next"],
    "Up": ["go-up"],
    "Cut": ["edit-cut"],
    "Copy": ["edit-copy"],
    "Paste": ["edit-paste"],
    "Delete": ["edit-delete"],
    "Undo": ["edit-undo"],
    "Redo": ["edit-redo"],
    "New Folder": ["folder-new"],
    "search_web": ["edit-find", "system-search"],
}

# The bevel is two pixels on each side; flood-filling the grey face from the corners keeps the glyph's own greys.
BEVEL_CUT = ["-alpha", "set", "-crop", "19x18+2+2", "+repage", "-fill", "none", "-fuzz", "2%",
             *[argument for corner in ("0,0", "18,0", "0,17", "18,17") for argument in ("-draw", f"color {corner} floodfill")],
             "-trim", "+repage"]


def convert(source: str, glyph_options: list[str], destination: Path):
    subprocess.run(["magick", source, *glyph_options, "-background", "none", "-gravity", "center",
                    "-extent", ICON_SIZE, str(destination)], check=True)


def build_set(name: str, folder: Path, icons: dict[str, list[str]], glyph_options: list[str]):
    target = OUTPUT / name
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    for source_name, icon_names in icons.items():
        # search_web.ico holds 32 and 16 pixel frames; the toolbar takes the small one.
        frame = "[1]" if source_name == "search_web" else ""
        for icon_name in icon_names:
            convert(f"{folder / source_name}.ico{frame}", glyph_options, target / f"{icon_name}.png")


def main(navigation_zip: str):
    with tempfile.TemporaryDirectory() as unpacked:
        subprocess.run(["7z", "x", "-y", f"-o{unpacked}", navigation_zip], check=True, stdout=subprocess.DEVNULL)
        buttons = Path(unpacked) / "Navigation Buttons"
        build_set("1995", buttons / "Windows 95", WINDOWS_95_ICONS, BEVEL_CUT)
        build_set("2000", buttons / "Windows 2000", WINDOWS_2000_ICONS, [])


if __name__ == "__main__":
    main(sys.argv[1])
