"""The Control Panel's previews on the Passwords pages: the log-on dialog and the loading screen are the
real QML screens (the theme under sddm/, the splash under splash/) loaded with the sheet's current values,
the branding preview is the 2000 banner the Shut Down tool draws for the log-on screen."""

import pytest
from conftest import load_script
from PySide6.QtCore import QObject


@pytest.fixture(scope="session")
def control_panel():
    return load_script("chicago95-control-panel")


def preview_of(control_panel, tab_name):
    tab = control_panel.build_tab("Passwords", tab_name, {}, control_panel.Actions())
    (preview,) = tab.previews
    return preview


def texts(root):
    return {child.property("text") for child in root.findChildren(QObject) if isinstance(child.property("text"), str)}


def errors(preview):
    return [error.toString() for error in preview.errors()]


def test_log_on_preview_draws_the_classic_dialog_with_the_typed_title(control_panel, qt_app):
    preview = preview_of(control_panel, "Log On")
    preview.refresh({"LOGIN_STYLE": "classic", "LOGIN_TITLE": "Welcome aboard"})
    qt_app.processEvents()
    root = preview.rootObject()

    assert (errors(preview), root.property("modern"), "Welcome aboard" in texts(root)) == ([], False, True)


def test_log_on_preview_draws_the_2000_dialog_over_a_banner_with_the_branding(control_panel, qt_app):
    preview = preview_of(control_panel, "Log On")
    preview.refresh({"LOGIN_STYLE": "2000", "BANNER_TEXT": "Chicago 2000", "EDITION": "Home"})
    qt_app.processEvents()

    assert (
        errors(preview),
        preview.rootObject().property("modern"),
        (preview.scratch / "theme/brand-banner.png").exists(),
    ) == ([], True, True)


def test_log_on_preview_paints_teal_for_the_classic_style_and_blue_for_2000(control_panel, qt_app):
    preview = preview_of(control_panel, "Log On")
    corners = []
    for style in ("classic", "2000"):
        preview.refresh({"LOGIN_STYLE": style})
        preview.show()
        qt_app.processEvents()
        corners.append(preview.grabFramebuffer().pixelColor(2, 2).name())
    preview.close()

    assert corners == ["#008080", "#3a6ea5"]


def test_branding_preview_is_the_411_wide_2000_banner_and_follows_the_edition(control_panel, qt_app):
    preview = preview_of(control_panel, "Branding")
    preview.refresh({"EDITION": "Professional"})
    first = preview.pixmap().toImage()
    preview.refresh({"EDITION": "Server"})
    second = preview.pixmap().toImage()

    assert (first.width(), first.isNull(), first == second) == (411, False, False)


def test_loading_preview_shows_the_2000_screen_at_stage_3_with_the_texts_chosen(control_panel, qt_app):
    preview = preview_of(control_panel, "Loading Screen")
    preview.refresh({"LOGIN_STYLE": "2000", "LOADING_TEXT": "Loading Chicago...", "LOADING_FOOTER": "Bottom line"})
    qt_app.processEvents()
    root = preview.rootObject()

    assert (
        errors(preview),
        root.property("modern"),
        root.property("stage"),
        {"Loading Chicago...", "Bottom line"} <= texts(root),
    ) == ([], True, 3, True)


def test_loading_preview_shows_the_classic_picture_for_the_classic_style(control_panel, qt_app):
    preview = preview_of(control_panel, "Loading Screen")
    preview.refresh({"LOGIN_STYLE": "classic", "SPLASH_IMAGE": "classic"})
    qt_app.processEvents()
    settings = (preview.scratch / "splash/settings.js").read_text()

    assert (
        preview.rootObject().property("modern"),
        'var style = "classic"' in settings,
        "background.png" in settings,
    ) == (False, True, True)


def test_a_sheet_refreshes_every_tabs_previews_with_the_values_of_all_its_tabs(control_panel, qt_app, tmp_path):
    window = control_panel.ControlPanel(settings_path=tmp_path / "setup.conf")
    window.navigate(control_panel.HOME_PAGE + ("Passwords",))
    sheet = window.pages.currentWidget()
    log_on = next(tab for tab in sheet.settings_tabs if "LOGIN_STYLE" in tab.fields)
    loading = next(tab for tab in sheet.settings_tabs if "LOADING_TEXT" in tab.fields)
    log_on.fields["LOGIN_STYLE"][1]("2000")
    sheet.refresh_previews()
    qt_app.processEvents()

    assert loading.previews[0].rootObject().property("modern") is True
