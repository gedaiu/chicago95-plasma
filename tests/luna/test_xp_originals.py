"""The Windows-XP-Originals fallback icon theme (luna/icons/xp_originals.py): built at install time from the user's
own icon archives through a map of freedesktop names, with no Microsoft pixels in the repository."""

import configparser
import importlib.util
import zipfile

import pytest
from conftest import REPO
from PIL import Image

spec = importlib.util.spec_from_file_location("xp_originals", REPO / "luna/icons/xp_originals.py")
xp_originals = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xp_originals)


def icon_bytes(tmp_path, colour, sizes):
    path = tmp_path / "icon.ico"
    Image.new("RGBA", (max(sizes), max(sizes)), colour).save(path, sizes=[(size, size) for size in sizes])
    return path.read_bytes()


@pytest.fixture
def archives(tmp_path):
    numbered, named = tmp_path / "ICON.zip", tmp_path / "High-Res_XP_Icons.zip"
    with zipfile.ZipFile(numbered, "w") as archive:
        archive.writestr("ICON/19.ico", icon_bytes(tmp_path, (255, 0, 0, 255), [48]))
        archive.writestr("ICON/20.ico", icon_bytes(tmp_path, (255, 0, 0, 255), [32]))
        archive.writestr("ICON/23.ico", icon_bytes(tmp_path, (0, 0, 255, 255), [48]))
    with zipfile.ZipFile(named, "w") as archive:
        archive.writestr("My Computer.ico", icon_bytes(tmp_path, (0, 255, 0, 255), [16, 32, 256]))
    return numbered, named


def build(tmp_path, archives, numbered_map, named_map):
    out = tmp_path / "Windows-XP-Originals"
    xp_originals.build_theme(out, archives[0], archives[1], numbered_map, named_map)
    return out


def test_a_numbered_icon_lands_under_its_name_at_its_own_size(tmp_path, archives):
    out = build(tmp_path, archives, {"folder": [19, 20]}, {})

    assert sorted(path.relative_to(out).as_posix() for path in out.rglob("*.png")) == [
        "32x32/xp/folder.png",
        "48x48/xp/folder.png",
    ]


def test_the_first_number_listed_for_a_size_wins(tmp_path, archives):
    out = build(tmp_path, archives, {"folder": [19, 23]}, {})

    assert Image.open(out / "48x48/xp/folder.png").convert("RGB").getpixel((5, 5)) == (255, 0, 0)


def test_every_size_of_a_named_icon_lands_and_comes_before_the_numbered_ones(tmp_path, archives):
    out = build(tmp_path, archives, {"computer": [19]}, {"computer": "My Computer.ico"})

    assert (
        sorted(path.parent.parent.name for path in out.rglob("computer.png")),
        Image.open(out / "48x48/xp/computer.png").convert("RGB").getpixel((5, 5)),
    ) == (["16x16", "256x256", "32x32", "48x48"], (255, 0, 0))


def test_the_index_lists_one_fixed_directory_per_size_it_holds(tmp_path, archives):
    out = build(tmp_path, archives, {"folder": [19, 20]}, {})
    index = configparser.ConfigParser(interpolation=None)
    index.read(out / "index.theme")

    assert (
        index["Icon Theme"]["Name"],
        index["Icon Theme"]["Directories"],
        dict(index["48x48/xp"]),
    ) == ("Windows XP Originals", "32x32/xp,48x48/xp", {"size": "48", "type": "Fixed"})


def test_a_missing_archive_or_number_is_skipped(tmp_path, archives):
    out = tmp_path / "Windows-XP-Originals"
    xp_originals.build_theme(out, archives[0], tmp_path / "absent.zip", {"folder": [19, 999]}, {"computer": "x.ico"})

    assert sorted(path.name for path in out.rglob("*.png")) == ["folder.png"]


def test_the_shipped_maps_use_numbers_inside_the_archives_range_and_freedesktop_style_names():
    names = [*xp_originals.NUMBERED, *xp_originals.NAMED]

    assert (
        all(6 <= number <= 1489 for numbers in xp_originals.NUMBERED.values() for number in numbers),
        all(name == name.lower() and " " not in name for name in names),
        {"folder", "computer", "user-trash", "printer", "help-browser"} <= set(xp_originals.NUMBERED),
    ) == (True, True, True)
