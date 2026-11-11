import importlib.util
import subprocess
from pathlib import Path

import pytest
from conftest import REPO


@pytest.fixture(scope="module")
def toolbar_icons():
    spec = importlib.util.spec_from_file_location("make_toolbar_icons", REPO / "setup/make_toolbar_icons.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def output(toolbar_icons, tmp_path, monkeypatch):
    destination = tmp_path / "icons"
    monkeypatch.setattr(toolbar_icons, "OUTPUT", destination)
    return destination


def write_ico(path: Path, frames=1):
    path.parent.mkdir(parents=True, exist_ok=True)
    sizes = ["32x32", "16x16"][:frames]
    arguments = [part for size in sizes for part in ("-size", size, "xc:red")]
    subprocess.run(["magick", *arguments, str(path)], check=True)


def png_size(path: Path):
    return subprocess.run(
        ["magick", "identify", "-format", "%wx%h", str(path)], capture_output=True, text=True, check=True
    ).stdout


def test_build_set_names_each_icon_for_every_freedesktop_name(toolbar_icons, output, tmp_path):
    write_ico(tmp_path / "Find.ico")

    toolbar_icons.build_set("test", tmp_path, {"Find": ["edit-find", "system-search"]}, [])

    assert sorted(path.name for path in (output / "test").iterdir()) == ["edit-find.png", "system-search.png"]


def test_build_set_centres_the_glyph_on_a_22_pixel_canvas(toolbar_icons, output, tmp_path):
    write_ico(tmp_path / "Find.ico")

    toolbar_icons.build_set("test", tmp_path, {"Find": ["edit-find"]}, [])

    assert png_size(output / "test/edit-find.png") == "22x22"


def test_build_set_takes_the_small_frame_of_search_web(toolbar_icons, output, tmp_path):
    write_ico(tmp_path / "search_web.ico", frames=2)

    toolbar_icons.build_set("test", tmp_path, {"search_web": ["edit-find"]}, [])

    assert png_size(output / "test/edit-find.png") == "22x22"


def test_build_set_replaces_a_previous_build(toolbar_icons, output, tmp_path):
    stale = output / "test/stale.png"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"")
    write_ico(tmp_path / "Find.ico")

    toolbar_icons.build_set("test", tmp_path, {"Find": ["edit-find"]}, [])

    assert [path.name for path in (output / "test").iterdir()] == ["edit-find.png"]


def test_main_builds_the_1995_and_2000_sets_from_the_navigation_archive(toolbar_icons, output, tmp_path):
    sources = tmp_path / "sources"
    for name in toolbar_icons.WINDOWS_95_ICONS:
        write_ico(sources / "Navigation Buttons/Windows 95" / f"{name}.ico")
    for name in toolbar_icons.WINDOWS_2000_ICONS:
        write_ico(sources / "Navigation Buttons/Windows 2000" / f"{name}.ico", frames=2 if name == "search_web" else 1)
    archive = tmp_path / "Navigation Buttons.zip"
    subprocess.run(["7z", "a", str(archive), "Navigation Buttons"], check=True, stdout=subprocess.DEVNULL, cwd=sources)

    toolbar_icons.main(str(archive))

    assert {folder.name: len(list(folder.glob("*.png"))) for folder in sorted(output.iterdir())} == {
        "1995": 8,
        "2000": 12,
    }


def test_script_without_archive_exits_with_index_error():
    result = subprocess.run(
        ["python3", str(REPO / "setup/make_toolbar_icons.py")], capture_output=True, text=True, check=False
    )

    assert (result.returncode, result.stderr.splitlines()[-1]) == (1, "IndexError: list index out of range")
