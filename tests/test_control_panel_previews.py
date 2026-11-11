"""The Control Panel's previews on the Passwords pages: the log-on dialog and the loading screen are the
real QML screens (the theme under sddm/, the splash under splash/) loaded with the sheet's current values,
the branding preview is the 2000 banner the Shut Down tool draws for the log-on screen."""

import pytest
from conftest import REPO, load_script
from PySide6.QtCore import QObject


@pytest.fixture(scope="session")
def control_panel():
    return load_script("chicago95-control-panel")


def preview_of(control_panel, tab_name, applet="Passwords"):
    tab = control_panel.build_tab(applet, tab_name, {}, control_panel.Actions())
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
    root = preview.dialog()

    assert (errors(preview), root.property("modern"), "Welcome aboard" in texts(root)) == ([], False, True)


def test_log_on_preview_draws_the_2000_dialog_over_a_banner_with_the_branding(control_panel, qt_app):
    preview = preview_of(control_panel, "Log On")
    preview.refresh({"LOGIN_STYLE": "2000", "BANNER_TEXT": "Chicago 2000", "EDITION": "Home"})
    qt_app.processEvents()

    assert (
        errors(preview),
        preview.dialog().property("modern"),
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


def test_branding_preview_is_the_2000_banner_shrunk_to_the_sheet_and_follows_the_edition(control_panel, qt_app):
    preview = preview_of(control_panel, "Branding")
    preview.refresh({"EDITION": "Professional"})
    first = preview.pixmap().toImage()
    preview.refresh({"EDITION": "Server"})
    second = preview.pixmap().toImage()

    assert (first.width(), first.isNull(), first == second) == (control_panel.BrandingPreview.WIDTH, False, False)


def test_loading_preview_shows_the_2000_screen_at_stage_3_with_the_texts_chosen(control_panel, qt_app):
    preview = preview_of(control_panel, "Boot Screen", "Booting Screen")
    preview.refresh({"BOOT_STYLE": "2000", "LOADING_TEXT": "Loading Chicago...", "LOADING_FOOTER": "Bottom line"})
    qt_app.processEvents()
    root = preview.dialog()

    assert (
        errors(preview),
        root.property("modern"),
        root.property("stage"),
        {"Loading Chicago...", "Bottom line"} <= texts(root),
    ) == ([], True, 3, True)


def test_loading_preview_shows_the_classic_picture_for_the_classic_style(control_panel, qt_app):
    preview = preview_of(control_panel, "Boot Screen", "Booting Screen")
    preview.refresh({"BOOT_STYLE": "classic", "LOGIN_STYLE": "2000", "SPLASH_IMAGE": "classic"})
    qt_app.processEvents()
    settings = (preview.scratch / "splash/settings.js").read_text()

    assert (
        preview.dialog().property("modern"),
        'var style = "classic"' in settings,
        "background.png" in settings,
    ) == (False, True, True)


def test_the_boot_screen_preview_follows_its_own_style_as_soon_as_the_radio_changes(control_panel, qt_app, tmp_path):
    window = control_panel.ControlPanel(settings_path=tmp_path / "setup.conf")
    window.navigate(control_panel.HOME_PAGE + ("Booting Screen",))
    sheet = window.pages.currentWidget()
    (boot,) = sheet.settings_tabs
    boot.fields["BOOT_STYLE"][1]("2000")
    sheet.refresh_previews()
    qt_app.processEvents()

    assert boot.previews[0].dialog().property("modern") is True


def test_the_boot_screen_preview_defaults_to_the_saved_login_style_until_a_boot_style_is_chosen(control_panel, qt_app):
    tab = control_panel.build_tab("Booting Screen", "Boot Screen", {"LOGIN_STYLE": "2000"}, control_panel.Actions())
    (preview,) = tab.previews
    preview.refresh({"LOGIN_STYLE": "2000", **tab.values()})
    qt_app.processEvents()

    assert (tab.values()["BOOT_STYLE"], preview.dialog().property("modern")) == ("2000", True)


def test_qml_previews_are_the_screens_at_their_own_size_shrunk_to_fit_the_sheet(control_panel, qt_app):
    log_on, loading = control_panel.LogOnPreview(), control_panel.LoadingPreview()

    assert (log_on.size().toTuple(), loading.size().toTuple(), log_on.scale, loading.scale) == (
        (264, 150),
        (192, 144),
        0.6,
        0.6,
    )


def test_a_property_sheet_window_keeps_the_standard_size_whatever_its_pages_ask(control_panel, qt_app, tmp_path):
    from PySide6.QtWidgets import QLabel

    tab = control_panel.SettingsTab({}, control_panel.Actions())
    huge = QLabel("x")
    huge.setFixedSize(900, 900)
    tab.form.addRow(huge)
    page = control_panel.PropertiesPage("Display", [("Background", tab)], lambda changes: True)
    window = control_panel.PropertySheetWindow(page, None)

    assert (window.size().toTuple(), page.tabs.widget(0).widget() is tab) == (control_panel.SHEET_SIZE.toTuple(), True)


def test_previews_take_the_theme_and_pictures_from_the_saved_checkout_or_the_installed_copies(control_panel, tmp_path):
    (tmp_path / "install.sh").write_text("")
    (tmp_path / "sddm/Chicago95Plasma").mkdir(parents=True)

    assert (
        control_panel.repo_of({"REPO": str(tmp_path)}),
        control_panel.repo_of({"REPO": str(tmp_path / "gone")}),
        control_panel.sddm_theme_of({"REPO": str(tmp_path)}),
        control_panel.splash_of({"REPO": str(tmp_path / "gone")})
        in (control_panel.REPO_DIR / "splash/chicago95.splashscreen/contents/splash", control_panel.INSTALLED_SPLASH),
    ) == (tmp_path, control_panel.REPO_DIR, tmp_path / "sddm/Chicago95Plasma", True)


def test_the_control_panel_installed_outside_the_checkout_opens_passwords_with_working_previews(qt_app, tmp_path):
    """Installed, the program lives in ~/.local/bin, whose parent has no sddm/, splash/ or plasmoids/: the previews
    take them from the checkout named in setup.conf (REPO) or from the installed copies."""
    import importlib.machinery
    import importlib.util
    import shutil

    bin_folder = tmp_path / "local/bin"
    bin_folder.mkdir(parents=True)
    for tool in ("chicago95-control-panel", "chicago95-startmenu", "chicago95-shutdown"):
        shutil.copy(REPO / "bin" / tool, bin_folder / tool)
    loader = importlib.machinery.SourceFileLoader(
        "installed_control_panel", str(bin_folder / "chicago95-control-panel")
    )
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(module)
    settings = tmp_path / "setup.conf"
    settings.write_text(f"REPO={REPO}\nLOGIN_STYLE=2000\n")
    window = module.ControlPanel(settings_path=settings)
    window.open_applet("Passwords")
    sheet = window.pages.currentWidget()
    sheet.refresh_previews()
    qt_app.processEvents()
    previews = [preview for tab in sheet.settings_tabs for preview in tab.previews]
    qml_errors = [error.toString() for preview in previews if hasattr(preview, "errors") for error in preview.errors()]

    assert (module.REPO_DIR, len(previews), qml_errors) == (tmp_path / "local", 2, [])
