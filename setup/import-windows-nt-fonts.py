#!/usr/bin/env python3
"""Install local UI fonts from a Windows 2000, XP, or 7 Fonts directory."""

import argparse
import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from fontTools.ttLib import TTFont

FILES = {
    "2000": ("tahoma.ttf", "tahomabd.ttf"),
    "xp": ("tahoma.ttf", "tahomabd.ttf", "trebuc.ttf", "trebucbd.ttf"),
    "7": ("segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf", "segoeuiz.ttf"),
}
OPTIONAL = {
    "xp": ("trebucit.ttf", "trebucbi.ttf"),
    "7": ("segoeuil.ttf", "seguisb.ttf"),
}


def install_font(source, destination, edition):
    if edition != "2000":
        shutil.copyfile(source, destination)
        return
    # XP ships a different version of Tahoma. Give 2000's face its own
    # family so applications can select it without replacing XP's font.
    family = "Chicago95 Windows 2000 Tahoma"
    with TTFont(source) as font:
        names = font["name"]
        style = "Bold" if font["OS/2"].usWeightClass >= 700 else "Regular"
        values = {
            1: family,
            3: f"{family} {style}",
            4: f"{family} {style}",
            6: f"Chicago95Windows2000Tahoma-{style}",
            16: family,
            21: family,
        }
        for record in names.names:
            if record.nameID in values:
                record.string = values[record.nameID]
        font.save(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("edition", choices=FILES)
    parser.add_argument("fonts", type=Path, help="local folder with the original TTF files")
    args = parser.parse_args()
    try:
        sources = {path.name.lower(): path for path in args.fonts.iterdir()}
        required = FILES[args.edition]
        missing = set(required) - sources.keys()
        if missing:
            raise ValueError(f"Missing font files: {', '.join(sorted(missing))}")
        files = (*required, *(name for name in OPTIONAL.get(args.edition, ()) if name in sources))
        data_home = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local/share"))
        destination = data_home / "fonts" / "Chicago95" / f"Windows{args.edition.upper()}"
        destination.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=destination) as scratch:
            for name in files:
                install_font(sources[name], Path(scratch) / name, args.edition)
            if args.edition in ("2000", "xp"):
                from make_nt_task_font import make_task_font

                make_task_font(sources["tahomabd.ttf"], Path(scratch) / "Taskbar-120-Bold.ttf", args.edition.upper())
            for path in Path(scratch).iterdir():
                path.replace(destination / path.name)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(destination)


if __name__ == "__main__":
    main()
