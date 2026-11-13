"""Wine's classic controls in the look's colours, with Wine's own visual theme off."""

import wine_look
from conftest import run_bash_with_steps
from PySide6.QtGui import QColor

SCHEME_1998 = {
    "face": QColor("#C0C0C0"),
    "selection": QColor("#000080"),
    "selection_text": QColor("#FFFFFF"),
    "title_active": QColor("#000080"),
    "title_active_blend": QColor("#1084D0"),
    "title_active_text": QColor("#FFFFFF"),
    "title_inactive": QColor("#808080"),
    "title_inactive_blend": QColor("#C0C0C0"),
    "title_inactive_text": QColor("#C0C0C0"),
}


def colours(scheme=SCHEME_1998, bevel="1995"):
    text = wine_look.registry(scheme, bevel)
    section = text.split("[HKEY_CURRENT_USER\\Control Panel\\Colors]\n")[1].split("\n\n")[0]
    return dict(line.replace('"', "").split("=") for line in section.splitlines())


def test_buttons_take_the_looks_face_and_bevel_lines():
    assert {key: colours()[key] for key in ("ButtonFace", "ButtonLight", "ButtonShadow", "ButtonDkShadow")} == {
        "ButtonFace": "192 192 192",
        "ButtonLight": "223 223 223",
        "ButtonShadow": "128 128 128",
        "ButtonDkShadow": "0 0 0",
    }


def test_title_bars_take_the_looks_active_gradient():
    assert (colours()["ActiveTitle"], colours()["GradientActiveTitle"]) == ("0 0 128", "16 132 208")


def test_selection_takes_the_looks_selection_colour():
    assert (colours()["Hilight"], colours()["HilightText"]) == ("0 0 128", "255 255 255")


def test_the_2000_bevel_draws_its_dark_line_in_404040():
    assert colours(bevel="2000")["ButtonDkShadow"] == "64 64 64"


def test_wines_visual_theme_is_off_so_the_classic_controls_show():
    assert '[HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\ThemeManager]\n"ThemeActive"="0"' in (
        wine_look.registry(SCHEME_1998, "1995")
    )


def test_setup_imports_the_look_into_the_wine_prefix(tmp_path):
    (tmp_path / ".wine").mkdir()
    (tmp_path / "stubs").mkdir()
    (tmp_path / "stubs/wine").write_text('#!/bin/sh\necho "$1 $2" >> "$HOME/wine.log"; cp "$2" "$HOME/imported.reg"\n')
    (tmp_path / "stubs/wine").chmod(0o755)
    run_bash_with_steps(
        tmp_path, f'PATH="$HOME/stubs:$PATH"; SETUP_DRY_RUN=0; MANIFEST={tmp_path}/manifest; theme_wine'
    )

    assert "ButtonFace" in (tmp_path / "imported.reg").read_text()
