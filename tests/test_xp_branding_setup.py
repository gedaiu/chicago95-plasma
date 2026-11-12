"""Setup's XP log-on screen branding: the logo, name, company and edition go into the login theme's theme.conf, and
the logo next to the theme (the greeter's user cannot read the home folder)."""

import configparser

import pytest
from conftest import REPO, run_bash_with_steps

BRANDING = "SETUP_BANNER_TEXT=Windows2026 SETUP_COMPANY=KDE SETUP_EDITION=Professional"


def theme_conf(tmp_path, style):
    lines = run_bash_with_steps(tmp_path, f"SETUP_LOGIN_STYLE={style} {BRANDING} sddm_theme_conf")
    settings = configparser.ConfigParser(interpolation=None)
    settings.read_string("\n".join(lines))
    return dict(settings["General"])


def test_the_xp_login_theme_carries_the_users_name_company_edition_and_logo_file(tmp_path):
    settings = theme_conf(tmp_path, "luna")

    assert {key: settings[key] for key in ("brandtext", "company", "edition", "brandlogo")} == {
        "brandtext": "Windows2026",
        "company": "KDE",
        "edition": "Professional",
        "brandlogo": "brand-logo.png",
    }


@pytest.mark.parametrize("style", ["classic", "2000"])
def test_the_other_login_styles_carry_no_xp_branding(tmp_path, style):
    assert theme_conf(tmp_path, style)["brandtext"] == ""


def test_the_xp_login_copies_the_logo_next_to_the_theme(tmp_path):
    lines = run_bash_with_steps(
        tmp_path,
        f"SETUP_DRY_RUN=1; SETUP_LOG=$HOME/log; SETUP_LOGIN_STYLE=luna; {BRANDING.replace(' ', '; ')}; "
        "ui_sudo() { printf '%s\\n' \"${@:2}\"; return 1; }; ui_message() { :; }; step_sddm",
    )

    assert any(line.startswith("sudo cp ") and line.endswith("/brand-logo.png") for line in lines)


def test_the_source_theme_lists_the_branding_keys_setup_fills_in():
    text = (REPO / "sddm/Chicago95Plasma/theme.conf").read_text()

    assert all(f"\n{key}=" in text for key in ("brandText", "brandLogo", "company", "edition"))


@pytest.mark.parametrize("key", ["BANNER_TEXT", "LOGIN_LOGO", "COMPANY", "EDITION"])
def test_a_branding_change_in_the_control_panel_reinstalls_the_login_and_boot_screens(key):
    from conftest import load_script

    components = load_script("chicago95-control-panel").COMPONENTS_BY_KEY[key]

    assert {"splash", "sddm", "plymouth"} <= set(components)
