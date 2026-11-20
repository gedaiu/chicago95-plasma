"""Firefox's own controls drawn in the look, from a userChrome.css that Setup imports into the profile."""

import shutil
import subprocess

import firefox_chrome
import pytest
from conftest import REPO, run_bash_with_steps
from PIL import Image
from test_wine_look import SCHEME_1998

IMPORT = '@import url("chicago95-controls.css");'


def lines(bevel):
    return firefox_chrome.bevel_lines(SCHEME_1998, bevel)


def setup_firefox(tmp_path, look="SETUP_WIDGET_STYLE=classic"):
    run_bash_with_steps(
        tmp_path,
        f"SETUP_DRY_RUN=0; MANIFEST={tmp_path}/manifest; {look}; SETUP_FIREFOX_PROFILE={tmp_path}; theme_firefox",
    )
    return (tmp_path / "chrome/userChrome.css").read_text()


def test_raised_bevel_is_white_and_light_over_black_and_shadow():
    assert firefox_chrome.raised(lines("1995")) == (
        "inset -1px -1px #000000, inset 1px 1px #ffffff, inset -2px -2px #808080, inset 2px 2px #dfdfdf"
    )


def test_default_button_draws_a_black_ring_outside_its_bevel():
    assert firefox_chrome.raised(lines("1995"), outline=1).startswith("inset 0 0 0 1px #000000, inset -2px -2px")


def test_sunken_field_is_shadow_and_black_over_white_and_light():
    assert firefox_chrome.sunken(lines("1995")) == (
        "inset 1px 1px #808080, inset -1px -1px #ffffff, inset 2px 2px #000000, inset -2px -2px #dfdfdf"
    )


def test_the_2000_bevel_draws_its_dark_line_in_404040():
    assert lines("2000")["dark"] == "#404040"


def test_controls_use_no_data_images_which_firefoxs_own_windows_refuse():
    assert "data:" not in firefox_chrome.user_chrome(SCHEME_1998, "1995")


def test_firefox_prefs_let_the_profile_restyle_its_controls():
    assert 'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);' in (
        (REPO / "config/firefox-user.js").read_text()
    )


def test_setup_writes_the_controls_next_to_user_chrome(tmp_path):
    setup_firefox(tmp_path)
    assert "radio-check" in (tmp_path / "chrome/chicago95-controls.css").read_text()


def test_setup_imports_the_controls_first_and_keeps_the_users_own_rules(tmp_path):
    (tmp_path / "chrome").mkdir()
    (tmp_path / "chrome/userChrome.css").write_text("#nav-bar { color: red; }\n")
    assert setup_firefox(tmp_path).splitlines() == [IMPORT, "#nav-bar { color: red; }"]


def test_setup_run_twice_imports_the_controls_once(tmp_path):
    setup_firefox(tmp_path)
    assert setup_firefox(tmp_path).splitlines() == [IMPORT]


def test_luna_look_takes_the_classic_controls_out(tmp_path):
    setup_firefox(tmp_path)
    user_chrome = setup_firefox(tmp_path, look="SETUP_WIDGET_STYLE=luna")
    assert (IMPORT in user_chrome, (tmp_path / "chrome/chicago95-controls.css").exists()) == (False, False)


def test_setup_run_twice_writes_each_firefox_pref_once(tmp_path):
    script = f"SETUP_DRY_RUN=0; MANIFEST={tmp_path}/manifest; SETUP_FIREFOX_PROFILE={tmp_path}; step_firefox"
    (tmp_path / "user.js").write_text('user_pref("my.own", 1);\n')
    run_bash_with_steps(tmp_path, f"{script}; {script}")
    written = (tmp_path / "user.js").read_text().splitlines()
    assert (written.count('user_pref("browser.display.use_system_colors", true);'), written[0]) == (
        1,
        'user_pref("my.own", 1);',
    )


def test_aero_controls_replace_classic_sheet_and_keep_profile_rules(tmp_path):
    setup_firefox(tmp_path)
    with (tmp_path / "chrome/userChrome.css").open("a") as sheet:
        sheet.write("#nav-bar { color: red; }\n")
    assert setup_firefox(tmp_path, "SETUP_WIDGET_STYLE=aero").splitlines() == [IMPORT, "#nav-bar { color: red; }"]
    installed = tmp_path / "chrome/chicago95-controls.css"
    assert installed.read_bytes() == (REPO / "aero/firefox-controls.css").read_bytes()


@pytest.mark.skipif(not shutil.which("firefox"), reason="Firefox is required to render browser controls")
def test_firefox_draws_the_installed_aero_dialog_border_and_gradient(tmp_path):
    setup_firefox(tmp_path, "SETUP_WIDGET_STYLE=aero")
    (tmp_path / "user.js").write_text('user_pref("layout.css.devPixelsPerPx", "1.0");\n')
    page, shot = tmp_path / "controls.html", tmp_path / "controls.png"
    page.write_text(
        '<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="chrome/userChrome.css">'
        "<style>dialog{position:static;margin:12px;border:0;padding:0}"
        "button{width:100px;height:28px;margin:0 3px}</style>"
        "<dialog open><button>OK</button><button disabled>Apply</button></dialog>"
    )
    subprocess.run(
        [
            "firefox",
            "--headless",
            "--no-remote",
            "--profile",
            tmp_path,
            "--window-size",
            "320,90",
            "--screenshot",
            shot,
            page.as_uri(),
        ],
        check=True,
        timeout=45,
        capture_output=True,
    )
    with Image.open(shot) as im:
        border, top, bottom = (im.getpixel((32, y))[:3] for y in (12, 15, 36))
    assert border == (112, 112, 112)
    assert top[0] > bottom[0] + 30 and top[0] == top[1] == top[2]
