"""Classic GTK follows the window scheme instead of retaining Windows 95 greys."""


import pytest
from gtk_palette import prepare_theme
from PIL import Image

WARM = dict(face="#d4d0c8", selection="#0a246a", selection_text="#ffffff",
            light="#d4d0c8", shadow="#808080", dark="#404040")


def test_theme_colours_change_without_recolouring_text_fields_or_transparency(tmp_path):
    source, output = tmp_path / "source", tmp_path / "output"
    source.mkdir()
    (source / "gtk.css").write_text("@define-color bg_color #c0c0c0;\n@define-color border_dark #000000;\n"
                                    ":root { --c95-face: #c0c0c0; --c95-selected-bg: #000080; }\n")
    image = Image.new("RGBA", (5, 1))
    image.putdata([(192, 192, 192, 255), (223, 223, 223, 128), (0, 0, 128, 255),
                   (0, 0, 0, 255), (255, 255, 255, 255)])
    image.save(source / "control.png")
    prepare_theme(source, output, WARM)
    result = Image.open(output / "control.png")
    assert list(result.get_flattened_data()) == [(212, 208, 200, 255), (212, 208, 200, 128),
                                                (10, 36, 106, 255), (0, 0, 0, 255), (255, 255, 255, 255)]
    assert "--c95-face: #d4d0c8" in (output / "gtk.css").read_text()
    assert "border_dark #404040" in (output / "gtk.css").read_text()
    # Rebuild from the original, so switching to another/custom scheme cannot leave old colours behind.
    prepare_theme(source, output, {**WARM, "face": "#c0c0c0", "selection": "#000080"})
    assert Image.open(output / "control.png").getpixel((0, 0)) == (192, 192, 192, 255)
    assert Image.open(source / "control.png").getpixel((0, 0)) == (192, 192, 192, 255)


@pytest.mark.parametrize("look", ("2000", "2001"))
def test_native_gtk_controls_match_the_window_palette(qt_app, tmp_path, look):
    import json
    import shutil

    import chicago95ui
    from showcase import gtk_controls, themed

    if not shutil.which("kwin_wayland"):
        pytest.skip("native GTK checks require isolated KWin")
    with themed(qt_app, look):
        scheme = chicago95ui.read_scheme()
        assert scheme["face"].getRgb()[:3] == (212, 208, 200)
    gtk_controls(look, tmp_path, audit=True, audit_kinds=("palette", "dropdown", "spinbox"))
    for version in ("3.0", "4.0"):
        output = tmp_path / f"gtk-{version}"
        for _group, label, filename in json.loads((output / "manifest.json").read_text()):
            image = Image.open(output / filename).convert("RGBA")
            background = Image.new("RGBA", image.size, "#d4d0c8")
            background.alpha_composite(image)
            colours = list(background.convert("RGB").get_flattened_data())
            assert (192, 192, 192) not in colours, f"{version} {label} retained the Windows 95 face"
            assert colours.count((212, 208, 200)) > 50
            if label == "palette entry":
                assert colours.count((255, 255, 255)) > 100
            if label == "palette selection":
                assert colours.count((10, 36, 106)) > 20
            if label in ("palette button", "palette disabled-button", "palette disabled-entry"):
                assert background.convert("RGB").getpixel((image.width // 2, image.height // 2)) == (212, 208, 200)


def test_installed_theme_keeps_a_pristine_copy_for_scheme_changes(tmp_path):
    from gtk_palette import sync_installed
    from PySide6.QtGui import QColor

    installed = tmp_path / ".themes/Chicago95"
    installed.mkdir(parents=True)
    image = Image.new("RGBA", (1, 1), (192, 192, 192, 255))
    image.save(installed / "face.png")
    scheme = {key: QColor(value) for key, value in WARM.items()}
    sync_installed(scheme, "2000", home=tmp_path)
    assert Image.open(installed / "face.png").getpixel((0, 0)) == (212, 208, 200, 255)
    scheme["face"] = QColor("#b0c8d0")
    sync_installed(scheme, "2000", home=tmp_path)
    assert Image.open(installed / "face.png").getpixel((0, 0)) == (176, 200, 208, 255)
    original = tmp_path / ".local/share/chicago95/gtk-original/face.png"
    assert Image.open(original).getpixel((0, 0)) == (192, 192, 192, 255)


@pytest.mark.parametrize("look", ("2000", "2001"))
def test_qt_controls_use_the_same_face_as_the_window(qt_app, look):
    from PySide6.QtWidgets import QComboBox, QLineEdit, QPushButton, QSpinBox
    from reference import qimage_to_pil
    from showcase import themed

    with themed(qt_app, look):
        for kind in (QPushButton, QLineEdit, QComboBox, QSpinBox):
            widget = kind()
            widget.resize(140, 24)
            if kind is not QPushButton:
                widget.setEnabled(False)
            image = qimage_to_pil(widget.grab().toImage())
            assert image.getpixel((70, 12)) == (212, 208, 200), kind.__name__
            widget.close()
