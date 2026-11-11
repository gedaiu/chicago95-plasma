"""The Start button flag's shadow (luna/images/render_logo.py): baked from the flag SVG's own outline."""

import importlib.util

from conftest import REPO
from PIL import Image, ImageChops

spec = importlib.util.spec_from_file_location("render_logo", REPO / "luna/images/render_logo.py")
render_logo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render_logo)


def test_committed_flag_shadow_equals_the_generator_output(qt_app):
    committed = Image.open(render_logo.FLAG_SHADOW_PNG).convert("RGBA")

    assert ImageChops.difference(committed, render_logo.render_flag_shadow()).getbbox() is None
