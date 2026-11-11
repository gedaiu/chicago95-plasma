import shutil
import subprocess

import pytest
from conftest import REPO

pytestmark = pytest.mark.skipif(not shutil.which("fc-match"), reason="needs fc-match")
RULE = REPO / "luna/fontconfig/61-chicago95-luna-fonts.conf"
SYSTEM_CONFIGURATION = "/etc/fonts/fonts.conf"


def installed_families():
    output = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True, check=False).stdout
    return {family.strip() for line in output.splitlines() for family in line.split(",")}


def matched_family(tmp_path, requested):
    configuration = tmp_path / "fonts.conf"
    configuration.write_text(
        '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd"><fontconfig>'
        f'<include ignore_missing="yes">{SYSTEM_CONFIGURATION}</include><include>{RULE}</include></fontconfig>'
    )
    output = subprocess.run(
        ["fc-match", "-f", "%{family}", requested],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "FONTCONFIG_FILE": str(configuration)},
        timeout=30,
        check=False,
    ).stdout
    return output.split(",")[0]


@pytest.mark.parametrize("requested", ["Franklin Gothic Medium", "Trebuchet MS", "Tahoma"])
def test_luna_font_alias_resolves_to_an_installed_family(tmp_path, requested):
    assert matched_family(tmp_path, requested) in installed_families()


def test_franklin_gothic_medium_prefers_libre_franklin_then_fira_sans_medium_noto_sans_and_dejavu_sans():
    """Libre Franklin is the open Franklin Gothic; Setup fetches it for the Luna look (fetch_libre_franklin)."""
    families = [
        line.strip()
        for line in RULE.read_text().split("Franklin Gothic Medium")[1].split("</prefer>")[0].split("<family>")[1:]
    ]

    assert [family.removesuffix("</family>") for family in families] == [
        "Libre Franklin",
        "Fira Sans Medium",
        "Noto Sans",
        "DejaVu Sans",
    ]


def test_trebuchet_ms_prefers_fira_sans_then_noto_sans_then_dejavu_sans():
    families = [
        line.strip() for line in RULE.read_text().split("Trebuchet MS")[1].split("</prefer>")[0].split("<family>")[1:]
    ]

    assert [family.removesuffix("</family>") for family in families] == ["Fira Sans", "Noto Sans", "DejaVu Sans"]
