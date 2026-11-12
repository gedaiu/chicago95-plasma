"""Native client-side caption buttons must retain Luna faces in both GTK versions."""
import json

import pytest
from PIL import Image


@pytest.fixture(scope="module")
def captions(tmp_path_factory, qt_app):
    from showcase import gtk_controls

    folder = tmp_path_factory.mktemp("luna-captions")
    gtk_controls("luna", folder, audit=True, audit_kinds=("caption",))
    images = {}
    for version in ("3.0", "4.0"):
        output = folder / f"gtk-{version}"
        for _, label, filename in json.loads((output / "manifest.json").read_text()):
            images[version, label.split()[1]] = Image.open(output / filename).convert("RGB")
    return images


@pytest.mark.parametrize("version", ["3.0", "4.0"])
def test_caption_close_has_red_face_and_white_glyph(captions, version):
    image = captions[version, "normal"]
    pixels = list(image.get_flattened_data())
    assert sum(r > 150 and r > g * 1.5 and r > b * 1.5 for r, g, b in pixels) > 150
    assert sum(min(r, g, b) > 235 for r, g, b in pixels) > 40


@pytest.mark.parametrize("version", ["3.0", "4.0"])
@pytest.mark.parametrize("state", ["hovered", "pressed", "backdrop"])
def test_caption_states_visibly_change(captions, version, state):
    from PIL import ImageChops

    assert ImageChops.difference(captions[version, "normal"], captions[version, state]).getbbox() is not None
