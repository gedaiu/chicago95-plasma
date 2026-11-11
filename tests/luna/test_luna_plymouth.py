import importlib.util
import re
from configparser import ConfigParser
from pathlib import Path

import pytest
from conftest import REPO
from PIL import Image

THEME = REPO / "luna/plymouth/Chicago95-XP"
MAKER = REPO / "luna/plymouth/make_assets.py"
INSTALLED_FOLDER = "/usr/share/plymouth/themes/Chicago95-XP"


def load_maker():
    spec = importlib.util.spec_from_file_location("make_assets", MAKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def theme_file():
    parser = ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(THEME / "Chicago95-XP.plymouth")
    return parser


def test_plymouth_file_names_the_script_module_and_the_installed_folder(theme_file):
    assert dict(theme_file["Plymouth Theme"]) == {
        "Name": "Chicago95 XP Boot Screen",
        "Description": "The XP start-up screen: wordmark on black with a sliding three-block progress bar",
        "ModuleName": "script",
    } and dict(theme_file["script"]) == {
        "ImageDir": INSTALLED_FOLDER,
        "ScriptFile": f"{INSTALLED_FOLDER}/Chicago95-XP.script",
    }


def test_script_file_named_by_the_plymouth_file_exists_in_the_theme(theme_file):
    assert (THEME / Path(theme_file["script"]["ScriptFile"]).name).is_file()


def test_script_references_only_images_that_exist():
    script = (THEME / "Chicago95-XP.script").read_text()
    referenced = set(re.findall(r'Image\("([^"]+)"\)', script))
    assert (sorted(referenced), [name for name in referenced if not (THEME / name).is_file()]) == (
        sorted(f"{name}{suffix}.png" for name in ("logo", "trough", "block") for suffix in ("", "@2x")),
        [],
    )


@pytest.mark.parametrize("name", ["logo", "trough", "block"])
@pytest.mark.parametrize("suffix, multiplier", [("", 1), ("@2x", 2)], ids=["1x", "2x"])
def test_generated_pictures_have_the_sizes_the_maker_declares(name, suffix, multiplier):
    declared = load_maker().SIZES[name]
    with Image.open(THEME / f"{name}{suffix}.png") as picture:
        assert picture.size == (declared[0] * multiplier, declared[1] * multiplier)


def test_logo_is_transparent_around_the_lettering_and_trough_is_black_inside():
    with Image.open(THEME / "logo.png") as logo, Image.open(THEME / "trough.png") as trough:
        assert (logo.getpixel((0, 0))[3], trough.getpixel((60, 7))) == (0, (0, 0, 0, 255))


def test_regenerating_the_pictures_reproduces_the_committed_files(tmp_path):
    maker = load_maker()
    maker.FOLDER = tmp_path
    maker.write_all()
    differing = [
        path.name
        for path in tmp_path.glob("*.png")
        if Image.open(path).tobytes() != Image.open(THEME / path.name).tobytes()
    ]
    assert differing == []
