"""Builds the Chicago95Luna GTK theme: the Windows XP Luna widget look for GTK 3 and GTK 4 programs.

    make_luna_gtk.py [--out DIR]
    make_luna_gtk.py --titlebar ACTIVE|INACTIVE

Writes DIR/index.theme, DIR/gtk-3.0/gtk.css and DIR/gtk-4.0/gtk.css (default Chicago95Luna beside this file). The colours
and gradients are the ones of the Kvantum theme (luna/kvantum/stops.py, LunaStyle's measured values), so the Qt and GTK
widgets match. --titlebar prints the header bar block for ~/.config/gtk-N.0/gtk.css: the vertical gradient of the Luna
title bar from luna/palette.py, six pixel rounded top corners and the Trebuchet MS bold caption with its dark shadow.
"""

import argparse
import base64
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LUNA_ROOT = HERE.parent
THEME_NAME = "Chicago95Luna"
FONT_FAMILY = 'Tahoma, "Wine Tahoma", "DejaVu Sans Condensed", sans-serif'
CAPTION_FONT = '"Trebuchet MS", "Fira Sans", sans-serif'
CAPTION_SHADOW = "#0A246A"
TITLE_RADIUS = 6
INACTIVE_CAPTION = "#D8E4F8"
VERSIONS = ("3.0", "4.0")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


kvantum = load_module("luna_kvantum_generator", LUNA_ROOT / "kvantum/make_luna_kvantum.py")
stops = kvantum.stops
palette = kvantum.palette
GRADIENTS = kvantum.gradient_table()
FACE, SELECTION = palette.PALETTE["face"], palette.PALETTE["selection"]


def vertical(name):
    return (
        "linear-gradient(to bottom, "
        + ", ".join(f"{colour} {round(offset * 100)}%" for offset, colour in GRADIENTS[name])
        + ")"
    )


def band_shadow(top, bottom, left, right):
    """Inset one pixel bands, outermost first: a longer offset is painted underneath, so only its inner band shows."""
    bands = []
    for depth, (top_colour, bottom_colour, left_colour, right_colour) in enumerate(zip(top, bottom, left, right), 1):
        bands += [
            f"inset 0 {depth}px {top_colour}",
            f"inset 0 -{depth}px {bottom_colour}",
            f"inset {depth}px 0 {left_colour}",
            f"inset -{depth}px 0 {right_colour}",
        ]
    return ", ".join(bands)


def corner_glow(light, dark):
    return band_shadow(light, dark, light, dark)


HOVER_SHADOW = corner_glow(stops.HOVER_RING_LIGHT, stops.HOVER_RING_DARK)
DEFAULT_SHADOW = band_shadow(
    stops.DEFAULT_RING_TOP, stops.DEFAULT_RING_BOTTOM, stops.DEFAULT_RING_SIDES, stops.DEFAULT_RING_SIDES
)
CHECK_SHADOW = corner_glow(stops.CHECK_GLOW[:1] * 2, stops.CHECK_GLOW[1:] * 2)


# The scroll bar's stepper buttons (chicago95lunascroll.py's measurements): GTK 4 has no steppers, so the trough
# paints them at its ends and keeps the slider off them with its padding; the trough's gradient runs across the bar.
STEPPER_SIZE = 17
STEPPER_FACE = ("#E1EBF8", "#CADBF3", "#B6CEEF")
STEPPER_BORDER = "#89B0E6"
STEPPER_ARROW = "#245CAB"
STEPPER_ARROWS = {
    "up": "5,10.5 8.5,6.5 12,10.5",
    "down": "5,6.5 12,6.5 8.5,10.5",
    "left": "10.5,5 6.5,8.5 10.5,12",
    "right": "6.5,5 10.5,8.5 6.5,12",
}
TROUGH_ACROSS = "linear-gradient(to %s, #EEEDE5 0%%, #F4F3EE 50%%, #FEFEFB 100%%)"


def stepper_svg(direction):
    stops_markup = "".join(
        f'<stop offset="{offset}" stop-color="{colour}"/>'
        for offset, colour in zip((0, 0.5, 1), STEPPER_FACE, strict=True)
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{STEPPER_SIZE}" height="{STEPPER_SIZE}">'
        f'<defs><linearGradient id="f" x1="0" y1="0" x2="0" y2="1">{stops_markup}</linearGradient></defs>'
        f'<rect x="1.5" y="1.5" width="{STEPPER_SIZE - 3}" height="{STEPPER_SIZE - 3}" rx="2.5" fill="url(#f)"'
        f' stroke="{STEPPER_BORDER}"/>'
        f'<polygon points="{STEPPER_ARROWS[direction]}" fill="{STEPPER_ARROW}"/></svg>'
    )


def stepper_image(direction):
    return data_uri(stepper_svg(direction))


def data_uri(svg):
    return 'url("data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode() + '")'


def indicator_png(kind, colour):
    # PNG works with GTK3 even on systems whose GdkPixbuf has no SVG loader.
    import io

    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (stops.INDICATOR_SIZE, stops.INDICATOR_SIZE))
    draw = ImageDraw.Draw(image)
    if kind == "tick":
        offset = (stops.INDICATOR_SIZE - len(stops.CHECK_TICK[0])) // 2
        for y, row in enumerate(stops.CHECK_TICK):
            for x, pixel in enumerate(row):
                if pixel == "#":
                    draw.point((x + offset, y + offset), fill=colour)
    elif kind == "mixed":
        draw.rectangle((3, 3, 9, 9), fill=colour)
    else:
        draw.ellipse((4, 4, 8, 8), fill=colour)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def indicator_icon(kind, colour):
    return f'url("assets/{kind}-{colour.lstrip("#")}.png")'


def tick_icon(colour):
    return indicator_icon("tick", colour)


def mixed_icon(colour):
    return indicator_icon("mixed", colour)


def dot_icon(colour):
    return indicator_icon("dot", colour)


def block(selectors, **properties):
    body = "".join(f"  {name.replace('_', '-')}: {value};\n" for name, value in properties.items())
    return f"{selectors} {{\n{body}}}\n"


def titlebar_block(active, inactive, caption):
    corners = f"{TITLE_RADIUS}px {TITLE_RADIUS}px 0 0"
    shared = dict(
        border_radius=corners, text_shadow=f"1px 1px 0 {CAPTION_SHADOW}", font_family=CAPTION_FONT, font_weight="bold"
    )
    return block(
        "headerbar.titlebar, .titlebar.default-decoration, headerbar.titlebar .title, .titlebar.default-decoration .title",
        background_image=vertical(active),
        background_color=GRADIENTS[active][0][1],
        color="#FFFFFF",
        **shared,
    ) + block(
        "headerbar.titlebar:backdrop, .titlebar.default-decoration:backdrop, headerbar.titlebar:backdrop .title, .titlebar.default-decoration:backdrop .title",
        background_image=vertical(inactive),
        background_color=GRADIENTS[inactive][0][1],
        color=caption,
        **shared,
    )


def widget_rules():
    field_border = stops.FIELD_BORDER
    rules = [
        block("*", font_family=FONT_FAMILY, font_size="8pt", text_shadow="none", box_shadow="none", outline_width="0"),
        block(
            "window, dialog, .background, toolbar, statusbar, menubar, actionbar, paned > separator",
            background_color=FACE,
            background_image="none",
            color="#000000",
        ),
        block(
            "button",
            min_height="21px",
            padding="0 10px",
            border="1px solid " + stops.BORDER,
            border_radius="3px",
            background_image=vertical("button-body"),
            background_color="#F0F0EA",
            color="#000000",
        ),
        block("button:hover", box_shadow=HOVER_SHADOW),
        block("button:active, button:checked", background_image=vertical("button-pressed"), box_shadow="none"),
        block("button:focus, button.default", box_shadow=DEFAULT_SHADOW),
        block("button.default:hover, button:focus:hover", box_shadow=HOVER_SHADOW),
        block(
            "button:disabled",
            border_color=stops.DISABLED_BORDER,
            background_image="none",
            background_color=GRADIENTS["disabled-face"][0][1],
            color=stops.DISABLED_TEXT,
            box_shadow="none",
        ),
        block(
            "button.flat, toolbar button, headerbar button",
            background_image="none",
            background_color="transparent",
            border_color="transparent",
        ),
        block(
            "button.flat:hover, toolbar button:hover, button.flat:checked, toolbar button:checked",
            background_image=vertical("button-body"),
            border_color=stops.BORDER,
            box_shadow="none",
        ),
        block(
            "button.flat:active, toolbar button:active",
            background_image=vertical("button-pressed"),
            border_color=stops.BORDER,
        ),
        block(
            "entry, spinbutton, textview, .view, treeview.view",
            min_height="17px",
            padding="1px 2px",
            border="1px solid " + field_border,
            border_radius="0",
            background_color="#FFFFFF",
            background_image="none",
            color="#000000",
            box_shadow="inset 0 0 0 1px #FFFFFF",
        ),
        block(
            "entry:disabled, spinbutton:disabled",
            border_color=stops.DISABLED_BORDER,
            background_color=FACE,
            color=stops.DISABLED_TEXT,
        ),
        block(
            "selection, entry selection, text selection, .view:selected, row:selected, treeview.view:selected, menuitem:hover, modelbutton:hover, "
            "iconview:selected, calendar:selected",
            background_color=SELECTION,
            background_image="none",
            color="#FFFFFF",
        ),
        block(
            "spinbutton button, combobox button.combo, combobox button",
            background_image=vertical("blue-button"),
            border="1px solid #B2C7F5",
            border_radius="2px",
            min_width="15px",
            padding="0",
        ),
        block(
            "spinbutton button:hover, combobox button:hover",
            background_image=vertical("blue-button-hover"),
            box_shadow=f"inset 0 0 0 1px {stops.HOVER_BORDER}",
        ),
        block(
            "spinbutton button:active, combobox button:active",
            background_image=vertical("blue-button-pressed"),
            box_shadow="none",
        ),
        block(
            "check, radio, checkbutton > check, checkbutton > radio, radiobutton > radio",
            min_width=f"{stops.INDICATOR_SIZE - 2}px",
            min_height=f"{stops.INDICATOR_SIZE - 2}px",
            padding="0",
            margin="0 3px 0 0",
            border="1px solid " + stops.CHECK_BORDER,
            background_image=vertical("check"),
            background_color="#FFFFFF",
            color="#000000",
        ),
        block("check", border_radius="0"),
        block("radio", border_radius="100%"),
        block("check:hover, radio:hover", box_shadow=CHECK_SHADOW),
        block("check:active, radio:active", background_image=vertical("check-pressed")),
        block(
            "check:checked, check:indeterminate",
            background_image=f"{tick_icon(stops.CHECK_MARK)}, {vertical('check')}",
            background_repeat="no-repeat",
            background_position="center",
        ),
        block("check:indeterminate", background_image=f"{mixed_icon(stops.CHECK_MARK)}, {vertical('check')}"),
        block(
            "radio:checked",
            background_image=f"{dot_icon(stops.CHECK_MARK)}, {vertical('check')}",
            background_repeat="no-repeat",
            background_position="center",
        ),
        block(
            "check:disabled, radio:disabled",
            border_color=stops.CHECK_BORDER_DISABLED,
            background_image=vertical("white-disabled"),
        ),
        block(
            "check:checked:disabled, check:indeterminate:disabled",
            background_image=f"{tick_icon(stops.CHECK_MARK_DISABLED)}, {vertical('white-disabled')}",
        ),
        block(
            "check:indeterminate:disabled",
            background_image=f"{mixed_icon(stops.CHECK_MARK_DISABLED)}, linear-gradient(to bottom, #FFFFFF, #FFFFFF)",
        ),
        block(
            "radio:checked:disabled",
            background_image=f"{dot_icon(stops.CHECK_MARK_DISABLED)}, {vertical('white-disabled')}",
        ),
        block(
            "notebook > stack, notebook > .frame",
            background_image=vertical("tab-page"),
            border="1px solid " + stops.PAGE_BORDER,
        ),
        block(
            "notebook > header > tabs > tab",
            min_height="19px",
            padding="0 8px",
            margin="2px 0 0 0",
            border="1px solid " + stops.PAGE_BORDER,
            border_radius="3px 3px 0 0",
            background_image=vertical("tab"),
            color="#000000",
        ),
        block(
            "notebook > header > tabs > tab:hover",
            box_shadow=f"inset 0 1px {stops.TAB_ORANGE[0]}, inset 0 3px {stops.TAB_ORANGE[2]}",
        ),
        block(
            "notebook > header > tabs > tab:checked",
            margin="0",
            background_image="none",
            background_color=GRADIENTS["tab-selected"][0][1],
            box_shadow=f"inset 0 1px {stops.TAB_ORANGE[0]}, inset 0 3px {stops.TAB_ORANGE[2]}",
        ),
        block("notebook > header > tabs > tab:disabled", color=stops.DISABLED_TEXT),
        block(
            "menu, .menu, .popup, popover.background > contents, popover.menu > contents",
            background_color="#FFFFFF",
            border="1px solid " + stops.MENU_BORDER,
            border_radius="0",
            padding="2px",
            color="#000000",
        ),
        block(
            "menuitem, modelbutton",
            min_height=f"{stops.SIZES['menu_item_height'] - 4}px",
            padding="0 4px",
            background_color="transparent",
            border_radius="0",
        ),
        block("menuitem:disabled, modelbutton:disabled", color=stops.DISABLED_TEXT),
        block("menu separator, popover separator", min_height="1px", margin="2px 0", background_color="#C6D7F1"),
        # GTK 4 popovers (GNOME Files' rename sheet): the popover node is .background, so the window rule would paint
        # it; the contents and the arrow are the white menu panel instead.
        block("popover.background", background_color="transparent", background_image="none", box_shadow="none"),
        block(
            "popover > contents",
            background_color="#FFFFFF",
            border="1px solid " + stops.MENU_BORDER,
            border_radius="0",
            padding="4px",
            color="#000000",
            box_shadow="none",
        ),
        block("popover > arrow", background_color="#FFFFFF", border="none", box_shadow="none"),
        block(
            "scrollbar",
            background_color="transparent",
            border="none",
            padding="0",
            margin="0",
            min_width=f"{stops.SIZES['scrollbar']}px",
            min_height=f"{stops.SIZES['scrollbar']}px",
        ),
        block(
            "scrollbar > range, scrollbar > range > trough",
            min_width=f"{stops.SIZES['scrollbar']}px",
            min_height=f"{stops.SIZES['scrollbar']}px",
            margin="0",
            padding="0",
            border="none",
            border_radius="0",
        ),
        block(
            "scrollbar.vertical trough",
            background_image=f"{stepper_image('up')}, {stepper_image('down')}, {TROUGH_ACROSS % 'right'}",
            background_repeat="no-repeat, no-repeat, repeat",
            background_position="center top, center bottom, center",
            padding="17px 0",
        ),
        block(
            "scrollbar.horizontal trough",
            background_image=f"{stepper_image('left')}, {stepper_image('right')}, {TROUGH_ACROSS % 'bottom'}",
            background_repeat="no-repeat, no-repeat, repeat",
            background_position="left center, right center, center",
            padding="0 17px",
        ),
        block(
            "scrollbar slider",
            min_width=f"{stops.SIZES['scrollbar'] - 2}px",
            min_height=f"{stops.SIZES['scrollbar'] - 2}px",
            margin="0",
            padding="0",
            border="1px solid #8AA3E6",
            border_radius="3px",
            background_image=vertical("thumb"),
        ),
        block("scrollbar slider:hover", background_image=vertical("thumb-hover")),
        block("scrollbar slider:active", border_color="#6F8DDB", background_image=vertical("thumb-pressed")),
        block(
            "scrollbar slider:disabled",
            border_color=stops.DISABLED_BORDER,
            background_image="none",
            background_color=FACE,
        ),
        block("progressbar", padding="0", border="none", background_image="none"),
        block(
            "progressbar > trough",
            min_width="0", min_height="0", padding="1px", margin="0",
            border="1px solid #68A3C6",
            background_color="#FFFFFF", background_image="none", border_radius="2px",
        ),
        block(
            "progressbar > trough > progress",
            min_width="0", min_height="0", padding="0", margin="0",
            border="none", border_radius="0", background_color="transparent",
            background_repeat="repeat", background_position="left top",
        ),
        block("progressbar.horizontal > trough > progress", min_height="13px"),
        block("progressbar.vertical > trough > progress", min_width="13px"),
        block("progressbar.horizontal > trough", min_height="13px"),
        block("progressbar.vertical > trough", min_width="13px"),
        *[
            block(
                f"progressbar.{orientation} > trough > progress",
                background_image=(
                    f"linear-gradient(to {direction}, {stops.GRADIENTS['progress-chunk'][1][1]} 0px, "
                    f"{stops.GRADIENTS['progress-chunk'][1][1]} {stops.PROGRESS_CHUNK_WIDTH}px, "
                    f"transparent {stops.PROGRESS_CHUNK_WIDTH}px, "
                    f"transparent {stops.PROGRESS_CHUNK_WIDTH + stops.PROGRESS_CHUNK_GAP}px)"
                ),
                background_size=(f"{stops.PROGRESS_CHUNK_WIDTH + stops.PROGRESS_CHUNK_GAP}px 100%"
                                 if orientation == "horizontal" else
                                 f"100% {stops.PROGRESS_CHUNK_WIDTH + stops.PROGRESS_CHUNK_GAP}px"),
                background_position="left top" if orientation == "horizontal" else "left bottom",
            )
            for orientation, direction in (("horizontal", "right"), ("vertical", "top"))
        ],
        block("progressbar > trough > progress.pulse", background_image="none",
              background_color=stops.GRADIENTS['progress-chunk'][1][1]),
        block(
            "scale trough",
            min_height=f"{stops.SIZES['slider_groove']}px",
            min_width=f"{stops.SIZES['slider_groove']}px",
            border="1px solid " + stops.MENU_BORDER,
            background_color=GRADIENTS["slider-groove"][0][1],
            border_radius="0",
        ),
        block("scale trough highlight, scale highlight", background_color=GRADIENTS["slider-filled"][0][1]),
        block(
            "scale slider",
            min_width=f"{stops.SIZES['slider_handle_width']}px",
            min_height=f"{stops.SIZES['slider_handle_length']}px",
            border="1px solid " + stops.CHECK_BORDER,
            border_radius="2px",
            background_image=vertical("slider-thumb"),
        ),
        block("scale slider:hover", box_shadow=CHECK_SHADOW),
        block("scale slider:active", background_image=vertical("check-pressed")),
        block(
            "scale slider:disabled",
            border_color=stops.CHECK_BORDER_DISABLED,
            background_image=vertical("white-disabled"),
        ),
        block(
            "treeview header button, columnview header button, column-header button",
            min_height=f"{stops.SIZES['header_height']}px",
            padding="0 6px",
            border_style="solid",
            border_width="0 1px 1px 0",
            border_color=stops.MENU_BORDER,
            border_radius="0",
            background_image="none",
            background_color=FACE,
        ),
        block(
            "treeview header button:hover, columnview header button:hover",
            background_color=GRADIENTS["face-hover"][0][1],
            box_shadow=f"inset 0 -2px {stops.HOVER_BORDER}",
        ),
        block(
            "treeview header button:active, columnview header button:active",
            background_color=GRADIENTS["face-pressed"][0][1],
            box_shadow="none",
        ),
        block(
            "tooltip, tooltip.background",
            background_color="#FFFFE1",
            background_image="none",
            color="#000000",
            border="1px solid #000000",
            border_radius="0",
            padding="0",
        ),
        block("frame > border, frame", border="1px solid " + stops.GROUP_BORDER, border_radius="4px"),
        block("separator", background_color=stops.MENU_BORDER, min_width="1px", min_height="1px"),
        block("label:disabled, *:disabled", color=stops.DISABLED_TEXT),
        block("label.title, headerbar .title", font_weight="bold"),
    ]
    return rules


LIBADWAITA_COLOURS = {
    "window-bg-color": FACE,
    "window-fg-color": "#000000",
    "view-bg-color": "#FFFFFF",
    "view-fg-color": "#000000",
    "headerbar-bg-color": FACE,
    "headerbar-fg-color": "#000000",
    "headerbar-border-color": FACE,
    "headerbar-backdrop-color": FACE,
    "headerbar-shade-color": "transparent",
    "headerbar-darker-shade-color": "transparent",
    "sidebar-bg-color": FACE,
    "sidebar-fg-color": "#000000",
    "sidebar-backdrop-color": FACE,
    "sidebar-border-color": stops.GROUP_BORDER,
    "sidebar-shade-color": "transparent",
    "secondary-sidebar-bg-color": FACE,
    "secondary-sidebar-fg-color": "#000000",
    "secondary-sidebar-backdrop-color": FACE,
    "secondary-sidebar-border-color": stops.GROUP_BORDER,
    "secondary-sidebar-shade-color": "transparent",
    "card-bg-color": "#FFFFFF",
    "card-fg-color": "#000000",
    "card-shade-color": "transparent",
    "dialog-bg-color": FACE,
    "dialog-fg-color": "#000000",
    "popover-bg-color": "#FFFFFF",
    "popover-fg-color": "#000000",
    "popover-shade-color": "transparent",
    "thumbnail-bg-color": "#FFFFFF",
    "thumbnail-fg-color": "#000000",
    "shade-color": "transparent",
    "scrollbar-outline-color": stops.MENU_BORDER,
    "accent-bg-color": SELECTION,
    "accent-fg-color": "#FFFFFF",
    "accent-color": SELECTION,
    "destructive-bg-color": "#CC0000",
    "destructive-fg-color": "#FFFFFF",
    "destructive-color": "#CC0000",
    "success-bg-color": stops.CHECK_MARK,
    "success-fg-color": "#000000",
    "success-color": stops.CHECK_MARK,
    "warning-bg-color": stops.HOVER_BORDER,
    "warning-fg-color": "#000000",
    "warning-color": stops.HOVER_BORDER,
    "error-bg-color": "#CC0000",
    "error-fg-color": "#FFFFFF",
    "error-color": "#CC0000",
    "border-color": stops.GROUP_BORDER,
}
LIBADWAITA_SETTINGS = {
    "border-opacity": "100%",
    "dim-opacity": "100%",
    "disabled-opacity": "100%",
    "window-radius": f"{TITLE_RADIUS}px",
}


def libadwaita_block():
    """libadwaita programs (GNOME Files among them) ignore gtk-theme-name and paint from these custom properties,
    read from the user's gtk.css (Setup imports the sheet there); the @define-color twins serve plain GTK 4 programs."""
    properties = "\n".join(
        f"  --{name}: {value};" for name, value in {**LIBADWAITA_COLOURS, **LIBADWAITA_SETTINGS}.items()
    )
    defines = "\n".join(
        f"@define-color {name.replace('-', '_')} {value};" for name, value in LIBADWAITA_COLOURS.items()
    )
    return f":root {{\n{properties}\n}}\n{defines}\n"


def indicator_backend_rules(version):
    # GTK3 draws a builtin black symbol over themed backgrounds unless suppressed.
    # GTK4's icon-size request otherwise expands the 13px box to 18px.
    return block("check, radio", **({"_gtk_icon_source": "none"} if version == "3.0" else {"_gtk_icon_size": "11px"}))


def build_css(version):
    header = f"/* Chicago95Luna GTK {version}: generated by luna/gtk/make_luna_gtk.py */\n"
    adwaita = libadwaita_block() if version == "4.0" else ""
    return (
        header
        + adwaita
        + indicator_backend_rules(version)
        + "\n".join(widget_rules())
        + "\n"
        + titlebar_block("title-active", "title-inactive", INACTIVE_CAPTION)
    )


def build_index():
    return (
        f"[Desktop Entry]\nType=X-GNOME-Metatheme\nName={THEME_NAME}\nComment=Windows XP Luna widgets\n"
        f"Encoding=UTF-8\n\n[X-GNOME-Metatheme]\nGtkTheme={THEME_NAME}\nMetacityTheme={THEME_NAME}\nIconTheme=Chicago95\n"
    )


def write_theme(out):
    for version in VERSIONS:
        assets = out / f"gtk-{version}" / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        for kind in ("tick", "mixed", "dot"):
            for colour in (stops.CHECK_MARK, stops.CHECK_MARK_DISABLED):
                (assets / f"{kind}-{colour.lstrip('#')}.png").write_bytes(indicator_png(kind, colour))
        (out / f"gtk-{version}").mkdir(parents=True, exist_ok=True)
        (out / f"gtk-{version}" / "gtk.css").write_text(build_css(version))
    (out / "index.theme").write_text(build_index())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=HERE / THEME_NAME)
    parser.add_argument("--titlebar", action="store_true", help="print the header bar block and exit")
    options = parser.parse_args()
    if options.titlebar:
        sys.stdout.write(titlebar_block("title-active", "title-inactive", INACTIVE_CAPTION))
    else:
        write_theme(options.out)
        print("wrote", options.out)
