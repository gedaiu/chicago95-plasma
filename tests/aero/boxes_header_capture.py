"""Render the installed Boxes guest toolbar template without opening a guest."""

import json
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Handy", "1")
from gi.repository import GLib, Gtk, Handy  # noqa: E402

Handy.init()
out = Path(sys.argv[1])
out.mkdir()
settings = Gtk.Settings.get_default()
settings.set_property("gtk-theme-name", "Chicago95Aero")
settings.set_property("gtk-decoration-layout", ":minimize,maximize,close")
settings.set_property("gtk-enable-animations", True)
ui = subprocess.check_output(["gresource", "extract", "/usr/bin/gnome-boxes", "/org/gnome/Boxes/ui/display-toolbar.ui"])
root = ET.fromstring(ui)
template = root.find("template")
template.tag = "object"
template.attrib = {"class": "HdyHeaderBar", "id": "toolbar"}
for parent in root.iter():
    for signal in parent.findall("signal"):
        parent.remove(signal)
builder = Gtk.Builder.new_from_string(ET.tostring(root, encoding="unicode"), -1)
bar = builder.get_object("toolbar")
bar.set_show_close_button(True)
bar.set_title("CI1")
window = Gtk.Window()
window.set_titlebar(bar)
window.set_default_size(700, 170)
window.show()


def wait(ms):
    loop = GLib.MainLoop()
    GLib.timeout_add(ms, lambda: (loop.quit(), False)[1])
    loop.run()


def descendants(widget):
    yield widget
    if isinstance(widget, Gtk.Container):
        children = []
        widget.forall(children.append)
        for child in children:
            yield from descendants(child)


wait(300)
buttons = {
    kind: w
    for w in descendants(bar)
    if isinstance(w, Gtk.Button)
    for kind in ("minimize", "maximize", "close")
    if w.get_style_context().has_class(kind)
}
scale = bar.get_scale_factor()
geometry = {}
for name, widget in {**buttons, "back": builder.get_object("back")}.items():
    x, y = widget.translate_coordinates(bar, 0, 0)
    context = widget.get_style_context()
    margin = context.get_margin(context.get_state())
    geometry[name] = [
        x + margin.left,
        y + margin.top,
        widget.get_allocated_width() - margin.left - margin.right,
        widget.get_allocated_height() - margin.top - margin.bottom,
    ]
(out / "layout.json").write_text(json.dumps(geometry))


def capture():
    surface = cairo.ImageSurface(
        cairo.FORMAT_ARGB32, bar.get_allocated_width() * scale, bar.get_allocated_height() * scale
    )
    surface.set_device_scale(scale, scale)
    bar.draw(cairo.Context(surface))
    return surface


close = buttons["close"]
capture().write_to_png(str(out / "normal.png"))
x, y, w, h = geometry["close"]
for entering in (True, False):
    samples = []
    start = time.monotonic()
    while True:
        surface = capture()
        # Average the interior of the face, clear of the rim and hover halo.
        data = surface.get_data()
        values = []
        for row in range((y + 3) * scale, (y + h - 4) * scale):
            left = row * surface.get_stride() + (x + 3) * scale * 4
            right = left + (w - 7) * scale * 4
            values.append(bytes(data[left:right:4]))  # Cairo ARGB32, low byte on x86
        pixels = b"".join(values)
        elapsed = (time.monotonic() - start) * 1000
        samples.append([elapsed, sum(pixels) / len(pixels)])
        if len(samples) == 1:
            if entering:
                close.set_state_flags(Gtk.StateFlags.PRELIGHT, False)
            else:
                close.unset_state_flags(Gtk.StateFlags.PRELIGHT)
        if elapsed > 270:
            break
        wait(8)
    label = "hover" if entering else "rest"
    surface.write_to_png(str(out / (label + ".png")))
    (out / (label + ".json")).write_text(json.dumps(samples))
window.destroy()
