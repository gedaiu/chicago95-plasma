"""Render GTK controls in a separate process (GTK 3 and 4 cannot share a process).

Invoked inside a disposable KWin session by showcase.gtk_controls; never uses the user's display.
"""

import json
import sys
from pathlib import Path

import gi

VERSION, THEME, OUTPUT = sys.argv[1:4]
AUDIT = "--consistency" in sys.argv[4:]
gi.require_version("Gtk", VERSION)
from gi.repository import GLib, Gtk  # noqa: E402

V4 = VERSION == "4.0"
if V4:
    gi.require_version("Gsk", "4.0")
    from gi.repository import Gsk


def add(box, widget):
    if V4:
        box.append(widget)
    else:
        box.pack_start(widget, False, False, 0)


def widgets():
    buttons = []
    for caption, state in (
        ("Normal", None),
        ("Hovered", Gtk.StateFlags.PRELIGHT),
        ("Pressed", Gtk.StateFlags.ACTIVE),
        ("Disabled", Gtk.StateFlags.INSENSITIVE),
    ):
        button = Gtk.Button(label=caption)
        if state is not None:
            button.set_state_flags(state, False)
        buttons.append(button)
    yield "Buttons", "Push buttons: normal, hovered, pressed, disabled", buttons
    checks = []
    for label, active, disabled in (("Off", False, False), ("On", True, False), ("Disabled", True, True)):
        check = Gtk.CheckButton(label=label)
        check.set_active(active)
        check.set_sensitive(not disabled)
        checks.append(check)
    mixed = Gtk.CheckButton(label="Mixed")
    mixed.set_inconsistent(True)
    yield "Buttons", "Check boxes: off, on, disabled, mixed", [*checks, mixed]
    radios = []
    for label in ("Selected", "Other", "Disabled"):
        radio = (
            Gtk.CheckButton(label=label)
            if V4
            else Gtk.RadioButton.new_with_label_from_widget(radios[0] if radios else None, label)
        )
        if V4 and radios:
            radio.set_group(radios[0])
        radios.append(radio)
    radios[0].set_active(True)
    radios[-1].set_sensitive(False)
    yield "Buttons", "Radio buttons", radios
    entries = []
    for text in ("Editable text", "Read only", "Disabled"):
        entry = Gtk.Entry()
        entry.set_text(text)
        entry.set_width_chars(12)
        entry.set_editable(text != "Read only")
        entry.set_sensitive(text != "Disabled")
        entries.append(entry)
    yield "Inputs", "Text fields", entries
    combo = Gtk.DropDown.new_from_strings(["First item", "Second item"]) if V4 else Gtk.ComboBoxText()
    if not V4:
        combo.append_text("First item")
        combo.append_text("Second item")
        combo.set_active(0)
    spin = Gtk.SpinButton.new_with_range(0, 100, 1)
    spin.set_value(42)
    yield "Inputs", "Drop-down and spin box", [combo, spin]
    scales = []
    for enabled in (True, False):
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        scale.set_value(40)
        scale.set_size_request(180, -1)
        scale.set_sensitive(enabled)
        scales.append(scale)
    yield "Ranges", "Sliders: normal and disabled", scales
    progress = Gtk.ProgressBar()
    progress.set_fraction(0.55)
    progress.set_size_request(260, -1)
    yield "Ranges", "Progress bar", [progress]
    states = []
    for fraction, enabled in ((0, True), (1, True), (.55, False)):
        bar = Gtk.ProgressBar()
        bar.set_fraction(fraction)
        bar.set_sensitive(enabled)
        bar.set_size_request(160, -1)
        states.append(bar)
    yield "Ranges", "Progress bars: empty, full, disabled", states
    directions = []
    for vertical, inverted in ((False, True), (True, False), (True, True)):
        bar = Gtk.ProgressBar()
        bar.set_fraction(.55)
        bar.set_inverted(inverted)
        bar.set_orientation(Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL)
        bar.set_size_request(-1, 90) if vertical else bar.set_size_request(160, -1)
        bar.set_valign(Gtk.Align.CENTER)
        directions.append(bar)
    yield "Ranges", "Progress bars: reversed, vertical, vertical reversed", directions
    for orientation, name in ((Gtk.Orientation.HORIZONTAL, "horizontal"), (Gtk.Orientation.VERTICAL, "vertical")):
        bars = []
        for enabled in (True, False):
            bar = Gtk.Scrollbar(
                orientation=orientation, adjustment=Gtk.Adjustment(value=25, lower=0, upper=100, page_size=20)
            )
            bar.set_size_request(220 if name == "horizontal" else -1, 100 if name == "vertical" else -1)
            bar.set_sensitive(enabled)
            bars.append(bar)
        yield "Ranges", f"Scroll bars: {name}, enabled and disabled", bars
    tabs = Gtk.Notebook()
    for name in ("General", "Details", "Advanced"):
        tabs.append_page(Gtk.Label(label=f"{name} settings"), Gtk.Label(label=name))
    tabs.set_size_request(350, 90)
    yield "Navigation", "Tabs", [tabs]
    listing = Gtk.ListBox()
    for name in ("Documents", "Pictures", "Downloads"):
        listing.append(Gtk.Label(label=name)) if V4 else listing.add(Gtk.Label(label=name))
    listing.select_row(listing.get_row_at_index(1))
    listing.set_size_request(260, 90)
    yield "Views", "List: selected row", [listing]
    frame = Gtk.Frame(label="Options")
    child = Gtk.CheckButton(label="Enable previews")
    frame.set_child(child) if V4 else frame.add(child)
    switch = Gtk.Switch()
    switch.set_active(True)
    yield "Containers and text", "Group box and switch", [frame, switch]


def consistency_widgets():
    # Empty labels isolate the indicator pixels from font rasterisation and label padding.
    for kind in ("checkbox", "radio"):
        for state in (
            "normal",
            "checked",
            "mixed",
            "disabled",
            "hovered",
            "pressed",
            "checked-hovered",
            "checked-pressed",
            "focused",
        ):
            if kind == "radio" and state == "mixed":
                continue
            widget = Gtk.CheckButton() if kind == "checkbox" or V4 else Gtk.RadioButton()
            if kind == "radio":
                peer = Gtk.CheckButton() if V4 else Gtk.RadioButton()
                widget.set_group(peer) if V4 else widget.join_group(peer)
                peer.set_active(True)
                widget._peer = peer  # the group must survive until the screenshot
            widget.set_active(state.startswith("checked") or state == "disabled")
            widget.set_inconsistent(state == "mixed")
            widget.set_sensitive(state != "disabled")
            widget.set_can_focus(False)
            if state.endswith("hovered"):
                widget.set_state_flags(Gtk.StateFlags.PRELIGHT, False)
            if state.endswith("pressed"):
                widget.set_state_flags(Gtk.StateFlags.ACTIVE, False)
            if state == "focused":
                widget.set_state_flags(Gtk.StateFlags.FOCUSED, False)
            yield "Indicators", f"{kind} {state}", [widget]

    for position in ("top", "bottom", "left", "right"):
        for state in ("first", "second", "disabled"):
            tabs = Gtk.Notebook()
            # Fixed label boxes isolate tab chrome from Pango's differing glyph metrics.
            for width in (42, 35, 52):
                label = Gtk.Label()
                label.set_size_request(width, 20)
                tabs.append_page(Gtk.Label(), label)
            tabs.set_tab_pos(getattr(Gtk.PositionType, position.upper()))
            tabs.set_size_request(350, 120)
            tabs._audit_page = 1 if state == "second" else 0
            tabs.set_sensitive(state != "disabled")
            yield "Navigation", f"tabs {state}-{position}", [tabs]

    for orientation in ("horizontal", "vertical"):
        for state, fraction in (("empty", 0), ("low", .01), ("half", .55), ("full", 1),
                                ("disabled", .55), ("inverted", .55), ("rtl", .55)):
            progress = Gtk.ProgressBar()
            progress.set_orientation(getattr(Gtk.Orientation, orientation.upper()))
            progress.set_size_request(260, -1) if orientation == "horizontal" else progress.set_size_request(-1, 160)
            progress.set_fraction(fraction)
            progress.set_sensitive(state != "disabled")
            progress.set_inverted(state == "inverted")
            if state == "rtl":
                progress.set_direction(Gtk.TextDirection.RTL)
            yield "Ranges", f"progress {state}-{orientation}", [progress]


def main():
    Gtk.init() if V4 else Gtk.init([])
    settings = Gtk.Settings.get_default()
    settings.set_property("gtk-theme-name", THEME)
    settings.set_property("gtk-enable-animations", False)
    output = Path(OUTPUT)
    output.mkdir(parents=True, exist_ok=True)
    catalogue = list(consistency_widgets() if AUDIT else widgets())
    manifest = []
    loop = GLib.MainLoop()
    position = 0
    window = None

    def show_next():
        nonlocal position, window
        if position == len(catalogue):
            (output / "manifest.json").write_text(json.dumps(manifest))
            loop.quit()
            return False
        group, label, children = catalogue[position]
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        for child in children:
            add(box, child)
        for edge in ("top", "bottom", "start", "end"):
            getattr(box, f"set_margin_{edge}")(12)
        window = Gtk.Window() if V4 else Gtk.OffscreenWindow()
        window.set_child(box) if V4 else window.add(box)
        window.present() if V4 else window.show_all()
        for child in children:
            if isinstance(child, Gtk.Notebook):
                child.set_current_page(getattr(child, "_audit_page", 0))
        window.set_focus(None)
        GLib.timeout_add(200, capture)
        return False

    def capture():
        nonlocal position
        group, label, _ = catalogue[position]
        path = output / f"{position}.png"
        if V4:
            # Snapshot the real widget tree, including the native theme's state styling.
            paintable = Gtk.WidgetPaintable.new(window.get_child())
            snapshot = Gtk.Snapshot()
            paintable.snapshot(snapshot, window.get_child().get_width(), window.get_child().get_height())
            node = snapshot.to_node()
            renderer = Gsk.CairoRenderer.new()
            renderer.realize(window.get_surface())
            texture = renderer.render_texture(node, None)
            texture.save_to_png(str(path))
            renderer.unrealize()
        else:
            window.get_pixbuf().savev(str(path), "png", [], [])
        manifest.append([group, label, path.name])
        window.destroy()
        position += 1
        GLib.idle_add(show_next)
        return False

    GLib.idle_add(show_next)
    loop.run()


if __name__ == "__main__":
    main()
