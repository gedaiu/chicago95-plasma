#!/usr/bin/env python3
"""The running distribution's branding, for Setup's "brand it as this computer's system" and the Control Panel's
Distro Setup: its name and version, edition, company and logos, from os-release (read as data, never run) and the
icon themes. Only what was found is returned; the rest keeps its defaults.

    chicago95distro.py [--os-release PATH] [--data-dirs DIR:DIR]   prints KEY<TAB>value lines
"""

import argparse
import os
import re
import sys
from pathlib import Path

DEFAULT_DATA_DIRS = "/usr/local/share:/usr/share"
OS_RELEASE = Path("/etc/os-release")
BRANDING_KEYS = ("BANNER_TEXT", "EDITION", "COMPANY", "LOADING_FOOTER", "START_LOGO", "LOGIN_LOGO", "COMPANY_LOGO")
LINE = re.compile(r"^([A-Z0-9_]+)=(.*)$")
START_LOGO_SIZE = 32  # the 16px Start button logo, sharp up to a 2x screen
SIZE_FOLDER = re.compile(r"^(\d+)x\d+(?:@\d+)?$")
PICTURES = (".svg", ".png")


def unquote(value):
    """os-release's shell-like quoting: one pair of quotes around the value, backslash escapes inside."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
        return re.sub(r"\\(.)", r"\1", value) if value else value
    return value


def read_os_release(path=OS_RELEASE):
    """{KEY: value} of an os-release file, or {} when there is none."""
    path = Path(path)
    if not path.is_file():
        return {}
    fields = {}
    for line in path.read_text(errors="replace").splitlines():
        match = LINE.match(line.strip())
        if match:
            fields[match.group(1)] = unquote(match.group(2))
    return fields


def theme_pictures(name, roots):
    """The icon's pictures, one list of (size, path) per theme, hicolor's first: the distribution ships its logo
    there, other themes redraw it. Scalable pictures count as size 0."""
    themes = {}
    for root in map(Path, roots):
        for theme in sorted((root / "icons").glob("*/")):
            for folder in theme.glob("*/*"):
                size = SIZE_FOLDER.match(folder.parent.name)
                for extension in PICTURES:
                    picture = folder / f"{name}{extension}"
                    if picture.is_file():
                        themes.setdefault(theme.name, []).append((int(size.group(1)) if size else 0, picture))
    return [themes[theme] for theme in sorted(themes, key=lambda theme: (theme != "hicolor", theme))]


def find_icon(name, roots, smallest):
    """From the first theme that has the icon: its scalable picture, else its smallest picture of START_LOGO_SIZE or
    more (smallest) or its largest; without one, a picture in pixmaps; "" when there is none."""
    for pictures in theme_pictures(name, roots):
        scalable = [path for size, path in pictures if size == 0]
        if scalable:
            return str(scalable[0])
        sized = sorted((size, str(path)) for size, path in pictures)
        sharp = [path for size, path in sized if size >= START_LOGO_SIZE]
        largest_first = [path for _size, path in sized[::-1]]
        usable = (sharp or largest_first) if smallest else largest_first
        if usable:
            return usable[0]
    return next((str(path) for path in pixmaps(roots, name)), "")


def pixmaps(roots, stem):
    for root in map(Path, roots):
        for extension in PICTURES:
            picture = root / "pixmaps" / f"{stem}{extension}"
            if picture.is_file():
                yield picture


def find_wordmark(fields, roots):
    """The distribution's wide logo for a light page: its logos package's light-background SVG, else
    pixmaps/<id>-logo; "" when there is none (the company's name is then written instead)."""
    distribution = fields.get("ID", "")
    if not distribution:
        return ""
    for root in map(Path, roots):
        light = root / f"{distribution}-logos" / f"{distribution}_lightbackground.svg"
        if light.is_file():
            return str(light)
    return next((str(path) for path in pixmaps(roots, f"{distribution}-logo")), "")


def distro_branding(fields, roots):
    """{setting key: value} for what the distribution names; {} without a NAME."""
    name = fields.get("NAME", "")
    if not name:
        return {}
    found = {
        "BANNER_TEXT": " ".join(part for part in (name, fields.get("VERSION_ID", "")) if part),
        "EDITION": fields.get("VARIANT", "").removesuffix(" Edition"),
        "COMPANY": fields.get("VENDOR_NAME") or name.split()[0],
        "LOADING_FOOTER": fields.get("PRETTY_NAME", ""),
        "COMPANY_LOGO": find_wordmark(fields, roots),
    }
    logo = fields.get("LOGO", "")
    if logo:
        found["START_LOGO"] = find_icon(logo, roots, smallest=True)
        found["LOGIN_LOGO"] = find_icon(logo, roots, smallest=False)
    return {key: value for key, value in found.items() if value}


def data_dirs():
    return [path for path in (os.environ.get("XDG_DATA_DIRS") or DEFAULT_DATA_DIRS).split(":") if path]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--os-release", type=Path, default=OS_RELEASE)
    parser.add_argument("--data-dirs", default="", help="colon-separated data dirs holding icons/ and pixmaps/")
    options = parser.parse_args()
    roots = [path for path in options.data_dirs.split(":") if path] or data_dirs()
    for key, value in distro_branding(read_os_release(options.os_release), roots).items():
        sys.stdout.write(f"{key}\t{value}\n")


if __name__ == "__main__":
    main()
