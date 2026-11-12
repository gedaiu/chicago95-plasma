"""The remaining branches of the small scripts: the askpass screenshot failure, the splash picture errors,
the background tile errors, the no-break space fixer on fonts without the glyphs to fix, the Plasma style's
--base copy, the log-on preview stand-ins and the update check's git failures."""

import importlib.util
import json
import os
import subprocess
import sys
from datetime import UTC, datetime

import chicago95update
import login_preview
import pytest
from conftest import REPO, load_script
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont


def user_base():
    return subprocess.run(
        [sys.executable, "-m", "site", "--user-base"], capture_output=True, text=True, check=True
    ).stdout.strip()


def run_python(arguments, home):
    return subprocess.run(
        [sys.executable, *map(str, arguments)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=dict(os.environ, HOME=str(home), QT_QPA_PLATFORM="offscreen", PYTHONUSERBASE=user_base()),
    )


def load_hyphenated(path):
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_font(path, characters):
    """A TrueType font of empty glyphs; characters maps code point to (glyph name, advance width)."""
    names = [".notdef", *dict.fromkeys(name for name, _width in characters.values())]
    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder(names)
    builder.setupCharacterMap({code: name for code, (name, _width) in characters.items()})
    empty = TTGlyphPen(None).glyph()
    builder.setupGlyf({name: empty for name in names})
    widths = {name: width for name, width in characters.values()}
    builder.setupHorizontalMetrics({name: (widths.get(name, 500), 0) for name in names})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({"familyName": "Test", "styleName": "Regular"})
    builder.setupOS2()
    builder.setupPost()
    builder.save(path)
    return path


@pytest.fixture(scope="module")
def font_fixer():
    return load_hyphenated(REPO / "setup/fix-font-spaces.py")


def test_askpass_screenshot_exits_with_one_when_the_picture_cannot_be_saved(tmp_path):
    result = run_python(
        [REPO / "bin/chicago95-askpass", "--screenshot", tmp_path / "missing-folder/askpass.png"], tmp_path
    )

    assert result.returncode == 1


def test_askpass_main_returns_one_when_the_screenshot_cannot_be_saved(qt_app, tmp_path):
    askpass = load_script("chicago95-askpass")

    assert askpass.main(["chicago95-askpass", "--screenshot", str(tmp_path / "missing-folder/askpass.png")]) == 1


def test_splash_image_stops_with_the_qml_errors_of_a_broken_splash(tmp_path):
    splash = tmp_path / "splash"
    splash.mkdir()
    (splash / "Splash.qml").write_text("import QtQuick 2.15\nItem { this is not qml }\n")

    result = run_python(
        [REPO / "bin/chicago95-splash-image", "--splash", splash, "--out", tmp_path / "out.png"], tmp_path
    )

    assert (result.returncode, "Splash.qml" in result.stderr, (tmp_path / "out.png").exists()) == (1, True, False)


def test_splash_image_stops_when_the_picture_cannot_be_written(tmp_path):
    splash = tmp_path / "splash"
    splash.mkdir()
    (splash / "Splash.qml").write_text("import QtQuick 2.15\nItem { property int stage: 0 }\n")
    out = tmp_path / "missing-folder/out.png"

    result = run_python(
        [REPO / "bin/chicago95-splash-image", "--splash", splash, "--size", "40x30", "--out", out], tmp_path
    )

    assert (result.returncode, f"could not write {out}" in result.stderr) == (1, True)


def test_splash_image_module_loads_without_running_main():
    module = load_script("chicago95-splash-image")

    assert module.SPLASH.name == "splash"


def test_background_pattern_raises_when_the_tile_cannot_be_written(tmp_path, qt_app):
    background_pattern = load_hyphenated(REPO / "setup/background_pattern.py")

    with pytest.raises(SystemExit, match="cannot write"):
        background_pattern.pattern_png(
            background_pattern.PATTERNS["dots"], "#008080", tmp_path / "missing-folder/tile.png"
        )


def test_background_pattern_script_writes_the_tile_named_on_its_command_line(tmp_path):
    tile = tmp_path / "tile.png"

    result = run_python([REPO / "setup/background_pattern.py", "grid", "#008080", tile], tmp_path)

    assert (result.returncode, tile.stat().st_size > 0) == (0, True)


def test_font_fixer_leaves_a_font_whose_no_break_space_shares_the_glyph_of_its_space(font_fixer, tmp_path):
    font = build_font(tmp_path / "shared.ttf", {0x20: ("space", 273), 0xA0: ("space", 273)})

    assert font_fixer.fix_no_break_space(font) is None


def test_font_fixer_leaves_a_font_without_a_no_break_space(font_fixer, tmp_path):
    font = build_font(tmp_path / "no-nbsp.ttf", {0x20: ("space", 273)})

    assert font_fixer.fix_no_break_space(font) is None


def test_font_fixer_leaves_a_font_whose_two_spaces_are_equally_wide(font_fixer, tmp_path):
    font = build_font(tmp_path / "equal.ttf", {0x20: ("space", 273), 0xA0: ("nbsp", 273)})

    assert font_fixer.fix_no_break_space(font) is None


def test_font_fixer_widens_the_no_break_space_of_a_truetype_font(font_fixer, tmp_path):
    font = build_font(tmp_path / "narrow.ttf", {0x20: ("space", 273), 0xA0: ("nbsp", 91)})

    change = font_fixer.fix_no_break_space(font)

    hmtx = TTFont(font)["hmtx"]
    assert (change, hmtx["nbsp"][0], list(font.parent.glob("*.chicago95-new"))) == ((91, 273), 273, [])


def test_font_fixer_main_prints_each_change_and_skips_the_fonts_that_need_none(font_fixer, tmp_path, capsys):
    narrow = build_font(tmp_path / "narrow.ttf", {0x20: ("space", 273), 0xA0: ("nbsp", 91)})
    fine = build_font(tmp_path / "fine.ttf", {0x20: ("space", 273), 0xA0: ("nbsp", 273)})

    assert (font_fixer.main([str(narrow), str(fine)]), capsys.readouterr().out) == (
        0,
        f"{narrow}: no-break space 91 -> 273\n",
    )


def test_plasma_style_copies_the_base_theme_and_writes_its_metadata(tmp_path):
    base = tmp_path / "base"
    (base / "icons").mkdir(parents=True)
    (base / "icons/stale.svg").write_text("")
    (base / "widgets").mkdir()
    (base / "colors~").write_text("")
    (base / "metadata.desktop").write_text("")
    out = tmp_path / "out"
    out.mkdir()
    (out / "previous-run.txt").write_text("")

    result = run_python([REPO / "plasma-style/make_chicago95_plasmastyle.py", "--out", out, "--base", base], tmp_path)

    metadata = json.loads((out / "metadata.json").read_text())
    assert (
        result.returncode,
        metadata["KPlugin"]["Id"],
        sorted(
            p.name
            for p in out.iterdir()
            if p.name in ("icons", "colors~", "metadata.desktop", "widgets", "previous-run.txt")
        ),
    ) == (
        0,
        "Chicago95",
        ["widgets"],
    )


def test_greeter_reports_what_the_machine_can_do_and_ignores_every_action(qt_app):
    greeter = login_preview.Greeter("WINDOWS", can_sleep=False)
    greeter.suspend()
    greeter.hibernate()
    greeter.login("user", "secret", 0)
    greeter.powerOff()
    greeter.reboot()

    assert (greeter.hostName, greeter.canSuspend, greeter.canHibernate) == ("WINDOWS", False, False)


def test_users_list_the_names_and_the_last_user(qt_app):
    users = login_preview.Users(["ann", "bob"], "bob")

    assert ([users.item(row).data(login_preview.NAME_ROLE) for row in range(users.rowCount())], users.lastUser) == (
        ["ann", "bob"],
        "bob",
    )


def test_sessions_list_the_names_and_start_at_the_first(qt_app):
    sessions = login_preview.Sessions(["Plasma"])

    assert (sessions.item(0).data(login_preview.NAME_ROLE), sessions.lastIndex) == ("Plasma", 0)


def test_keyboard_offers_its_layouts_and_remembers_the_chosen_one_and_the_lock_keys(qt_app):
    keyboard = login_preview.Keyboard([("us", "English (US)"), ("ro", "Romanian")], caps_lock=True)
    layouts_changed, locks_changed = [], []
    keyboard.currentLayoutChanged.connect(lambda: layouts_changed.append(True))
    keyboard.lockChanged.connect(lambda: locks_changed.append(True))
    keyboard.numLock = True
    keyboard.currentLayout = 1

    assert (
        [(layout.shortName, layout.longName) for layout in keyboard.layouts],
        keyboard.capsLock,
        keyboard.numLock,
        keyboard.currentLayout,
        len(layouts_changed),
        len(locks_changed),
    ) == ([("us", "English (US)"), ("ro", "Romanian")], True, True, 1, 1, 1)


@pytest.fixture
def theme_source(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "main.qml").write_text("")
    (source / "theme.conf").write_text("[General]\n# comment\nfont=Test\nsize=3\n")
    return source


def test_theme_settings_read_the_general_values_and_apply_the_overrides(theme_source):
    assert login_preview.theme_settings(theme_source, size="9") == {"font": "Test", "size": "9"}


def test_prepare_login_theme_copies_the_banner_and_the_icon_beside_the_theme(theme_source, tmp_path, monkeypatch):
    monkeypatch.setattr(login_preview, "UI_FONT", tmp_path / "no-such-font.otf")
    banner, icon, folder = tmp_path / "banner.png", tmp_path / "me.jpg", tmp_path / "preview"
    banner.write_bytes(b"banner")
    icon.write_bytes(b"icon")

    main_qml = login_preview.prepare_login_theme(theme_source, folder, banner=banner, icon=icon)

    assert (
        main_qml,
        sorted(p.name for p in (folder / "theme").iterdir()),
        (folder / "imports/SddmComponents/qmldir").exists(),
    ) == (
        folder / "theme/main.qml",
        ["brand-banner.png", "login-icon.jpg", "main.qml", "theme.conf"],
        True,
    )


def test_prepare_login_theme_adds_the_ui_font_when_installed(theme_source, tmp_path, monkeypatch):
    font = tmp_path / "MSW98UI-Regular.otf"
    font.write_bytes(b"font")
    monkeypatch.setattr(login_preview, "UI_FONT", font)

    login_preview.prepare_login_theme(theme_source, tmp_path / "preview")

    assert sorted(p.name for p in (tmp_path / "preview/theme").iterdir()) == [
        "MSW98UI-Regular.otf",
        "main.qml",
        "theme.conf",
    ]


def test_login_context_gives_the_theme_what_sddm_would_marked_as_a_preview(theme_source, qt_app):
    """previewMode keeps the XP Welcome screen from looking up the real logged-on users."""
    context = login_preview.login_context(theme_source, host_name="BOX", size="7")

    assert (
        context["config"],
        context["sddm"].hostName,
        context["userModel"].lastUser,
        context["keyboard"].capsLock,
    ) == (
        {"font": "Test", "size": "7", "previewMode": True},
        "BOX",
        "user",
        False,
    )


def test_origin_of_falls_back_to_the_project_when_git_cannot_start(tmp_path):
    assert chicago95update.origin_of(str(tmp_path), git=str(tmp_path / "no-such-git")) == chicago95update.PROJECT_ORIGIN


def test_update_check_reports_only_once_when_git_fails_and_then_exits(qt_app, tmp_path):
    results = []
    check = chicago95update.UpdateCheck(
        {"COMMIT": "abc"},
        cache_path=tmp_path / "cache.json",
        git=str(tmp_path / "no-such-git"),
        now=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )
    check.finished.connect(results.append)
    check.report(-1, None)
    check.report(0, None)

    assert [(result["installed"], result["error"] != "") for result in results] == [("abc", True)]
