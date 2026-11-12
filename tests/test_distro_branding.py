"""The running distribution's branding (lib/chicago95distro.py), read from os-release as data and from the icon
themes: its name and version, edition, company and logos, as Setup and the Control Panel's Distro Setup use them."""

import subprocess
import sys

import chicago95distro as distro
import pytest
from conftest import REPO
from PIL import Image

OS_RELEASE = """NAME="Testix Linux"
VERSION="7 (Studio Edition)"
ID=testix
VERSION_ID=7
PRETTY_NAME="Testix Linux 7 (Studio Edition)"
VARIANT="Studio Edition"
LOGO=testix-logo-icon
"""


def png(path, size):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (size, size), "#3c6eb4").save(path)
    return path


@pytest.fixture
def system(tmp_path):
    """An os-release and a data dir with the logo icon at 16, 48 and 256px and a wide wordmark."""
    (tmp_path / "os-release").write_text(OS_RELEASE)
    share = tmp_path / "share"
    for size in (16, 48, 256):
        png(share / f"icons/hicolor/{size}x{size}/apps/testix-logo-icon.png", size)
    png(share / "pixmaps/testix-logo.png", 64)
    return tmp_path


def branding(system, text=OS_RELEASE):
    (system / "os-release").write_text(text)
    return distro.distro_branding(distro.read_os_release(system / "os-release"), [system / "share"])


def test_the_name_is_the_distributions_name_and_version(system):
    assert branding(system)["BANNER_TEXT"] == "Testix Linux 7"


def test_the_edition_is_the_variant_without_the_word_edition(system):
    assert branding(system)["EDITION"] == "Studio"


def test_the_company_is_the_first_word_of_the_name_without_a_vendor(system):
    assert branding(system)["COMPANY"] == "Testix"


def test_the_company_is_the_vendor_when_os_release_names_one(system):
    assert branding(system, OS_RELEASE + 'VENDOR_NAME="Testix Project"\n')["COMPANY"] == "Testix Project"


def test_the_loading_screen_footer_is_the_pretty_name(system):
    assert branding(system)["LOADING_FOOTER"] == "Testix Linux 7 (Studio Edition)"


def test_the_start_logo_is_the_smallest_picture_that_stays_sharp_on_a_2x_screen(system):
    assert branding(system)["START_LOGO"] == str(system / "share/icons/hicolor/48x48/apps/testix-logo-icon.png")


def test_the_start_logo_is_the_scalable_logo_when_there_is_one(system):
    svg = system / "share/icons/hicolor/scalable/apps/testix-logo-icon.svg"
    svg.parent.mkdir(parents=True)
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"/>')
    assert branding(system)["START_LOGO"] == str(svg)


def test_the_login_logo_is_the_largest_picture_of_the_logo_icon(system):
    assert branding(system)["LOGIN_LOGO"] == str(system / "share/icons/hicolor/256x256/apps/testix-logo-icon.png")


def test_the_company_logo_is_the_distributions_wordmark(system):
    assert branding(system)["COMPANY_LOGO"] == str(system / "share/pixmaps/testix-logo.png")


def test_without_a_wordmark_there_is_no_company_logo(system):
    (system / "share/pixmaps/testix-logo.png").unlink()
    assert "COMPANY_LOGO" not in branding(system)


def test_without_a_logo_icon_there_are_no_logos(system):
    found = branding(system, OS_RELEASE.replace("LOGO=testix-logo-icon\n", ""))
    assert [key for key in ("START_LOGO", "LOGIN_LOGO") if key in found] == []


def test_a_missing_os_release_gives_no_branding(tmp_path):
    assert distro.distro_branding(distro.read_os_release(tmp_path / "none"), [tmp_path]) == {}


def test_os_release_is_read_as_text_never_run(system):
    found = branding(system, "NAME=\"$(touch hacked) `id`\"\nVERSION_ID='1'\n")
    assert found["BANNER_TEXT"] == "$(touch hacked) `id` 1"


def test_the_command_prints_one_tab_separated_line_per_value(system):
    output = subprocess.run(
        [
            sys.executable,
            str(REPO / "lib/chicago95distro.py"),
            "--os-release",
            str(system / "os-release"),
            "--data-dirs",
            str(system / "share"),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "BANNER_TEXT\tTestix Linux 7" in output.splitlines()


def test_the_distributions_own_hicolor_pictures_win_over_another_themes_drawing(system):
    other = system / "share/icons/Other/16x16/places/testix-logo-icon.svg"
    other.parent.mkdir(parents=True)
    other.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"/>')
    assert branding(system)["LOGIN_LOGO"] == str(system / "share/icons/hicolor/256x256/apps/testix-logo-icon.png")


def test_another_themes_drawing_is_used_when_hicolor_has_none(system):
    for size in (16, 48, 256):
        (system / f"share/icons/hicolor/{size}x{size}/apps/testix-logo-icon.png").unlink()
    other = png(system / "share/icons/Other/32x32/places/testix-logo-icon.png", 32)
    assert branding(system)["LOGIN_LOGO"] == str(other)


def test_the_start_logo_is_the_largest_picture_when_none_is_32px(system):
    for size in (48, 256):
        (system / f"share/icons/hicolor/{size}x{size}/apps/testix-logo-icon.png").unlink()
    assert branding(system)["START_LOGO"] == str(system / "share/icons/hicolor/16x16/apps/testix-logo-icon.png")
