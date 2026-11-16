"""GTK 3's message dialog (VS Code's and every Electron app's native dialog) packs its buttons edge to edge;
the classic sheet keeps them apart like the originals' dialogs."""

import json
import os
import subprocess
import sys

import pytest
from conftest import REPO

PROBE = """
import json, sys
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib
provider = Gtk.CssProvider()
provider.load_from_path(sys.argv[1])
Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
dialog = Gtk.MessageDialog(text="Trust this folder?")
dialog.add_buttons("Trust folder", 1, "Cancel", 2, "Don't trust", 3)
dialog.show_all()
def report():
    faces = []
    for button in dialog.get_action_area().get_children():
        box, margin = button.get_allocation(), button.get_style_context().get_margin(Gtk.StateFlags.NORMAL)
        faces.append((box.x + margin.left, box.x + box.width - margin.right))
    boxes, ends = sorted(start for start, _ in faces), sorted(end for _, end in faces)
    print(json.dumps(min(start - end for start, end in zip(boxes[1:], ends[:-1]))))
    Gtk.main_quit()
GLib.timeout_add(300, report)
Gtk.main()
"""


def test_buttons_in_a_gtk3_message_dialog_with_the_classic_sheet_are_six_pixels_apart():
    if not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")):
        pytest.skip("GTK needs a display")
    gap = subprocess.run(
        [sys.executable, "-c", PROBE, str(REPO / "config/gtk-frames-classic.css")],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
        env={**os.environ, "GTK_THEME": "Adwaita"},
    ).stdout
    assert json.loads(gap) == 6
