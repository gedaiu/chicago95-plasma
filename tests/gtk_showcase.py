"""Render GTK controls in a separate process (GTK 3 and 4 cannot share a process).

Invoked inside a disposable KWin session by showcase.gtk_controls; never uses the user's display.
"""

import json
import os
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


def input_widgets():
    for kind in ("dropdown", "spinbox"):
        for state in ("normal", "disabled", "hovered", "pressed"):
            if kind == "dropdown":
                control = Gtk.DropDown.new_from_strings(["First item", "Second item"]) if V4 else Gtk.ComboBoxText()
                if not V4:
                    control.append_text("First item")
                    control.append_text("Second item")
                    control.set_active(0)
            else:
                control = Gtk.SpinButton.new_with_range(0, 100, 1)
                control.set_value(42)
            control.set_size_request(160, -1)
            control.set_sensitive(state != "disabled")
            control.set_can_focus(False)
            if state in ("hovered", "pressed"):
                control.set_state_flags(Gtk.StateFlags.PRELIGHT if state == "hovered" else Gtk.StateFlags.ACTIVE, False)
            yield kind, state, control


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
    inputs = list(input_widgets())
    for kind, title in (("dropdown", "Drop-down"), ("spinbox", "Spin box")):
        yield (
            "Inputs",
            f"{title}: normal, disabled, hovered, pressed",
            [control for control_kind, _state, control in inputs if control_kind == kind],
        )
    for point in (None, "after"):
        for orientation in ("horizontal", "vertical"):
            label = "with ticks" if point else "plain"
            yield (
                "Ranges",
                f"Sliders: {orientation}, {label}, normal, disabled, hovered, pressed",
                [
                    control
                    for state, axis, control in slider_widgets(point)
                    if axis == orientation and state in ("normal", "disabled", "hovered", "pressed")
                ],
            )
    progress = Gtk.ProgressBar()
    progress.set_fraction(0.55)
    progress.set_size_request(260, -1)
    yield "Ranges", "Progress bar", [progress]
    states = []
    for fraction, enabled in ((0, True), (1, True), (0.55, False)):
        bar = Gtk.ProgressBar()
        bar.set_fraction(fraction)
        bar.set_sensitive(enabled)
        bar.set_size_request(160, -1)
        states.append(bar)
    yield "Ranges", "Progress bars: empty, full, disabled", states
    directions = []
    for vertical, inverted in ((False, True), (True, False), (True, True)):
        bar = Gtk.ProgressBar()
        bar.set_fraction(0.55)
        bar.set_inverted(inverted != vertical)
        bar.set_orientation(Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL)
        bar.set_size_request(-1, 90) if vertical else bar.set_size_request(160, -1)
        bar.set_valign(Gtk.Align.CENTER)
        directions.append(bar)
    yield "Ranges", "Progress bars: reversed, vertical, vertical reversed", directions
    for orientation, name in ((Gtk.Orientation.HORIZONTAL, "horizontal"), (Gtk.Orientation.VERTICAL, "vertical")):
        bars = []
        for state in ("normal", "disabled", "hovered", "pressed"):
            bar = Gtk.Scrollbar(
                orientation=orientation, adjustment=Gtk.Adjustment(value=25, lower=0, upper=100, page_size=20)
            )
            bar.set_size_request(220 if name == "horizontal" else -1, 100 if name == "vertical" else -1)
            bar.set_sensitive(state != "disabled")
            if state in ("hovered", "pressed"):
                bar._audit_interaction = state
            bars.append(bar)
        label = f"Scroll bars: {name}, normal / disabled / thumb hover / thumb pressed"
        yield "Ranges", label + (" (GTK4 end arrows are decorative)" if V4 else ""), bars
    for state in ("first", "second", "disabled", "hovered"):
        tabs = Gtk.Notebook()
        for name in ("General", "Details", "Advanced"):
            tabs.append_page(Gtk.Label(label=f"{name} settings"), Gtk.Label(label=name))
        tabs.set_size_request(350, 90)
        tabs._audit_page = 1 if state == "second" else 0
        tabs._audit_tab_hover = state == "hovered"
        tabs.set_sensitive(state != "disabled")
        yield "Navigation", "Tabs" if state == "first" else f"Tabs: {state}", [tabs]
    listing = Gtk.ListBox()
    for name in ("Documents", "Pictures", "Downloads"):
        listing.append(Gtk.Label(label=name)) if V4 else listing.add(Gtk.Label(label=name))
    listing.select_row(listing.get_row_at_index(1))
    listing.set_size_request(260, 90)
    yield "Views", "List: selected row", [listing]
    for state in ("normal", "disabled", "unlabelled"):
        frame = Gtk.Frame(label="Options" if state != "unlabelled" else None)
        frame.set_size_request(240, 80)
        child = Gtk.CheckButton(label="Enable previews")
        frame.set_child(child) if V4 else frame.add(child)
        frame.set_sensitive(state != "disabled")
        yield "Containers and text", f"Group box: {state}", [frame]
    for active in (False, True):
        yield (
            "Indicators",
            f"Switches: {'on' if active else 'off'}, normal, disabled, hovered, pressed, focused",
            [widget for state, widget in switch_widgets() if state.startswith("on-" if active else "off-")],
        )


def switch_widgets():
    for active in (False, True):
        for state in ("normal", "disabled", "hovered", "pressed", "focused"):
            widget = Gtk.Switch()
            widget.set_active(active)
            widget.set_sensitive(state != "disabled")
            widget.set_valign(Gtk.Align.CENTER)
            widget.set_halign(Gtk.Align.CENTER)
            flag = {
                "hovered": Gtk.StateFlags.PRELIGHT,
                "pressed": Gtk.StateFlags.ACTIVE,
                "focused": Gtk.StateFlags.FOCUSED,
            }.get(state)
            if flag is not None:
                widget._audit_switch_flag = flag
                widget.set_state_flags(flag, False)
            yield f"{'on' if active else 'off'}-{state}", widget


def consistency_widgets():
    for state, flag in (
        ("normal", None),
        ("hovered", Gtk.StateFlags.PRELIGHT),
        ("pressed", Gtk.StateFlags.ACTIVE),
        ("backdrop", Gtk.StateFlags.BACKDROP),
    ):
        bar = Gtk.HeaderBar()
        if V4:
            bar.set_show_title_buttons(False)
        bar.get_style_context().add_class("titlebar")
        for kind in ("minimize", "maximize", "close"):
            button = Gtk.Button()
            button.get_style_context().add_class("titlebutton")
            button.get_style_context().add_class(kind)
            button.set_child(Gtk.Image.new_from_icon_name(f"window-{kind}-symbolic")) if V4 else button.add(
                Gtk.Image.new_from_icon_name(f"window-{kind}-symbolic", Gtk.IconSize.BUTTON)
            )
            button._caption_flag = flag
            if flag is not None:
                button.set_state_flags(flag, False)
            bar.pack_end(button)
        if not V4:
            bar.show_all()
        yield "Window decorations", "caption " + state, [bar]

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

    for state, switch in switch_widgets():
        yield "Indicators", f"switch {state}", [switch]

    for name in ("button", "disabled-button", "entry", "disabled-entry", "selection"):
        control = Gtk.Button() if "button" in name else Gtk.Entry()
        control.set_size_request(140, 24)
        control.set_sensitive(not name.startswith("disabled"))
        if name == "selection":
            control.set_text("Selected text")
            control.select_region(0, -1)
            control._audit_focus = True
        yield "Palette", f"palette {name}", [control]

    yield "Typography", "tabfont normal", [Gtk.Label(label="General Details Advanced")]

    for position in ("top", "bottom", "left", "right"):
        for state in ("first", "second", "disabled", "hovered"):
            tabs = Gtk.Notebook()
            # Fixed label boxes isolate tab chrome from Pango's differing glyph metrics.
            for width in (42, 35, 52):
                label = Gtk.Label()
                label.set_size_request(width, 13)
                tabs.append_page(Gtk.Label(), label)
            tabs.set_tab_pos(getattr(Gtk.PositionType, position.upper()))
            tabs.set_size_request(350, 120)
            tabs._audit_page = 1 if state == "second" else 0
            tabs._audit_tab_hover = state == "hovered"
            tabs.set_sensitive(state != "disabled")
            yield "Navigation", f"tabs {state}-{position}", [tabs]

    for orientation in ("horizontal", "vertical"):
        for state, fraction in (
            ("empty", 0),
            ("low", 0.01),
            ("half", 0.55),
            ("full", 1),
            ("disabled", 0.55),
            ("inverted", 0.55),
            ("rtl", 0.55),
        ):
            progress = Gtk.ProgressBar()
            progress.set_orientation(getattr(Gtk.Orientation, orientation.upper()))
            progress.set_size_request(260, -1) if orientation == "horizontal" else progress.set_size_request(-1, 160)
            progress.set_fraction(fraction)
            progress.set_sensitive(state != "disabled")
            # Qt's vertical progress starts at the bottom; GTK's starts at the top.
            # Request the same visual direction explicitly for cross-toolkit audits.
            progress.set_inverted((state == "inverted") != (orientation == "vertical"))
            if state == "rtl":
                progress.set_direction(Gtk.TextDirection.RTL)
            yield "Ranges", f"progress {state}-{orientation}", [progress]

    for orientation in ("horizontal", "vertical"):
        for state, value in (
            ("normal", 25),
            ("start", 0),
            ("end", 80),
            ("disabled", 25),
            ("hovered", 25),
            ("pressed", 25),
        ):
            bar = Gtk.Scrollbar(
                orientation=getattr(Gtk.Orientation, orientation.upper()),
                adjustment=Gtk.Adjustment(value=value, lower=0, upper=100, page_size=20),
            )
            bar.set_size_request(220, -1) if orientation == "horizontal" else bar.set_size_request(-1, 180)
            bar.set_sensitive(state != "disabled")
            if state in ("hovered", "pressed"):
                bar._audit_interaction = state
            yield "Ranges", f"scrollbar {state}-{orientation}", [bar]

    for point in (None, "before", "after"):
        for state, orientation, scale in slider_widgets(point):
            kind = "slider" if point is None else f"slider-{point}"
            yield "Ranges", f"{kind} {state}-{orientation}", [scale]

    for state in ("normal", "disabled", "unlabelled"):
        frame = Gtk.Frame()
        if state != "unlabelled":
            # Fixed label geometry isolates frame layout from Pango glyph rasterisation.
            label = Gtk.Label()
            label.set_size_request(48, 18)
            frame.set_label_widget(label)
        frame.set_size_request(240, 80)
        child = Gtk.DrawingArea()
        child.set_size_request(8, 8)
        child.set_halign(Gtk.Align.CENTER)
        child.set_valign(Gtk.Align.CENTER)

        def draw_marker(_area, context, *_args):
            context.set_source_rgb(0, 0, 0)
            context.paint()
            return False

        child.set_draw_func(draw_marker) if V4 else child.connect("draw", draw_marker)
        frame.set_child(child) if V4 else frame.add(child)
        frame.set_sensitive(state != "disabled")
        yield "Containers and text", f"groupbox {state}", [frame]

    for kind, state, control in input_widgets():
        yield "Inputs", f"{kind} {state}", [control]


def slider_widgets(point=None):
    for orientation in ("horizontal", "vertical"):
        for state, value in (
            ("normal", 40),
            ("start", 0),
            ("end", 100),
            ("disabled", 40),
            ("hovered", 40),
            ("pressed", 40),
        ):
            scale = Gtk.Scale.new_with_range(getattr(Gtk.Orientation, orientation.upper()), 0, 100, 1)
            scale.set_draw_value(False)
            if point:
                side = (
                    (Gtk.PositionType.TOP if point == "before" else Gtk.PositionType.BOTTOM)
                    if orientation == "horizontal"
                    else (Gtk.PositionType.LEFT if point == "before" else Gtk.PositionType.RIGHT)
                )
                for mark in (0, 25, 50, 75, 100):
                    scale.add_mark(mark, side, None)
            scale.set_value(value)
            scale.set_size_request(180, 21) if orientation == "horizontal" else scale.set_size_request(21, 180)
            scale.set_sensitive(state != "disabled")
            if state in ("hovered", "pressed"):
                scale._audit_interaction = state
            yield state, orientation, scale


def main():
    Gtk.init() if V4 else Gtk.init([])
    settings = Gtk.Settings.get_default()
    settings.set_property("gtk-theme-name", THEME)
    settings.set_property("gtk-enable-animations", False)
    font_family = os.environ.get("CHICAGO95_SHOWCASE_FONT")
    if font_family:
        settings.set_property("gtk-font-name", f"{font_family} 11px")
        settings.set_property("gtk-xft-dpi", 96 * 1024)
        settings.set_property("gtk-xft-antialias", 0 if font_family == "MS W98 UI" else 1)
    output = Path(OUTPUT)
    output.mkdir(parents=True, exist_ok=True)
    catalogue = list(consistency_widgets() if AUDIT else widgets())
    if AUDIT and "--only" in sys.argv:
        kinds = sys.argv[sys.argv.index("--only") + 1].split(",")
        catalogue = [row for row in catalogue if row[1].split()[0] in kinds]
    manifest = []
    loop = GLib.MainLoop()
    position = 0
    window = None
    capture_attempts = 0

    def show_next():
        nonlocal position, window, capture_attempts
        capture_attempts = 0
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
        native_caption = not V4 and label.startswith("caption ")
        if native_caption:
            box.remove(children[0])
        window = Gtk.Window() if V4 or native_caption else Gtk.OffscreenWindow()
        if native_caption:
            window.set_titlebar(children[0])
        window.set_child(box) if V4 else window.add(box)
        window.present() if V4 else window.show_all()
        for child in children:
            if isinstance(child, Gtk.Notebook):
                child.set_current_page(getattr(child, "_audit_page", 0))
        for child in children:
            if getattr(child, "_audit_tab_hover", False):
                if V4:

                    def hover_tab(node):
                        if node.get_css_name() == "tabs":
                            tab = node.get_first_child()
                            while tab is not None and tab.get_css_name() != "tab":
                                tab = tab.get_next_sibling()
                            tab.get_next_sibling().set_state_flags(Gtk.StateFlags.PRELIGHT, False)
                        node = node.get_first_child()
                        while node is not None:
                            hover_tab(node)
                            node = node.get_next_sibling()

                    hover_tab(child)
                else:
                    from gi.repository import Gdk

                    label = child.get_tab_label(child.get_nth_page(1))
                    x, y = label.translate_coordinates(
                        window, label.get_allocated_width() // 2, label.get_allocated_height() // 2
                    )
                    event_window = child.get_window()
                    for candidate in event_window.get_children():
                        geometry = candidate.get_geometry()
                        if (
                            geometry.x <= x < geometry.x + geometry.width
                            and geometry.y <= y < geometry.y + geometry.height
                        ):
                            event_window = candidate
                            x, y = x - geometry.x, y - geometry.y
                            break
                    event = Gdk.Event.new(Gdk.EventType.MOTION_NOTIFY)
                    event.window, event.x, event.y = event_window, x, y
                    event.set_device(window.get_display().get_default_seat().get_pointer())
                    child.event(event)
        window.set_focus(None)
        for child in children:
            if getattr(child, "_audit_focus", False):
                child.grab_focus()
                child.select_region(0, -1)
            if hasattr(child, "_audit_switch_flag"):
                child.set_state_flags(child._audit_switch_flag, False)
        for child in children:
            state = getattr(child, "_audit_interaction", None)
            if state:
                if V4:

                    def flag_slider(widget, state=state):
                        if widget.get_css_name() == "slider":
                            widget.set_state_flags(
                                Gtk.StateFlags.PRELIGHT if state == "hovered" else Gtk.StateFlags.ACTIVE, False
                            )
                        node = widget.get_first_child()
                        while node is not None:
                            flag_slider(node)
                            node = node.get_next_sibling()

                    flag_slider(child)
                else:
                    from gi.repository import Gdk

                    start, end = child.get_slider_range()
                    allocation = child.get_allocation()
                    horizontal = child.get_orientation() == Gtk.Orientation.HORIZONTAL
                    event = Gdk.Event.new(Gdk.EventType.MOTION_NOTIFY)
                    event.window = child.get_window()
                    # GtkRange owns an input-only child window; events use its local coordinates.
                    for candidate in event.window.get_children():
                        geometry = candidate.get_geometry()
                        if (geometry.x, geometry.y, geometry.width, geometry.height) == (
                            allocation.x,
                            allocation.y,
                            allocation.width,
                            allocation.height,
                        ):
                            event.window = candidate
                            break
                    event.x = (start + end) / 2 if horizontal else allocation.width / 2
                    event.y = allocation.height / 2 if horizontal else (start + end) / 2
                    event.set_device(window.get_display().get_default_seat().get_pointer())
                    crossing = Gdk.Event.new(Gdk.EventType.ENTER_NOTIFY)
                    crossing.window, crossing.x, crossing.y = event.window, event.x, event.y
                    crossing.mode = Gdk.CrossingMode.NORMAL
                    crossing.detail = Gdk.NotifyType.NONLINEAR
                    crossing.set_device(window.get_display().get_default_seat().get_pointer())
                    child.event(crossing)
                    child.event(event)
                    if state == "pressed":
                        press = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
                        press.window, press.x, press.y = event.window, event.x, event.y
                        press.button = 1
                        press.set_device(window.get_display().get_default_seat().get_pointer())
                        child.event(press)
        GLib.timeout_add(200, capture)
        return False

    def capture():
        nonlocal position, capture_attempts
        group, label, children = catalogue[position]
        if label == "tabfont normal":
            from gi.repository import Pango

            context = children[0].get_pango_context()
            description = context.get_font_description()
            resolved = context.load_font(description).describe()
            (output / "font.json").write_text(
                json.dumps(
                    {
                        "requested_family": description.get_family(),
                        "resolved_family": resolved.get_family(),
                        "size": description.get_size() / Pango.SCALE,
                        "absolute": description.get_size_is_absolute(),
                    }
                )
            )
        if not V4 and label.startswith("caption "):
            for button in children[0].get_children():
                flag = getattr(button, "_caption_flag", None)
                if flag is not None:
                    button.set_state_flags(flag, False)
        path = output / f"{position}.png"
        if V4:
            # Snapshot the real widget tree, including the native theme's state styling.
            paintable = Gtk.WidgetPaintable.new(window.get_child())
            snapshot = Gtk.Snapshot()
            paintable.snapshot(snapshot, window.get_child().get_width(), window.get_child().get_height())
            node = snapshot.to_node()
            if node is None:
                # A busy compositor may not have produced the first frame yet.
                capture_attempts += 1
                if capture_attempts <= 10:
                    return True
                raise RuntimeError(f"GTK4 did not paint {label} after repeated capture attempts")
            renderer = Gsk.CairoRenderer.new()
            renderer.realize(window.get_surface())
            texture = renderer.render_texture(node, None)
            texture.save_to_png(str(path))
            renderer.unrealize()
        elif label.startswith("caption "):
            import cairo

            surface = cairo.ImageSurface(
                cairo.FORMAT_ARGB32, window.get_allocated_width(), window.get_allocated_height()
            )
            window.draw(cairo.Context(surface))
            surface.write_to_png(str(path))
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
