from PySide6.QtGui import QColor

import chicago95ui


def names(colors):
    return {name: color.name() for name, color in colors.items()}


def test_scheme_without_kdeglobals_is_the_1995_palette(tmp_path):
    assert names(chicago95ui.read_scheme(tmp_path / "kdeglobals")) == {
        "face": "#c0c0c0", "selection": "#000080", "selection_text": "#ffffff",
        "title_active": "#000080", "title_active_blend": "#000080", "title_active_text": "#ffffff",
        "title_inactive": "#808080", "title_inactive_blend": "#808080", "title_inactive_text": "#c0c0c0"}


def test_scheme_reads_title_gradient_and_face_written_by_system_settings(tmp_path):
    settings = tmp_path / "kdeglobals"
    settings.write_text("[Colors:Window]\nBackgroundNormal=212,208,200\n\n"
                        "[WM]\nactiveBackground=0,0,128\nactiveBlend=16,132,208\n")

    scheme = names(chicago95ui.read_scheme(settings))

    assert (scheme["face"], scheme["title_active"], scheme["title_active_blend"]) == ("#d4d0c8", "#000080", "#1084d0")


def test_bevel_shades_of_c0c0c0_are_dfdfdf_and_808080():
    assert [shade.name() for shade in chicago95ui.bevel_shades(QColor("#C0C0C0"))] == ["#dfdfdf", "#808080"]


def test_sync_colors_passes_solid_titles_as_one_colour_and_gradients_as_two():
    from conftest import load_script
    sync = load_script("chicago95-sync-colors")
    scheme = chicago95ui.read_scheme("/nonexistent")
    scheme["title_active_blend"] = QColor("#1084D0")

    assert sync.title_arguments(scheme) == ["--active", "#000080,#1084d0", "--inactive", "#808080"]
