#!/usr/bin/env python3
"""Builds the Windows-XP-Originals icon theme from the user's own icon archives, the fallback under the Windows-XP
icon set: whatever that set lacks is looked up here.

No icon is in the repository. The maps below tie freedesktop icon names to the icons in two archives the user
supplies: ICON.zip, 1484 shell icons numbered 6..1489 (one size per file, a concept repeated at several sizes), and
High-Res_XP_Icons.zip, 35 named icons holding every size up to 256. Named icons come first; for each name and size
the first icon found wins, so the lists put the XP-era drawing before the older ones.

    xp_originals.py --out DIR --numbered ICON.zip --named High-Res_XP_Icons.zip
"""

import argparse
import io
import zipfile
from pathlib import Path

from PIL import Image

THEME_NAME = "Windows XP Originals"
SUBDIRECTORY = "xp"

NUMBERED = {
    "folder": [19, 20, 21, 22],
    "folder-open": [32, 33, 34],
    "folder-new": [1326, 1327, 1328],
    "folder-pictures": [800, 801, 802, 803],
    "folder-music": [812, 813, 814, 815],
    "user-home": [947, 948, 949],
    "go-home": [947, 948, 949],
    "computer": [119, 120, 121, 122],
    "drive-harddisk": [52, 53, 54],
    "drive-optical": [85, 86, 87],
    "media-optical": [88, 89, 90],
    "media-floppy": [46, 47, 48],
    "network-server": [69, 70, 71],
    "network-workgroup": [148, 149, 150, 151],
    "internet-web-browser": [1484, 1485, 1486],
    "printer": [129, 130, 131],
    "scanner": [1299, 1300, 1301],
    "camera-photo": [879, 880, 881],
    "camera-video": [1317, 1318, 1319],
    "input-mouse": [769, 770, 771],
    "video-display": [853, 854, 855],
    "preferences-system": [154, 155, 156],
    "preferences-desktop-theme": [1015, 1016, 1017],
    "preferences-desktop-font": [289, 290, 291],
    "preferences-desktop-accessibility": [997, 998, 999, 1000],
    "preferences-system-network": [1054, 1055, 1056],
    "preferences-desktop-sound": [1060, 1061, 1062],
    "applications-system": [1042, 1043, 1044],
    "system-users": [1009, 1010, 1011],
    "system-search": [190, 191, 192, 193],
    "edit-find": [190, 191, 192, 193],
    "help-browser": [198, 199, 200, 201],
    "help-contents": [198, 199, 200, 201],
    "dialog-information": [976, 977, 978, 980],
    "system-shutdown": [241, 242, 243, 244],
    "system-lock-screen": [365, 366, 367],
    "document-open-recent": [166, 167, 168, 169],
    "user-trash": [261, 262, 263],
    "user-trash-full": [682, 683, 681],
    "text-x-generic": [400, 401, 514],
    "font-x-generic": [528, 529, 530],
    "audio-x-generic": [749, 750, 751],
    "video-x-generic": [743, 744, 745],
    "application-x-executable": [14, 15],
    "media-playback-start": [875, 876],
    "go-next": [1066],
}

NAMED = {
    "computer": "My Computer.ico",
    "network-workgroup": "My Network Places.ico",
    "folder-open": "Folder Open.ico",
    "user-home": "My Profile Folder.ico",
    "text-x-generic": "File.ico",
    "audio-x-generic": "Music File.ico",
    "video-x-generic": "Video File.ico",
    "application-x-cd-image": "Disk Image File.ico",
    "video-display": "Display.ico",
    "computer-laptop": "Laptop.ico",
    "phone": "Phone.ico",
    "camera-photo": "Camera.ico",
    "input-gaming": "Game Controller.ico",
    "applications-internet": "Earth (fixed).ico",
    "applications-multimedia": "Video.ico",
    "preferences-system-network": "Internet Properties.ico",
    "preferences-desktop-sound": "Sounds, Speech, and Audio Devices.ico",
    "preferences-desktop-personal": "User Personalization.ico",
    "system-users": "User Accounts.ico",
    "user-identity": "User 1.ico",
    "network-server": "Manage your Server.ico",
    "kmines": "Minesweeper.ico",
    "gnome-mines": "Minesweeper.ico",
}


def archive_members(path):
    """{file name without folders: bytes} of an archive, or {} when it is not there."""
    if not Path(path).is_file():
        return {}
    with zipfile.ZipFile(path) as archive:
        return {Path(name).name: archive.read(name) for name in archive.namelist() if name.lower().endswith(".ico")}


def icon_sizes(data):
    """{size: RGBA image} for every square size an .ico holds."""
    icon = Image.open(io.BytesIO(data))
    pictures = {}
    for width, height in sorted(icon.info.get("sizes", {icon.size})):
        if width == height:
            icon.size = (width, height)
            pictures[width] = icon.convert("RGBA")
    return pictures


def collect(numbered_archive, named_archive, numbered_map, named_map):
    """{(name, size): image}, named icons first, then the numbered ones; the first icon for a name and size wins."""
    chosen = {}
    named_files, numbered_files = archive_members(named_archive), archive_members(numbered_archive)
    sources = [(name, [named_files.get(file)]) for name, file in named_map.items()]
    sources += [
        (name, [numbered_files.get(f"{number}.ico") for number in numbers]) for name, numbers in numbered_map.items()
    ]
    for name, datas in sources:
        for data in filter(None, datas):
            for size, picture in icon_sizes(data).items():
                chosen.setdefault((name, size), picture)
    return chosen


def index_text(sizes):
    directories = [f"{size}x{size}/{SUBDIRECTORY}" for size in sorted(sizes, key=str)]
    sections = "".join(
        f"\n[{size}x{size}/{SUBDIRECTORY}]\nSize={size}\nType=Fixed\n" for size in sorted(sizes, key=str)
    )
    header = f"[Icon Theme]\nName={THEME_NAME}\nComment=The user's own Windows XP icons\n"
    return f"{header}Directories={','.join(directories)}\n{sections}"


def build_theme(out, numbered_archive, named_archive, numbered_map=None, named_map=None):
    chosen = collect(
        numbered_archive,
        named_archive,
        NUMBERED if numbered_map is None else numbered_map,
        NAMED if named_map is None else named_map,
    )
    out = Path(out)
    for (name, size), picture in chosen.items():
        folder = out / f"{size}x{size}" / SUBDIRECTORY
        folder.mkdir(parents=True, exist_ok=True)
        picture.save(folder / f"{name}.png")
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.theme").write_text(index_text({size for _name, size in chosen}))
    return len(chosen)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--numbered", type=Path, required=True)
    parser.add_argument("--named", type=Path, required=True)
    options = parser.parse_args()
    print(build_theme(options.out, options.numbered, options.named), "icons")


if __name__ == "__main__":
    main()
