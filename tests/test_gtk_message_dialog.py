"""GTK 3's message dialog (VS Code's and every Electron app's native dialog) packs its buttons edge to edge;
the classic sheet keeps them apart like the originals' dialogs."""

import json
import os
import subprocess
import sys

import pytest
from conftest import REPO, run_bash_with_steps

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


CSS_ERRORS = """
import sys
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
provider = Gtk.CssProvider()
errors = []
provider.connect("parsing-error", lambda _p, _s, error: errors.append(error.message))
try:
    provider.load_from_data(open(sys.argv[1], "rb").read().replace(b"@import 'colors.css';", b""))
except gi.repository.GLib.Error:
    pass
print("\\n".join(errors))
"""


def test_the_classic_block_in_the_gtk3_sheet_names_no_gtk4_only_property(tmp_path):
    run_bash_with_steps(tmp_path, "SETUP_LOG=/dev/null; import_gtk_progress Chicago95")
    errors = subprocess.run(
        [sys.executable, "-c", CSS_ERRORS, str(tmp_path / ".config/gtk-3.0/gtk.css")],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    ).stdout.split("\n")
    assert [error for error in errors if "not a valid property name" in error] == []


def test_the_title_bar_block_in_the_gtk3_sheet_names_no_gtk4_only_property(tmp_path):
    run_bash_with_steps(tmp_path, "SETUP_LOG=/dev/null; write_gtk_titlebar_css '#000080,#1084D0' '#808080' '#C0C0C0'")
    errors = subprocess.run(
        [sys.executable, "-c", CSS_ERRORS, str(tmp_path / ".config/gtk-3.0/gtk.css")],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    ).stdout.split("\n")
    assert [error for error in errors if "not a valid property name" in error] == []


HANDY_WINDOW = """
import sys, gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Handy", "1")
from gi.repository import Gdk, GLib, Gtk, Handy
import cairo
Handy.init()
provider = Gtk.CssProvider()
provider.load_from_path(sys.argv[2])
Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
window = Handy.ApplicationWindow()
window.set_default_size(200, 120)
window.add(Gtk.Box())
window.show_all()
def grab():
    size = window.get_allocation()
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size.width, size.height)
    window.draw(cairo.Context(surface))
    surface.write_to_png(sys.argv[1])
    Gtk.main_quit()
GLib.timeout_add(600, grab)
Gtk.main()
"""


def test_a_libhandy_window_like_gnome_boxes_gets_the_raised_frame_light_white_then_face(tmp_path):
    from PIL import Image

    if not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")):
        pytest.skip("GTK needs a display")
    sheet = tmp_path / "sheet.css"
    sheet.write_text(
        subprocess.run(
            [sys.executable, str(REPO / "lib/gtk_header.py"), "--gtk", "3.0"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    shot = tmp_path / "window.png"
    subprocess.run(
        [sys.executable, "-c", HANDY_WINDOW, str(shot), str(sheet)],
        capture_output=True,
        check=True,
        timeout=30,
        env={**os.environ, "GTK_THEME": "Adwaita"},
    )
    image = Image.open(shot).convert("RGB")
    margin = next(x for x in range(image.width) if Image.open(shot).getpixel((x, 60))[3] == 255)
    assert [image.getpixel((margin + step, 60)) for step in range(4)] == [
        (223, 223, 223),
        (255, 255, 255),
        (192, 192, 192),
        (192, 192, 192),
    ]


CONTENT_SHIFT = """
import sys, gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Handy", "1")
from gi.repository import Gdk, GLib, Gtk, Handy
Handy.init()
window, outer, inner = Handy.ApplicationWindow(), Gtk.Box(), Gtk.Box()
outer.pack_start(inner, True, True, 0)
window.add(outer)
window.show_all()
before = []
def style():
    before.append(inner.translate_coordinates(window, 0, 0)[0])
    provider = Gtk.CssProvider()
    provider.load_from_path(sys.argv[1])
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
    GLib.timeout_add(300, report)
def report():
    print(inner.translate_coordinates(window, 0, 0)[0] - before[0])
    Gtk.main_quit()
GLib.timeout_add(300, style)
Gtk.main()
"""


def test_a_libhandy_windows_content_moves_4_pixels_in_so_a_vm_screen_leaves_the_frame_showing(tmp_path):
    if not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")):
        pytest.skip("GTK needs a display")
    sheet = tmp_path / "sheet.css"
    sheet.write_text(
        subprocess.run(
            [sys.executable, str(REPO / "lib/gtk_header.py"), "--gtk", "3.0"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    shift = subprocess.run(
        [sys.executable, "-c", CONTENT_SHIFT, str(sheet)],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
        env={**os.environ, "GTK_THEME": "Adwaita"},
    ).stdout
    assert shift == "4\n"
