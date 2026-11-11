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
CAPTION_SIZE = "10pt"  # kdeglobals WM activeFont, the Luna font step's Trebuchet MS 10
TITLE_RADIUS = 6
INACTIVE_CAPTION = "#D8E4F8"
VERSIONS = ("3.0", "4.0")
# A fixed size XP dialog has a 3 pixel frame where a resizable window has 4: per side it keeps these bands of the
# window frame, counted from the outer edge on the left and from the face on the right and bottom (xprun.png, xpfont.png,
# xpcolour.png against xpnotepad.png).
DIALOG_FRAME_BANDS = {"left": (1, 2, 3), "right": (1, 2, 3), "bottom": (0, 2, 3)}
DIALOG_FRAME = 3
DIALOG_TITLE_HEIGHT = 29
SIDE_SHADING_WIDTH = 28  # the Aurorae decoration's CORNER_W, over which its title darkens towards each frame edge


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


slider = load_module("luna_slider_art", LUNA_ROOT / "lib/chicago95lunaslider.py")
inputs = load_module("gtk_input_rules", LUNA_ROOT.parent / "lib/gtk_inputs.py")
kvantum = load_module("luna_kvantum_generator", LUNA_ROOT / "kvantum/make_luna_kvantum.py")
aurorae_stops = load_module("luna_aurorae_stops", LUNA_ROOT / "aurorae/stops.py")
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


OFFSETS = ("0 {}px", "0 -{}px", "{}px 0", "-{}px 0")


def band_shadow(top, bottom, left, right):
    """Inset one pixel bands, each side's colours given from the outer edge in. GTK paints the last shadow on top, so
    the deepest band comes first and every shallower one covers all but its innermost pixel. A side given as None
    gets no bands."""
    sides = [(colours, offset) for colours, offset in zip((top, bottom, left, right), OFFSETS) if colours]
    depth = min(len(colours) for colours, _ in sides)
    return ", ".join(
        f"inset {offset.format(band)} {colours[band - 1]}" for band in range(depth, 0, -1) for colours, offset in sides
    )


def dialog_frame(frame_left, frame_bottom):
    """The left, right and bottom of a dialog's frame; the right edge shares the bottom's colours, as Aurorae's does."""

    def kept(colours, side):
        return [colours[band] for band in DIALOG_FRAME_BANDS[side]]

    return band_shadow(
        None,
        kept(frame_bottom, "bottom")[::-1],
        kept(frame_left, "left"),
        kept(frame_bottom, "right")[::-1],
    )


def rgba(colour, opacity):
    return f"rgba({int(colour[1:3], 16)}, {int(colour[3:5], 16)}, {int(colour[5:7], 16)}, {opacity})"


def side_shading(overlay, direction):
    """Aurorae's title side overlay: (distance from the frame edge, colour, opacity), held to SIDE_SHADING_WIDTH."""
    stops_text = ", ".join(f"{rgba(colour, opacity)} {distance}px" for distance, colour, opacity in overlay)
    _, last_colour, last_opacity = overlay[-1]
    return (
        f"linear-gradient(to {direction}, {stops_text}, {rgba(last_colour, last_opacity)} {SIDE_SHADING_WIDTH}px, "
        f"transparent {SIDE_SHADING_WIDTH}px)"
    )


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


def stepper_svg(direction, disabled=False):
    stops_markup = "".join(
        f'<stop offset="{offset}" stop-color="{colour}"/>'
        for offset, colour in zip((0, 0.5, 1), STEPPER_FACE, strict=True)
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{STEPPER_SIZE}" height="{STEPPER_SIZE}">'
        f'<defs><linearGradient id="f" x1="0" y1="0" x2="0" y2="1">{stops_markup}</linearGradient></defs>'
        f'<rect x="1.5" y="1.5" width="{STEPPER_SIZE - 3}" height="{STEPPER_SIZE - 3}" rx="2.5" fill="url(#f)"'
        f' stroke="{STEPPER_BORDER}"/>'
        f'<polygon points="{STEPPER_ARROWS[direction]}" fill="{STEPPER_ARROW}"/></svg>'
    )
    return svg.replace(STEPPER_ARROW, stops.DISABLED_TEXT) if disabled else svg


def stepper_image(direction, disabled=False):
    suffix = "-disabled" if disabled else ""
    return f'url("assets/stepper-{direction}{suffix}.svg")' 


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


def tab_png(selected, hovered, position, fill=False, edge=False):
    import io

    from PIL import Image

    image = Image.new("RGBA", (5, 21))
    gradient = ["#FFFFFF", "#FEFEFE", "#FCFCFB", "#FAFAF9", "#F8F8F6", "#F6F6F3", "#F6F6F2", "#F5F5F1",
                "#F4F4F0", "#F3F3EF", "#F3F3EE", "#F2F2ED", "#F1F1ED", "#F1F1EC", "#F0F0EB", "#F0F0EA"]
    for y in range(21):
        for x in range(5):
            colour = None
            if selected:
                colour = ("#E68B2C", "#FFC83C", "#FFC73C")[y] if y < 3 else "#FCFCFE"
                if x in (0, 4) and y > 0:
                    colour = "#919B9C"
            elif 2 <= y <= 19:
                colour = "#91A7B4" if y == 2 else "#ECEBE6" if y == 19 else gradient[y - 3]
                if hovered and y in (2, 3):
                    colour = "#FFC73C"
                if x in (0, 4):
                    colour = "#919B9C"
            if colour:
                image.putpixel((x, y), (*bytes.fromhex(colour[1:]), 255))
    if fill or edge:
        image = image.crop((0, 0, 1, 21) if edge else (2, 0, 3, 21))
    transforms = {"bottom": Image.Transpose.FLIP_TOP_BOTTOM, "left": Image.Transpose.ROTATE_90,
                  "right": Image.Transpose.ROTATE_270}
    if position in transforms:
        image = image.transpose(transforms[position])
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def notebook_rules():
    yield block("notebook, notebook > header, notebook > header > tabs", padding="0", margin="0",
                border="0", box_shadow="none", background_image="none")
    yield block("notebook > stack, notebook > .frame", background_image=vertical("tab-page"),
                border="1px solid " + stops.PAGE_BORDER)
    yield block("notebook > header > tabs > tab", padding="0 5px", margin="0", min_height="16px",
                min_width="0", border_style="solid", border_color="transparent", border_radius="0",
                background_image="none", background_color="transparent", box_shadow="none", color="#000000")
    yield block("notebook > header > tabs > tab label", padding="0", margin="0")
    for position, edge in (("top", "bottom"), ("bottom", "top"), ("left", "right"), ("right", "left")):
        header = f"notebook > header.{position}"
        horizontal = position in ("top", "bottom")
        yield block(header, background_image="linear-gradient(#919B9C, #919B9C)",
                    background_repeat="no-repeat", background_position=edge,
                    background_size="100% 1px" if horizontal else "1px 100%")
        yield block(header + " + stack", **{f"border-{position}-width": "0"})
        for state, selected, hovered in (("", False, False), (":hover", False, True), (":checked", True, False)):
            artwork = f"{position}-{int(selected)}-{int(hovered)}.png"
            yield block(header + " > tabs > tab" + state,
                        border_width="0", border_image_source="none",
                        background_image=(f'url("assets/tab-edge-{artwork}"), url("assets/tab-edge-{artwork}"), '
                                          f'url("assets/tab-fill-{artwork}")'),
                        background_size="1px 100%, 1px 100%, 1px 100%" if horizontal else "100% 1px, 100% 1px, 100% 1px",
                        background_repeat="no-repeat, no-repeat, " + ("repeat-x" if horizontal else "repeat-y"),
                        background_position="left top, right top, center" if horizontal else "left top, left bottom, center",
                        background_origin="border-box", background_clip="border-box",
                        min_height="21px" if horizontal else "14px", min_width="0" if horizontal else "21px",
                        padding="0 6px" if horizontal else "6px 0")
            if not horizontal:
                direction = "right" if position == "left" else "left"
                if selected:
                    edge_fill = "#E68B2C 0px, #E68B2C 1px, #919B9C 1px, #919B9C 100%"
                    body_fill = "#E68B2C 0px, #E68B2C 1px, #FFC83C 1px, #FFC83C 2px, #FFC73C 2px, #FFC73C 3px, #FCFCFE 3px"
                else:
                    edge_fill = ("transparent 0px, transparent 2px, #919B9C 2px, #919B9C calc(100% - 1px), "
                                 "transparent calc(100% - 1px)")
                    accent = "#FFC73C 2px, #FFC73C 4px, #FFFFFF 4px" if hovered else "#91A7B4 2px, #91A7B4 3px, #FFFFFF 3px"
                    body_fill = (f"transparent 0px, transparent 2px, {accent}, #F0F0EA calc(100% - 2px), "
                                 "#ECEBE6 calc(100% - 2px), #ECEBE6 calc(100% - 1px), transparent calc(100% - 1px)")
                yield block(header + " > tabs > tab" + state,
                            background_image=(f"linear-gradient(to {direction}, {edge_fill}), "
                                              f"linear-gradient(to {direction}, {edge_fill}), "
                                              f"linear-gradient(to {direction}, {body_fill})"))
    yield block("notebook > header.top > tabs > tab:not(:checked) label", transform="translateY(1px)")
    yield block("notebook > header.bottom > tabs > tab:not(:checked) label", transform="translateY(-1px)")
    yield block("notebook > header > tabs > tab:disabled", color=stops.DISABLED_TEXT)


def switch_png(part, active=False, state="normal"):
    """Shared pixel artwork avoids different GTK built-in icons and corner rasterisation."""
    import io

    from PIL import Image, ImageColor, ImageDraw

    thumb = part == "thumb"
    width, height = (17, 17) if thumb else (36, 19)
    image = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(image)
    border = stops.DISABLED_BORDER if state == "disabled" else stops.CHECK_BORDER
    if thumb and state == "hovered":
        border = "#E59700"
    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=2, fill=border)
    if thumb:
        name = {"pressed": "check-pressed", "disabled": "white-disabled"}.get(state, "button-body")
        gradient = GRADIENTS[name]
        for y in range(1, height - 1):
            t = (y - 1) / (height - 3)
            for (left, first), (right, last) in zip(gradient, gradient[1:], strict=False):
                if left <= t <= right:
                    weight = (t - left) / max(right - left, 1e-9)
                    colour = tuple(round(a + (b - a) * weight)
                                   for a, b in zip(ImageColor.getrgb(first), ImageColor.getrgb(last), strict=True))
                    draw.line((1, y, width - 2, y), fill=colour)
                    break
    else:
        draw.rectangle((1, 1, width - 2, height - 2), fill=SELECTION if active and state != "disabled" else FACE)
        colour = stops.DISABLED_TEXT if state == "disabled" else "#FFFFFF" if active else "#000000"
        # Put the mark in both halves; the thumb covers one. GTK4 mirrors its
        # thumb in RTL, while GTK3 retains its physical left/right placement.
        for offset in (0, 17):
            if active:
                draw.rectangle((8 + offset, 5, 9 + offset, 13), fill=colour)
            else:
                draw.ellipse((5 + offset, 5, 13 + offset, 13), outline=colour, width=2)
        if state == "focused":
            for x in range(2, width - 2, 2):
                draw.point((x, 2), fill="#000000")
                draw.point((x, height - 3), fill="#000000")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def switch_rules():
    yield block("switch", min_width="34px", min_height="17px", padding="1px", margin="0",
                border="0", border_radius="0", box_shadow="none", outline="none",
                color="transparent", background_color="transparent", background_size="100% 100%",
                background_repeat="no-repeat", **{"-gtk-icon-source": "none", "-gtk-icon-shadow": "none"})
    yield block("switch image, switch image:disabled", color="transparent", opacity="0", min_width="0", min_height="0")
    yield block("switch slider", min_width="17px", min_height="17px", padding="0", margin="0",
                border="0", border_radius="0", box_shadow="none", background_color="transparent",
                background_size="100% 100%", background_repeat="no-repeat")
    for active in (False, True):
        selector = "switch:checked" if active else "switch:not(:checked)"
        for state, pseudo in (("normal", ""), ("hovered", ":hover"), ("pressed", ":active"),
                              ("focused", ":focus"), ("disabled", ":disabled")):
            yield block(selector + pseudo, color="transparent",
                        background_image=f'url("assets/switch-{int(active)}-{state}.png")')
    for state, pseudo in (("normal", ""), ("hovered", ":hover"), ("pressed", ":active"),
                          ("focused", ":focus"), ("disabled", ":disabled")):
        yield block(f"switch{pseudo} slider", background_image=f'url("assets/switch-thumb-{state}.png")')


def slider_png(horizontal, state, point=None):
    import io

    from PIL import Image

    width, height = slider.THUMB_SIZE if horizontal else slider.THUMB_SIZE[::-1]
    image = Image.new("RGBA", (width, height))
    image.putdata([(*bytes.fromhex(pixel[1:]), 255) if pixel else (0, 0, 0, 0)
                   for row in slider.thumb_pixels(width, height, horizontal, state, point) for pixel in row])
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def scale_rules():
    yield block("scale", padding="0", margin="0")
    yield block("scale.horizontal.marks-before, scale.horizontal.marks-after", min_height="26px")
    yield block("scale.vertical.marks-before, scale.vertical.marks-after", min_width="26px")
    yield block("scale marks", padding="0", margin="0", border="0")
    yield block("scale.horizontal marks.bottom", padding_top="2px")
    yield block("scale.horizontal marks.top", padding_bottom="2px")
    yield block("scale.vertical marks.right", padding_left="2px")
    yield block("scale.vertical marks.left", padding_right="2px")
    yield block("scale mark indicator", color="#ACA899", background_color="#ACA899", background_image="none",
                border="0", padding="0", margin="0")
    yield block("scale.horizontal mark indicator", min_width="1px", min_height="3px")
    yield block("scale.vertical mark indicator", min_width="3px", min_height="1px")
    yield block("scale trough", padding="0", margin="0", border="0", border_radius="0",
                box_shadow="none", min_width="0", min_height="0")
    yield block("scale highlight, scale fill", background="none", border="0", box_shadow="none")
    yield block("scale slider", padding="0", border="0", border_radius="0", box_shadow="none",
                background_color="transparent", background_repeat="no-repeat", background_size="100% 100%")
    for orientation, direction in (("horizontal", "bottom"), ("vertical", "right")):
        horizontal = orientation == "horizontal"
        bands = ", ".join(f"{colour} {i}px, {colour} {i + 1}px"
                          for i, colour in enumerate(slider.GROOVE_ROWS))
        yield block(f"scale.{orientation} trough",
                    min_height="1px" if horizontal else "0", min_width="0" if horizontal else "1px",
                    background_image=f"linear-gradient(to {direction}, {bands})",
                    background_size="100% 1px" if horizontal else "1px 100%",
                    background_position="center", background_repeat="no-repeat")
        yield block(f"scale.{orientation} slider", min_width="11px" if horizontal else "21px",
                    min_height="21px" if horizontal else "11px",
                    margin="-8px 0" if horizontal else "0 -8px")
        for state, pseudo in (("normal", ""), ("hover", ":hover"), ("pressed", ":active"),
                              ("disabled", ":disabled")):
            yield block(f"scale.{orientation} slider{pseudo}",
                        background_image=f'url("assets/slider-{orientation}-{state}.png")')
            for point in ("before", "after"):
                other = "after" if point == "before" else "before"
                yield block(f"scale.{orientation}.marks-{point}:not(.marks-{other}) slider{pseudo}",
                            background_image=f'url("assets/slider-{orientation}-{state}-{point}.png")')


def scale_backend_rules(version):
    # GTK3 positions the thumb centre at the track ends; GTK4 keeps the whole
    # thumb inside its allocation. Reserve half a thumb at each end in GTK3,
    # and inset only the painted track in GTK4.
    rules = []
    for orientation in ("horizontal", "vertical"):
        horizontal = orientation == "horizontal"
        if version == "3.0":
            rules.append(block(f"scale.{orientation}", padding="0 5px" if horizontal else "5px 0"))
            # GTK3 draws its indicator line with inclusive endpoints (2 CSS pixels become 3).
            rules.append(block(f"scale.{orientation} mark indicator",
                               min_height="2px" if horizontal else "1px",
                               min_width="1px" if horizontal else "2px"))
        else:
            rules.append(block(f"scale.{orientation} trough",
                               background_size="calc(100% - 10px) 1px" if horizontal else "1px calc(100% - 10px)",
                               background_position="center", background_repeat="no-repeat"))
    return "\n".join(rules)


def scrollbar_grip_png(horizontal):
    """Four alternating dark/light ridges, with a transparent trailing pixel for centring."""
    import io

    from PIL import Image

    image = Image.new("RGBA", (9, 11) if horizontal else (11, 9))
    for band in range(8):
        colour = (152, 186, 233, 255) if band % 2 == 0 else (236, 242, 251, 255)
        for across in range(11):
            image.putpixel((band, across) if horizontal else (across, band), colour)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def scrollbar_thumb_rules():
    for orientation, direction in (("horizontal", "bottom"), ("vertical", "right")):
        for state, gradient in (("", "thumb"), (":hover", "thumb-hover"), (":active", "thumb-pressed")):
            fill = vertical(gradient).replace("to bottom", f"to {direction}")
            yield block(
                f"scrollbar.{orientation} slider{state}",
                background_image=f'url("assets/scroll-grip-{orientation}.png"), {fill}',
                background_repeat="no-repeat, no-repeat",
                background_position="center, center",
                background_size="9px 11px, 100% 100%" if orientation == "horizontal" else "11px 9px, 100% 100%",
            )
        yield block(f"scrollbar.{orientation} slider:disabled", background_image="none")


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


TITLE_BARS = ("headerbar.titlebar", ".titlebar.default-decoration", "messagedialog .titlebar")


def titlebar_state(state, gradient, overlay, caption):
    """The bar paints the gradient; its title label only the caption text, or it would lay a shorter gradient of its
    own over the bar's."""
    bars = [bar + state for bar in TITLE_BARS]
    text = dict(
        color=caption,
        text_shadow=f"1px 1px 0 {CAPTION_SHADOW}",
        font_family=CAPTION_FONT,
        font_size=CAPTION_SIZE,
        font_weight="bold",
    )
    return block(
        ", ".join(bars),
        background_image=f"{side_shading(overlay['left'], 'right')}, {side_shading(overlay['right'], 'left')}, "
        + vertical(gradient),
        background_color=GRADIENTS[gradient][0][1],
        border_radius=f"{TITLE_RADIUS}px {TITLE_RADIUS}px 0 0",
        **text,
    ) + block(", ".join(f"{bar} .title" for bar in bars), **text)


def titlebar_block(active, inactive, caption):
    return titlebar_state("", active, aurorae_stops.SIDE_OVERLAY, "#FFFFFF") + titlebar_state(
        ":backdrop", inactive, aurorae_stops.INACTIVE_SIDE_OVERLAY, caption
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
        # GTK links a message box's buttons into one strip; XP spaced them 4 dialog units apart, 7 from the edges.
        block(
            "messagedialog .dialog-action-area > button:not(:first-child), "
            ".messagedialog .dialog-action-area > button:not(:first-child)",
            margin_left="6px",
        ),
        block("messagedialog .dialog-action-box, .messagedialog .dialog-action-box", padding="0 11px 11px 11px"),
        # GTK draws a message box's title itself, so no window manager frame surrounds it: its body draws one.
        block(
            "messagedialog .dialog-vbox",
            padding=f"0 {DIALOG_FRAME}px {DIALOG_FRAME}px {DIALOG_FRAME}px",
            box_shadow=dialog_frame(palette.PALETTE["border_left"], palette.PALETTE["border_bottom"]),
        ),
        block(
            "messagedialog .dialog-vbox:backdrop",
            box_shadow=dialog_frame(aurorae_stops.INACTIVE_BORDER_LEFT, aurorae_stops.INACTIVE_BORDER_BOTTOM),
        ),
        block("messagedialog .titlebar", min_height=f"{DIALOG_TITLE_HEIGHT}px"),
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
        *notebook_rules(),
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
            "scrollbar > range, scrollbar > range > trough, scrollbar contents, scrollbar trough",
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
        *scrollbar_thumb_rules(),
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
        *scale_rules(),
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
        *switch_rules(),
        block("frame", border="1px solid " + stops.GROUP_BORDER, border_radius="4px"),
        block("frame > border", border="none", padding="0", margin="0"),
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


def scrollbar_backend_rules(version):
    rules = []
    if version == "3.0":
        rules.append(block("scrollbar", **{
            "_GtkScrollbar_has_backward_stepper": "true",
            "_GtkScrollbar_has_forward_stepper": "true",
        }))
        rules.append(block("scrollbar button, scrollbar button:disabled", min_width="17px", min_height="17px",
                           padding="0", margin="0", border="none", box_shadow="none",
                           background_color="transparent", background_repeat="no-repeat",
                           background_position="center", _gtk_icon_source="none"))
    for orientation, first, last, across in (
        ("horizontal", "left", "right", "bottom"), ("vertical", "up", "down", "right")
    ):
        rules.append(block(f"scrollbar.{orientation}", background_image=TROUGH_ACROSS % across))
        if version == "3.0":
            rules.append(block(f"scrollbar.{orientation} trough", padding="0",
                               background_image=TROUGH_ACROSS % across))
            for node, direction in (("up", first), ("down", last)):
                for state, disabled in (("", False), (":disabled", True)):
                    rules.append(block(f"scrollbar.{orientation} button.{node}{state}",
                                       background_image=stepper_image(direction, disabled)))
        else:
            rules.append(block(f"scrollbar.{orientation}:disabled trough",
                               background_image=f"{stepper_image(first, True)}, {stepper_image(last, True)}, "
                                                + TROUGH_ACROSS % across))
    return "\n".join(rules) + "\n"


def input_backend_rules(version):
    # Committed themes use relative asset paths and remain relocatable.
    root = HERE / THEME_NAME
    return inputs.input_css(root, version, luna=True).replace((root / f"gtk-{version}").as_uri() + "/", "")


def build_css(version):
    header = f"/* Chicago95Luna GTK {version}: generated by luna/gtk/make_luna_gtk.py */\n"
    adwaita = libadwaita_block() if version == "4.0" else ""
    return (
        header
        + adwaita
        + indicator_backend_rules(version)
        + "\n".join(widget_rules())
        + scale_backend_rules(version)
        + scrollbar_backend_rules(version)
        + input_backend_rules(version)
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
        for orientation in ("horizontal", "vertical"):
            (assets / f"scroll-grip-{orientation}.png").write_bytes(scrollbar_grip_png(orientation == "horizontal"))
        for orientation in ("horizontal", "vertical"):
            for state in ("normal", "hover", "pressed", "disabled"):
                (assets / f"slider-{orientation}-{state}.png").write_bytes(
                    slider_png(orientation == "horizontal", state))
                for point in ("before", "after"):
                    (assets / f"slider-{orientation}-{state}-{point}.png").write_bytes(
                        slider_png(orientation == "horizontal", state, point))
        for state in ("normal", "hovered", "pressed", "focused", "disabled"):
            (assets / f"switch-thumb-{state}.png").write_bytes(switch_png("thumb", state=state))
            for active in (False, True):
                (assets / f"switch-{int(active)}-{state}.png").write_bytes(switch_png("track", active, state))
        for position in ("top", "bottom", "left", "right"):
            for selected, hovered in ((False, False), (False, True), (True, False)):
                (assets / f"tab-edge-{position}-{int(selected)}-{int(hovered)}.png").write_bytes(
                    tab_png(selected, hovered, position, edge=True))
                (assets / f"tab-fill-{position}-{int(selected)}-{int(hovered)}.png").write_bytes(
                    tab_png(selected, hovered, position, fill=True))
        for direction in STEPPER_ARROWS:
            for disabled in (False, True):
                suffix = "-disabled" if disabled else ""
                (assets / f"stepper-{direction}{suffix}.svg").write_text(stepper_svg(direction, disabled))
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
