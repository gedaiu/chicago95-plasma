"""The Control Panel's Distro Setup: every name, text and logo the screens show, in one place, with a preview of
each screen (Start menu, log on, banner, boot page, after log on, Shut Down). The other pages keep their own
fields; an Apply on any of them shows on the others."""

import configparser

import pytest
from conftest import REPO, load_script
from PIL import Image

DISTRO_DEFAULTS = {
    "BANNER_TEXT": "Chicago95",
    "EDITION": "Professional",
    "TAGLINE": "Built on Linux Technology",
    "COMPANY": "KDE",
    "START_LOGO": "flag",
    "LOGIN_LOGO": "start",
    "COMPANY_LOGO": "text",
    "LOGIN_ICON": "keys",
    "START_TEXT": "Start",
    "LOGIN_TITLE": "Log On to %h",
    "LOGIN_MESSAGE": "Type a user name and password to log on.",
    "LOADING_TEXT": "Starting up...",
    "LOADING_FOOTER": "Chicago95 for KDE Plasma",
    "SPLASH_IMAGE": "classic",
    "BRANDING": "windows",
}


@pytest.fixture(scope="module")
def control_panel():
    return load_script("chicago95-control-panel")


def distro_tab(control_panel, settings=None):
    return control_panel.build_tab("Distro Setup", "Names and Logos", settings or {}, control_panel.Actions())


@pytest.fixture
def testix(monkeypatch, tmp_path):
    """This computer, as far as the Control Panel can tell: Testix Linux 7 with its logo icon."""
    (tmp_path / "os-release").write_text('NAME="Testix Linux"\nVERSION_ID=7\nLOGO=testix-logo\n')
    icon = tmp_path / "share/icons/hicolor/48x48/apps/testix-logo.png"
    icon.parent.mkdir(parents=True)
    Image.new("RGBA", (48, 48), "#3c6eb4").save(icon)
    monkeypatch.setenv("SETUP_OS_RELEASE", str(tmp_path / "os-release"))
    monkeypatch.setenv("SETUP_DATA_DIRS", str(tmp_path / "share"))
    return icon


@pytest.fixture
def window(control_panel, qt_app, tmp_path):
    ran = []
    actions = control_panel.Actions(
        start_process=lambda program, arguments: None,
        run_setup=lambda parent, command: ran.append(command),
        show_message=lambda parent, title, text: None,
        ask_to_apply=lambda parent: "cancel",
    )
    (tmp_path / "setup.conf").write_text(f"REPO={REPO}\n")
    return control_panel.ControlPanel(settings_path=tmp_path / "setup.conf", actions=actions)


def sheet(window, applet):
    return window.page_for(applet)


def field(page, key):
    tab = next(tab for tab in page.settings_tabs if key in tab.fields)
    return tab.fields[key]


def test_distro_setup_is_an_applet_of_its_own(control_panel):
    assert "Distro Setup" in control_panel.APPLET_BY_NAME


def test_distro_setup_holds_every_name_text_and_logo_with_the_windows_defaults(control_panel, qt_app):
    assert distro_tab(control_panel).values() == DISTRO_DEFAULTS


def test_distro_setup_previews_every_screen_the_names_show_on(control_panel, qt_app):
    assert [type(preview).__name__ for preview in distro_tab(control_panel).previews] == [
        "StartMenuPreview",
        "LogOnPreview",
        "BrandingPreview",
        "LoadingPreview",
        "AfterLogOnPreview",
        "ShutDownPreview",
    ]


def test_the_shut_down_preview_names_the_system_the_values_give(control_panel, qt_app):
    preview = control_panel.ShutDownPreview()
    preview.refresh({**DISTRO_DEFAULTS, "BANNER_TEXT": "Testix Linux 7"})
    rc = configparser.ConfigParser(interpolation=None)
    rc.read(preview.scratch / "config/chicago95rc")
    assert rc.get("Branding", "osName") == "Testix Linux 7"


def test_the_shut_down_preview_shows_the_dialog_the_shut_down_tool_draws(control_panel, qt_app):
    preview = control_panel.ShutDownPreview()
    preview.refresh(DISTRO_DEFAULTS)
    preview.process.waitForFinished(30000)
    qt_app.processEvents()
    assert preview.picture.pixmap().isNull() is False


def test_using_this_computers_system_names_it_after_the_distribution(control_panel, qt_app, testix):
    tab = distro_tab(control_panel)
    tab.distro_button.click()
    assert tab.values()["BANNER_TEXT"] == "Testix Linux 7"


def test_using_this_computers_system_puts_its_logo_on_the_start_button(control_panel, qt_app, testix):
    tab = distro_tab(control_panel)
    tab.distro_button.click()
    assert tab.values()["START_LOGO"] == str(testix)


def test_using_this_computers_system_remembers_the_choice(control_panel, qt_app, testix):
    tab = distro_tab(control_panel)
    tab.distro_button.click()
    assert tab.values()["BRANDING"] == "distro"


def test_windows_names_put_the_looks_names_back(control_panel, qt_app, testix):
    tab = distro_tab(control_panel, {"LOOK": "2001"})
    tab.distro_button.click()
    tab.windows_button.click()
    assert (tab.values()["BANNER_TEXT"], tab.values()["BRANDING"]) == ("Windows XP Professional", "windows")


def test_a_name_applied_on_distro_setup_shows_on_the_open_taskbar_page(window, qt_app):
    taskbar = sheet(window, "Taskbar")
    distro = sheet(window, "Distro Setup")
    field(distro, "BANNER_TEXT")[1]("Testix Linux 7")
    distro.apply()
    assert field(taskbar, "BANNER_TEXT")[0]() == "Testix Linux 7"


def test_an_edition_applied_on_the_passwords_page_shows_on_distro_setup(window, qt_app):
    distro = sheet(window, "Distro Setup")
    passwords = sheet(window, "Passwords")
    field(passwords, "EDITION")[1]("Studio")
    passwords.apply()
    assert field(distro, "EDITION")[0]() == "Studio"


def test_an_open_page_keeps_its_own_changes_when_another_page_applies(window, qt_app):
    taskbar = sheet(window, "Taskbar")
    distro = sheet(window, "Distro Setup")
    field(taskbar, "START_TEXT")[1]("Go")
    field(distro, "BANNER_TEXT")[1]("Testix Linux 7")
    distro.apply()
    assert (field(taskbar, "START_TEXT")[0](), field(taskbar, "BANNER_TEXT")[0]()) == ("Go", "Testix Linux 7")


def test_an_open_page_with_its_own_changes_still_offers_to_apply_them(window, qt_app):
    taskbar = sheet(window, "Taskbar")
    distro = sheet(window, "Distro Setup")
    field(taskbar, "START_TEXT")[1]("Go")
    field(distro, "BANNER_TEXT")[1]("Testix Linux 7")
    distro.apply()
    assert taskbar.changed_values() == {"START_TEXT": "Go"}


def test_the_company_reinstalls_the_shut_down_dialogs_branding(control_panel):
    assert "startmenu" in control_panel.COMPONENTS_BY_KEY["COMPANY"]


def test_the_xp_log_on_banner_preview_names_the_system(control_panel, qt_app):
    from PySide6.QtCore import QObject

    preview = control_panel.BrandingPreview()
    preview.refresh({**DISTRO_DEFAULTS, "LOGIN_STYLE": "luna", "BANNER_TEXT": "Testix Linux 7"})
    wordmark = preview.wordmark.rootObject().findChild(QObject, "wordmark")
    assert wordmark.property("name") == "Testix Linux 7"


def test_the_xp_start_button_preview_shows_the_chosen_logo(control_panel, qt_app, testix):
    from PySide6.QtCore import QObject

    preview = control_panel.StartMenuPreview()
    preview.refresh({**DISTRO_DEFAULTS, "LOOK": "luna", "TASKBAR_STYLE": "luna", "START_LOGO": str(testix)})
    qt_app.processEvents()
    button = preview.button.rootObject().findChild(QObject, "startButton")
    assert (button.property("customLogo"), button.property("logoSource").toLocalFile()) == (True, str(testix))


@pytest.mark.parametrize("button", ["distro_button", "windows_button"])
def test_the_names_from_buttons_fit_their_captions(control_panel, qt_app, button):
    widget = getattr(distro_tab(control_panel), button)
    assert widget.width() >= widget.sizeHint().width()


def test_the_control_panel_runs_the_tools_beside_it_not_an_older_installed_copy(control_panel):
    assert control_panel.tool_path("chicago95-shutdown") == str(REPO / "bin/chicago95-shutdown")


def test_a_tool_missing_beside_the_control_panel_comes_from_the_installed_ones(control_panel, monkeypatch, tmp_path):
    installed = tmp_path / ".local/bin/chicago95-newtool"
    installed.parent.mkdir(parents=True)
    installed.touch()
    monkeypatch.setenv("HOME", str(tmp_path))
    assert control_panel.tool_path("chicago95-newtool") == str(installed)


def test_the_xp_log_on_banner_preview_shows_the_whole_edition_line(control_panel, qt_app):
    from PySide6.QtCore import QObject, QRectF

    preview = control_panel.BrandingPreview()
    preview.refresh(
        {**DISTRO_DEFAULTS, "LOGIN_STYLE": "luna", "BANNER_TEXT": "Fedora Linux 44", "EDITION": "Workstation"}
    )
    qt_app.processEvents()
    edition = preview.wordmark.rootObject().findChild(QObject, "edition")
    bottom = edition.mapRectToScene(QRectF(0, 0, edition.width(), edition.height())).bottom()
    assert bottom <= preview.height()
