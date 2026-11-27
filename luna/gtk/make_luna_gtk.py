"""Builds the Chicago95Luna GTK theme: the Windows XP Luna widget look for GTK 3 and GTK 4 programs.

    make_luna_gtk.py [--out DIR]
    make_luna_gtk.py --titlebar [--caption-assets DIR] [--dpi DPI]

Writes DIR/index.theme, DIR/gtk-3.0/gtk.css and DIR/gtk-4.0/gtk.css (default Chicago95Luna beside this file).
The colours and gradients are the ones of the Kvantum theme (luna/kvantum/stops.py, LunaStyle's measured
values), so the Qt and GTK widgets match. --titlebar prints the header bar block for ~/.config/gtk-N.0/gtk.css:
the vertical gradient of the Luna title bar from luna/palette.py, six pixel rounded top corners and the Trebuchet
MS bold caption with its dark shadow.
"""

import argparse
import base64
import importlib.util
import os
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
# window frame, counted from the outer edge on the left and from the face on the right and bottom (xprun.png,
# xpfont.png, xpcolour.png against xpnotepad.png).
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
aurorae = load_module("luna_aurorae_generator", LUNA_ROOT / "aurorae/make_luna_aurorae.py")
aurorae_stops = aurorae.stops
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
    sides = [(colours, offset) for colours, offset in zip((top, bottom, left, right), OFFSETS, strict=True) if colours]
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


def checkbox_frame_svg(colour, scale):
    # The 13px and 25px XP resources both have a single physical pixel of outline.
    side = stops.INDICATOR_SIZE * scale
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{side}" height="{side}">'
        f'<rect x=".5" y=".5" width="{side - 1}" height="{side - 1}" '
        f'fill="none" stroke="{colour}"/></svg>\n'
    )


def indicator_svg(kind, colour, scale=1):
    side = stops.INDICATOR_SIZE
    if kind == "tick":
        # Windows XP picks the larger of these resources from 185 DPI.
        side = 13 if scale == 1 else 25
        mark = kvantum.marks.tick_svg(side, colour)
        if scale == 1:
            mark = f'<g shape-rendering="crispEdges">{mark}</g>'
    elif kind == "mixed":
        mark = f'<rect x="3" y="3" width="7" height="7" fill="{colour}"/>'
    else:
        side = 13 if scale == 1 else 25
        radius = kvantum.marks.RADIO_RADIUS[side]
        disabled = colour == stops.CHECK_MARK_DISABLED
        fill = kvantum.marks.RADIO_DISABLED if disabled else "url(#radioMark)"
        mark = "" if disabled else f"<defs>{kvantum.marks.radio_gradient(side)}</defs>"
        snap = ' shape-rendering="crispEdges"' if scale == 1 else ""
        mark += f'<circle cx="{side / 2}" cy="{side / 2}" r="{radius}" fill="{fill}"{snap}/>'
    physical = stops.INDICATOR_SIZE * scale
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{physical}" height="{physical}" '
        f'viewBox="0 0 {side} {side}">{mark}</svg>\n'
    )


def checkbox_rules():
    # Each layer occupies the full indicator. Keeping the outline in the SVG lets
    # the two density variants retain the one-device-pixel edge from XP.
    yield block(
        "check, checkbutton > check",
        min_width="13px",
        min_height="13px",
        margin="0 3px 0 0",
        padding="0",
        border="0",
        border_radius="0",
        background_repeat="no-repeat",
        background_position="center",
        box_shadow="none",
    )
    for selected, mark_kind in (("", None), (":checked", "tick"), (":indeterminate", "mixed")):
        for state in ("", ":hover", ":active", ":disabled"):
            disabled = state == ":disabled"
            frame = density_pair("checkbox-frame-disabled" if disabled else "checkbox-frame")
            layers = [frame]
            if mark_kind:
                colour = stops.CHECK_MARK_DISABLED if disabled else stops.CHECK_MARK
                layers.append(indicator_icon(mark_kind, colour))
            if state == ":hover":
                # XP surrounds the pale centre with a gold gradient.
                centre = "#F4F4F2" if selected else "#E7E7E3"
                layers.extend(
                    [
                        f"linear-gradient({centre}, {centre})",
                        "linear-gradient(to bottom right, #FFF0CF 12%, #F8B330 88%)",
                    ]
                )
                sizes = ["100% 100%"] * (len(layers) - 2) + ["calc(100% - 5px) calc(100% - 5px)", "100% 100%"]
            else:
                if disabled:
                    colours = "#FFFFFF, #FFFFFF"
                elif state == ":active":
                    colours = "#B0B0A7 14%, #D7D5C8 50%, #F1EFDF 86%"
                elif selected:
                    colours = "#E2E2DD 14%, #F3F3F1 50%, #FFFFFF 86%"
                else:
                    colours = "#DCDCD7 14%, #F1F1EF 50%, #FFFFFF 86%"
                layers.append(f"linear-gradient(to bottom right, {colours})")
                sizes = ["100% 100%"] * len(layers)
            yield block(
                "check" + selected + state,
                background_image=", ".join(layers),
                background_size=", ".join(sizes),
                box_shadow="none",
            )


def notebook_rules():
    yield block(
        "notebook, notebook > header, notebook > header > tabs",
        padding="0",
        margin="0",
        border="0",
        box_shadow="none",
        background_image="none",
    )
    yield block(
        "notebook > stack, notebook > .frame",
        background_image=vertical("tab-page"),
        border="1px solid " + stops.PAGE_BORDER,
    )
    yield block(
        "notebook > header > tabs > tab",
        padding="0 5px",
        margin="0",
        min_height="16px",
        min_width="0",
        border_style="solid",
        border_color="transparent",
        border_radius="0",
        background_image="none",
        background_color="transparent",
        box_shadow="none",
        color="#000000",
    )
    yield block("notebook > header > tabs > tab label", padding="0", margin="0")
    for position, edge in (("top", "bottom"), ("bottom", "top"), ("left", "right"), ("right", "left")):
        header = f"notebook > header.{position}"
        horizontal = position in ("top", "bottom")
        yield block(
            header,
            background_image="linear-gradient(#919B9C, #919B9C)",
            background_repeat="no-repeat",
            background_position=edge,
            background_size="100% 1px" if horizontal else "1px 100%",
        )
        yield block(header + " + stack", **{f"border-{position}-width": "0"})
        for state, selected, hovered in (("", False, False), (":hover", False, True), (":checked", True, False)):
            if selected:
                edge_fill = "#E68B2C 0px, #E68B2C 1px, #919B9C 1px, #919B9C 100%"
                body_fill = "#E68B2C 0px, #E68B2C 1px, #FFC83C 1px, #FFC83C 2px, #FFC73C 2px, #FFC73C 3px, #FCFCFE 3px"
            else:
                edge_fill = (
                    "transparent 0px, transparent 2px, #919B9C 2px, #919B9C calc(100% - 1px), "
                    "transparent calc(100% - 1px)"
                )
                accent = "#FFC73C 2px, #FFC73C 4px, #FFFFFF 4px" if hovered else "#91A7B4 2px, #91A7B4 3px, #FFFFFF 3px"
                # The native 21px tab has a faster falloff near its white edge.
                # Place each colour at its sample centre to interpolate between rows at higher DPI.
                face = "#F0F0EA calc(100% - 2px)"
                if horizontal:
                    colours = (
                        "FEFEFE FCFCFB FAFAF9 F8F8F6 F6F6F3 F6F6F2 F5F5F1 F4F4F0 "
                        "F3F3EF F3F3EE F2F2ED F1F1ED F1F1EC F0F0EB F0F0EA"
                    ).split()
                    face = ", ".join(f"#{colour} {row + 4.5}px" for row, colour in enumerate(colours))
                body_fill = (
                    f"transparent 0px, transparent 2px, {accent}, {face}, "
                    "#ECEBE6 calc(100% - 2px), #ECEBE6 calc(100% - 1px), transparent calc(100% - 1px)"
                )
            yield block(
                header + " > tabs > tab" + state,
                border_width="0",
                border_image_source="none",
                background_image=(
                    f"linear-gradient(to {edge}, {edge_fill}), "
                    f"linear-gradient(to {edge}, {edge_fill}), "
                    f"linear-gradient(to {edge}, {body_fill})"
                ),
                background_size="1px 100%, 1px 100%, 1px 100%" if horizontal else "100% 1px, 100% 1px, 100% 1px",
                background_repeat="no-repeat, no-repeat, " + ("repeat-x" if horizontal else "repeat-y"),
                background_position="left top, right top, center" if horizontal else "left top, left bottom, center",
                background_origin="border-box",
                background_clip="border-box",
                min_height="21px" if horizontal else "14px",
                min_width="0" if horizontal else "21px",
                padding="0 6px" if horizontal else "6px 0",
            )
    yield block("notebook > header.top > tabs > tab:not(:checked) label", padding="2px 0 0")
    yield block("notebook > header.bottom > tabs > tab:not(:checked) label", padding="0 0 2px")
    yield block("notebook > header > tabs > tab:disabled", color=stops.DISABLED_TEXT)


def switch_svg(part, active=False, state="normal"):
    thumb = part == "thumb"
    width, height = (17, 17) if thumb else (36, 19)
    border = stops.DISABLED_BORDER if state == "disabled" else stops.CHECK_BORDER
    if thumb and state == "hovered":
        border = "#E59700"
    face = f'<rect width="{width}" height="{height}" rx="2" fill="{border}"/>'
    if thumb:
        name = {"pressed": "check-pressed", "disabled": "white-disabled"}.get(state, "button-body")
        colours = "".join(f'<stop offset="{t}" stop-color="{c}"/>' for t, c in GRADIENTS[name])
        content = (
            '<defs><linearGradient id="fill" gradientUnits="userSpaceOnUse" x1="0" y1="1.5" x2="0" y2="15.5">'
            f'{colours}</linearGradient></defs>{face}<rect x="1" y="1" width="15" height="15" fill="url(#fill)"/>'
        )
    else:
        fill = SELECTION if active and state != "disabled" else FACE
        ink = stops.DISABLED_TEXT if state == "disabled" else "#fff" if active else "#000"
        content = face + f'<rect x="1" y="1" width="34" height="17" fill="{fill}"/>'
        # The thumb covers one mark. GTK 4 mirrors the thumb in right-to-left layouts.
        for x in (9, 26):
            content += (
                f'<path d="M{x} 5v9" stroke="{ink}" stroke-width="2"/>'
                if active
                else f'<circle cx="{x + 0.5}" cy="9.5" r="3.625" fill="none" stroke="{ink}" stroke-width="2"/>'
            )
        if state == "focused":
            content += '<path d="M2 2.5h32m-32 14h32" stroke="black" stroke-dasharray="1 1"/>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">{content}</svg>\n'
    )


def switch_rules():
    yield block(
        "switch",
        min_width="34px",
        min_height="17px",
        padding="1px",
        margin="0",
        border="0",
        border_radius="0",
        box_shadow="none",
        outline="none",
        color="transparent",
        background_color="transparent",
        background_size="100% 100%",
        background_repeat="no-repeat",
        **{"-gtk-icon-source": "none", "-gtk-icon-shadow": "none"},
    )
    yield block("switch image, switch image:disabled", color="transparent", opacity="0", min_width="0", min_height="0")
    yield block(
        "switch slider",
        min_width="17px",
        min_height="17px",
        padding="0",
        margin="0",
        border="0",
        border_radius="0",
        box_shadow="none",
        background_color="transparent",
        background_size="100% 100%",
        background_repeat="no-repeat",
    )
    for active in (False, True):
        selector = "switch:checked" if active else "switch:not(:checked)"
        for state, pseudo in (
            ("normal", ""),
            ("hovered", ":hover"),
            ("pressed", ":active"),
            ("focused", ":focus"),
            ("disabled", ":disabled"),
        ):
            track = state if state in ("disabled", "focused") else "normal"
            yield block(
                selector + pseudo,
                color="transparent",
                background_image=f'url("assets/switch-{int(active)}-{track}.svg")',
            )
    for state, pseudo in (
        ("normal", ""),
        ("hovered", ":hover"),
        ("pressed", ":active"),
        ("focused", ":focus"),
        ("disabled", ":disabled"),
    ):
        thumb = "normal" if state == "focused" else state
        yield block(f"switch{pseudo} slider", background_image=f'url("assets/switch-thumb-{thumb}.svg")')


def slider_svg(horizontal, state, point=None, scale=1):
    width, height = slider.THUMB_SIZE if horizontal else slider.THUMB_SIZE[::-1]
    colours = slider.thumb_stops(state)
    gradient = "".join(f'<stop offset="{i / (len(colours) - 1)}" stop-color="{c}"/>' for i, c in enumerate(colours))
    light, dark = slider.THUMB_BORDER_LIGHT, slider.THUMB_BORDER_DARK
    top, bottom = slider.thumb_accent(state)
    if point:
        # Overlapping outlines form the light and dark bevel on the two sides
        # of the pointer. Each diagonal continues in a straight line at any scale.
        body = (
            f'<path d="M0 0h11v15.5L5.5 21 0 15.5z" fill="{dark}"/>'
            f'<path d="M0 0h10v15.5L5.5 20h-1L0 15.5z" fill="{light}"/>'
            '<path d="M1 1h9v14.5L5.5 20 1 15.5z" fill="url(#fill)"/>'
            f'<path d="M1.5 16h1l3.5 3.5-.5.5z" fill="{top}"/>'
            f'<path d="M8.5 16h1l-4 4-.5-.5z" fill="{bottom}"/>'
        )
    else:
        body = (
            f'<rect width="11" height="21" fill="{dark}"/><rect width="10" height="20" fill="{light}"/>'
            '<rect x="1" y="1" width="9" height="19" fill="url(#fill)"/>'
            f'<path d="M1 18.5h9" stroke="{bottom}"/><path d="M1 19.5h9" stroke="{top}"/>'
        )
    body += f'<path d="M1 1.5h9" stroke="{top}"/><path d="M1 2.5h9" stroke="{bottom}"/>'
    if point == "before":
        body = f'<g transform="translate(0 21) scale(1 -1)">{body}</g>'
    if not horizontal:
        body = f'<g transform="matrix(0 1 1 0 0 0)">{body}</g>'
    if point and scale == 1:
        body = f'<g shape-rendering="crispEdges">{body}</g>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width * scale}" height="{height * scale}" '
        f'viewBox="0 0 {width} {height}"><defs><linearGradient id="fill" gradientUnits="userSpaceOnUse" '
        f'x1="0" y1=".5" x2="0" y2="20.5">{gradient}</linearGradient></defs>{body}</svg>\n'
    )


def scale_rules():
    yield block("scale", padding="0", margin="0")
    yield block("scale.horizontal.marks-before, scale.horizontal.marks-after", min_height="26px")
    yield block("scale.vertical.marks-before, scale.vertical.marks-after", min_width="26px")
    yield block("scale marks", padding="0", margin="0", border="0")
    yield block("scale.horizontal marks.bottom", padding_top="2px")
    yield block("scale.horizontal marks.top", padding_bottom="2px")
    yield block("scale.vertical marks.bottom", padding_left="2px")
    yield block("scale.vertical marks.top", padding_right="2px")
    yield block(
        "scale mark indicator",
        color="#ACA899",
        background_color="#ACA899",
        background_image="none",
        border="0",
        padding="0",
        margin="0",
    )
    yield block("scale.horizontal mark indicator", min_width="1px", min_height="3px")
    yield block("scale.vertical mark indicator", min_width="3px", min_height="1px")
    yield block(
        "scale trough",
        padding="0",
        margin="0",
        border="0",
        border_radius="0",
        box_shadow="none",
        min_width="0",
        min_height="0",
    )
    yield block("scale highlight, scale fill", background="none", border="0", box_shadow="none")
    yield block(
        "scale slider",
        padding="0",
        border="0",
        border_radius="0",
        box_shadow="none",
        background_color="transparent",
        background_repeat="no-repeat",
        background_size="100% 100%",
    )
    for orientation, direction in (("horizontal", "bottom"), ("vertical", "right")):
        horizontal = orientation == "horizontal"
        bands = ", ".join(f"{colour} {i}px, {colour} {i + 1}px" for i, colour in enumerate(slider.GROOVE_ROWS))
        yield block(
            f"scale.{orientation} trough",
            min_height="1px" if horizontal else "0",
            min_width="0" if horizontal else "1px",
            background_image=f"linear-gradient(to {direction}, {bands})",
            background_size="100% 1px" if horizontal else "1px 100%",
            background_position="center",
            background_repeat="no-repeat",
        )
        yield block(
            f"scale.{orientation} slider",
            min_width="11px" if horizontal else "21px",
            min_height="21px" if horizontal else "11px",
            margin="-8px 0" if horizontal else "0 -8px",
        )
        yield block(f"scale.{orientation}.marks-before slider, scale.{orientation}.marks-after slider", margin="0")
        for state, pseudo in (("normal", ""), ("hover", ":hover"), ("pressed", ":active"), ("disabled", ":disabled")):
            yield block(
                f"scale.{orientation} slider{pseudo}",
                background_image=f'url("assets/slider-{orientation}-{state}.svg")',
            )
            for point in ("before", "after"):
                other = "after" if point == "before" else "before"
                yield block(
                    f"scale.{orientation}.marks-{point}:not(.marks-{other}) slider{pseudo}",
                    background_image=density_pair(f"slider-{orientation}-{state}-{point}"),
                )


def scale_backend_rules(version):
    # GTK3 positions the thumb centre at the track ends; GTK4 keeps the whole
    # thumb inside its allocation. Reserve half a thumb at each end in GTK3,
    # and inset only the painted track in GTK4.
    rules = []
    if version == "3.0":
        rules.append(block("scale.horizontal marks.top", padding_bottom="3px"))
        rules.append(block("scale.vertical marks.top", padding_right="3px"))
    for orientation in ("horizontal", "vertical"):
        horizontal = orientation == "horizontal"
        if version == "3.0":
            rules.append(block(f"scale.{orientation}", padding="0 5px" if horizontal else "5px 0"))
            # GTK3 draws its indicator line with inclusive endpoints (2 CSS pixels become 3).
            rules.append(
                block(
                    f"scale.{orientation} mark indicator",
                    min_height="2px" if horizontal else "1px",
                    min_width="1px" if horizontal else "2px",
                )
            )
        else:
            rules.append(
                block(
                    f"scale.{orientation} trough",
                    background_size="calc(100% - 10px) 1px" if horizontal else "1px calc(100% - 10px)",
                    background_position="center",
                    background_repeat="no-repeat",
                )
            )
    return "\n".join(rules)


def scrollbar_grip_svg(horizontal):
    """Four bevel ridges with a transparent trailing pixel for centring."""
    width, height = (9, 11) if horizontal else (11, 9)
    transform = "" if horizontal else ' transform="matrix(0 1 1 0 0 0)"'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
        f'  <g{transform}><rect width="8" height="11" fill="#ecf2fb"/>'
        '<path d="M.5 0v11m2-11v11m2-11v11m2-11v11" stroke="#98bae9"/></g>\n</svg>\n'
    )


def scrollbar_thumb_rules():
    for orientation, direction in (("horizontal", "bottom"), ("vertical", "right")):
        for state, gradient in (("", "thumb"), (":hover", "thumb-hover"), (":active", "thumb-pressed")):
            fill = vertical(gradient).replace("to bottom", f"to {direction}")
            yield block(
                f"scrollbar.{orientation} slider{state}",
                background_image=f'url("assets/scroll-grip-{orientation}.svg"), {fill}',
                background_repeat="no-repeat, no-repeat",
                background_position="center, center",
                background_size="9px 11px, 100% 100%" if orientation == "horizontal" else "11px 9px, 100% 100%",
            )
        yield block(f"scrollbar.{orientation} slider:disabled", background_image="none")


def density_pair(name):
    return f'-gtk-scaled(url("assets/{name}.svg"), url("assets/{name}@2.svg"))'


def indicator_icon(kind, colour):
    name = f"{kind}-{colour.lstrip('#')}"
    if kind != "mixed":
        return density_pair(name)
    return f'url("assets/{name}.svg")'


def radio_rules(assets=None):
    native_120dpi = assets is not None
    yield block(
        "radio, checkbutton > radio, radiobutton > radio",
        min_width="13px",
        min_height="13px",
        padding="0",
        margin="0 3px 0 0",
        border="0",
        background_color="transparent",
        background_repeat="no-repeat",
        background_position="center",
        box_shadow="none",
    )
    if native_120dpi:
        # The XP face is 16 physical pixels at 120 DPI. The indicator node
        # still needs a whole logical pixel allocation for GTK's layout.
        yield block("radio", background_size="12.8px 12.8px", background_position="left top")
    for checked in ("", ":checked"):
        for pseudo, state in (
            ("", "checked" if checked else "normal"),
            (":hover", "hover"),
            (":active", "pressed"),
            (":disabled", "disabled"),
        ):
            if native_120dpi:
                face = "normal" if state == "checked" else state
                layers = [f'url("{assets}/face-{face}.svg")']
                if checked:
                    mark = "disabled" if state == "disabled" else "normal"
                    layers.insert(0, f'url("{assets}/mark-{mark}.svg")')
            else:
                layers = [density_pair("radio-face-" + state)]
                if checked:
                    colour = stops.CHECK_MARK_DISABLED if state == "disabled" else stops.CHECK_MARK
                    layers.insert(0, indicator_icon("dot", colour))
            yield block("radio" + checked + pseudo, background_image=", ".join(layers))


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


CAPTION_KINDS = aurorae.DPI_CAPTION_KINDS
# A 22-unit GTK 3 background at 125% leaves a quarter device pixel on
# each side of the 27-pixel disabled Close face.
GTK3_DISABLED_CLOSE_SIZE = 22
CAPTION_STATES = (
    ("", 0),
    (":backdrop", 4),
    (":hover", 1),
    (":active", 2),
    (":disabled", 3),
    (":backdrop:hover", 5),
    (":backdrop:active", 6),
    (":backdrop:disabled", 7),
)


def caption_filename(kind, index):
    return f"{kind}-{aurorae.STATE_NAMES[aurorae.caption_art_index(kind, index)]}.svg"


def caption_url(asset):
    return 'url("' + (asset.as_uri() if asset.is_absolute() else asset.as_posix()) + '")'


def caption_controls(assets, *, gtk3=False, dpi=96):
    high_dpi = dpi == aurorae.LARGE_CAPTION_DPI
    size = aurorae.LARGE_CAPTION * 96 / dpi if high_dpi and not gtk3 else aurorae.BUTTON
    size = f"{size:g}px"
    rules = [
        block("headerbar", min_height="26px", padding="2px 4px"),
        block(
            "headerbar button",
            min_width="21px",
            min_height="21px",
            padding="0 3px",
            margin="0 1px",
            border="1px solid " + stops.BORDER,
            border_radius="3px",
            color="#000000",
            background_color=FACE,
            background_image=vertical("button-body"),
            box_shadow="none",
        ),
        block("headerbar button:hover", background_image=vertical("button-body"), box_shadow=HOVER_SHADOW),
        block("headerbar button:active", background_image=vertical("button-pressed"), box_shadow="none"),
        block("headerbar windowcontrols", padding="0", margin="0"),
    ]
    if gtk3:
        # GtkHeaderBar adds six pixels between controls. Keep Luna's
        # two-pixel gap after accounting for the preceding right margin.
        adjacent = "headerbar.titlebar button.titlebutton + button.titlebutton"
        for direction, side in (("ltr", "left"), ("rtl", "right")):
            margin = f"margin_{side}"
            rules.append(block(f"{adjacent}:dir({direction})", **{margin: "-5px"}))
            if high_dpi:
                # At 120 DPI the extra unit before Close keeps the three
                # faces in phase with the compositor's pixel sampling.
                rules.append(block(f"{adjacent}.close:dir({direction})", **{margin: "-4px"}))
    else:
        # GTK 4 rounds both margins separately. One spacing value preserves
        # the native 120-DPI pitch when the 27-pixel face is installed.
        rules.append(block("headerbar windowcontrols", border_spacing="1px" if high_dpi else "2px"))
    for kind in CAPTION_KINDS:
        css_kind = "maximize" if kind == "restore" else kind
        parent = "window.maximized headerbar" if kind == "restore" else "headerbar"
        bases = (f"{parent} button.titlebutton.{css_kind}", f"{parent} windowcontrols button.{css_kind}")
        position = "center"
        if high_dpi and not gtk3:
            # The 23-unit pitch paints 28.75 pixels at 125%. Move the outer
            # faces by a quarter pixel to keep the native 29-pixel spacing.
            # Raise every face by the same amount to align its vertical position.
            horizontal = {"minimize": "calc(50% - 0.2px)", "close": "calc(50% + 0.2px)"}
            position = f"{horizontal.get(kind, 'center')} calc(50% - 0.2px)"
        rules.append(
            block(
                ", ".join(bases),
                min_width=size,
                min_height=size,
                padding="0",
                margin="0 1px",
                border="none",
                border_radius="0",
                background_color="transparent",
                background_repeat="no-repeat",
                background_position=position,
                background_size=f"{size} {size}",
                box_shadow="none",
            )
        )
        if not gtk3:
            rules.append(block(bases[1], margin="0"))
        elif high_dpi and kind == "close":
            side = f"{GTK3_DISABLED_CLOSE_SIZE}px"
            rules.append(block(", ".join(base + ":disabled" for base in bases), background_size=f"{side} {side}"))
        rules.append(block(", ".join(base + " image" for base in bases), opacity="0"))
        for state, index in CAPTION_STATES:
            asset = assets / caption_filename(kind, index)
            image = caption_url(asset)
            if gtk3 and high_dpi:
                doubled = caption_url(asset.with_name(asset.stem + "@2.svg"))
                image = f"-gtk-scaled({image}, {doubled})"
            rules.append(
                block(
                    ", ".join(base + state for base in bases),
                    background_image=image,
                    background_color="transparent",
                    box_shadow="none",
                )
            )
    return "\n".join(rules)


def titlebar_block(active, inactive, caption, assets=Path("../caption"), *, gtk3=False, dpi=96):
    return (
        titlebar_state("", active, aurorae_stops.SIDE_OVERLAY, "#FFFFFF")
        + titlebar_state(":backdrop", inactive, aurorae_stops.INACTIVE_SIDE_OVERLAY, caption)
        + caption_controls(assets, gtk3=gtk3, dpi=dpi)
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
            "selection, entry selection, text selection, .view:selected, row:selected, treeview.view:selected, "
            "menuitem:hover, modelbutton:hover, "
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
        *radio_rules(),
        *checkbox_rules(),
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
            min_width="0",
            min_height="0",
            padding="1px",
            margin="0",
            border="1px solid #68A3C6",
            background_color="#FFFFFF",
            background_image="none",
            border_radius="2px",
        ),
        block(
            "progressbar > trough > progress",
            min_width="0",
            min_height="0",
            padding="0",
            margin="0",
            border="none",
            border_radius="0",
            background_color="transparent",
            background_repeat="repeat",
            background_position="left top",
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
                background_size=(
                    f"{stops.PROGRESS_CHUNK_WIDTH + stops.PROGRESS_CHUNK_GAP}px 100%"
                    if orientation == "horizontal"
                    else f"100% {stops.PROGRESS_CHUNK_WIDTH + stops.PROGRESS_CHUNK_GAP}px"
                ),
                background_position="left top" if orientation == "horizontal" else "left bottom",
            )
            for orientation, direction in (("horizontal", "right"), ("vertical", "top"))
        ],
        block(
            "progressbar > trough > progress.pulse",
            background_image="none",
            background_color=stops.GRADIENTS["progress-chunk"][1][1],
        ),
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
    return f":root {{\n{properties}\n}}\n{defines}\n{FILES_ADDRESS}"


FILES_ADDRESS = """
/* GNOME Files uses breadcrumbs where XP Explorer had a single Address field. */
.nautilus-window .nautilus-pathbar {
  background: #ffffff;
  border: 1px solid #7f9db9;
  border-radius: 0;
  padding: 0;
  box-shadow: none;
}
.nautilus-window .nautilus-pathbar button {
  min-height: 18px;
  margin: 0 2px;
  padding: 0 4px;
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}
.nautilus-window .nautilus-pathbar > menubutton > button box,
.nautilus-window .nautilus-pathbar > menubutton > button contents,
.nautilus-window .nautilus-pathbar > menubutton > button image {
  min-height: 0;
  margin: 0;
  padding: 0;
  -gtk-icon-size: 14px;
}
.nautilus-window .nautilus-pathbar label {
  font-size: 11px;
  font-weight: normal;
}
.nautilus-window .nautilus-pathbar button:hover {
  background: #eff5fb;
  box-shadow: inset 0 0 0 1px #a2bfd9;
}
.nautilus-window .nautilus-pathbar button:active {
  background: #d2e2f3;
  box-shadow: inset 0 0 0 1px #7f9db9;
}
"""


def indicator_backend_rules(version):
    # GTK3 draws a builtin black symbol over themed backgrounds unless suppressed.
    # GTK4's icon-size request otherwise expands the 13px box to 18px.
    return block("check, radio", **({"_gtk_icon_source": "none"} if version == "3.0" else {"_gtk_icon_size": "11px"}))


def scrollbar_backend_rules(version):
    rules = []
    if version == "3.0":
        rules.append(
            block(
                "scrollbar",
                **{
                    "_GtkScrollbar_has_backward_stepper": "true",
                    "_GtkScrollbar_has_forward_stepper": "true",
                },
            )
        )
        rules.append(
            block(
                "scrollbar button, scrollbar button:disabled",
                min_width="17px",
                min_height="17px",
                padding="0",
                margin="0",
                border="none",
                box_shadow="none",
                background_color="transparent",
                background_repeat="no-repeat",
                background_position="center",
                _gtk_icon_source="none",
            )
        )
    for orientation, first, last, across in (
        ("horizontal", "left", "right", "bottom"),
        ("vertical", "up", "down", "right"),
    ):
        rules.append(block(f"scrollbar.{orientation}", background_image=TROUGH_ACROSS % across))
        if version == "3.0":
            rules.append(block(f"scrollbar.{orientation} trough", padding="0", background_image=TROUGH_ACROSS % across))
            for node, direction in (("up", first), ("down", last)):
                for state, disabled in (("", False), (":disabled", True)):
                    rules.append(
                        block(
                            f"scrollbar.{orientation} button.{node}{state}",
                            background_image=stepper_image(direction, disabled),
                        )
                    )
        else:
            rules.append(
                block(
                    f"scrollbar.{orientation}:disabled trough",
                    background_image=f"{stepper_image(first, True)}, {stepper_image(last, True)}, "
                    + TROUGH_ACROSS % across,
                )
            )
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
        + titlebar_block("title-active", "title-inactive", INACTIVE_CAPTION, gtk3=version == "3.0")
    )


def build_index():
    return (
        f"[Desktop Entry]\nType=X-GNOME-Metatheme\nName={THEME_NAME}\nComment=Windows XP Luna widgets\n"
        f"Encoding=UTF-8\n\n[X-GNOME-Metatheme]\nGtkTheme={THEME_NAME}\nMetacityTheme={THEME_NAME}\nIconTheme=Chicago95\n"
    )


def write_caption_faces(folder, large, *, density=1):
    folder.mkdir(parents=True, exist_ok=True)
    intrinsic = (density * aurorae.BUTTON,) * 2 if density > 1 else None
    for kind in CAPTION_KINDS:
        for index in sorted({aurorae.caption_art_index(kind, index) for _, index in CAPTION_STATES}):
            path = folder / caption_filename(kind, index)
            if density > 1:
                path = path.with_name(f"{path.stem}@{density}.svg")
            if large and density > 1 and kind == "close" and index == 3:
                size = (density * GTK3_DISABLED_CLOSE_SIZE,) * 2
                face = aurorae.caption_face_svg(kind, index, large, intrinsic_size=size, padding=0.25)
            else:
                face = aurorae.caption_face_svg(kind, index, large, intrinsic_size=intrinsic)
            path.write_text(face)


def write_theme(out):
    captions = out / "caption"
    write_caption_faces(captions, False)
    write_caption_faces(captions / "large", True)
    radio_assets = out / "radio-120dpi"
    radio_assets.mkdir(parents=True, exist_ok=True)
    marks = kvantum.marks
    for state in ("normal", "hover", "pressed", "disabled"):
        (radio_assets / f"face-{state}.svg").write_text(marks.radio_face_svg(16, state, 16))
    for state in ("normal", "disabled"):
        gradient = marks.radio_gradient(16) if state == "normal" else ""
        fill = "url(#radioMark)" if gradient else marks.RADIO_DISABLED
        (radio_assets / f"mark-{state}.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
            f'<defs>{gradient}</defs><circle cx="8" cy="8" r="{marks.RADIO_RADIUS[16]:g}" fill="{fill}"/></svg>\n'
        )
    (out / "radio-120dpi.css").write_text("\n".join(radio_rules("radio-120dpi")))
    for version in VERSIONS:
        assets = out / f"gtk-{version}" / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        for orientation in ("horizontal", "vertical"):
            horizontal = orientation == "horizontal"
            for state in ("normal", "hover", "pressed", "disabled"):
                name = f"slider-{orientation}-{state}"
                (assets / f"{name}.svg").write_text(slider_svg(horizontal, state))
                for point in ("before", "after"):
                    (assets / f"{name}-{point}.svg").write_text(slider_svg(horizontal, state, point))
                    (assets / f"{name}-{point}@2.svg").write_text(slider_svg(horizontal, state, point, 2))
        for state in ("normal", "hovered", "pressed", "disabled"):
            (assets / f"switch-thumb-{state}.svg").write_text(switch_svg("thumb", state=state))
        for state in ("normal", "disabled", "focused"):
            for active in (False, True):
                (assets / f"switch-{int(active)}-{state}.svg").write_text(switch_svg("track", active, state))
        for orientation in ("horizontal", "vertical"):
            (assets / f"scroll-grip-{orientation}.svg").write_text(scrollbar_grip_svg(orientation == "horizontal"))
        for state in ("normal", "checked", "hover", "pressed", "disabled"):
            for size, physical, suffix in ((13, 13, ""), (25, 26, "@2")):
                (assets / f"radio-face-{state}{suffix}.svg").write_text(
                    kvantum.marks.radio_face_svg(size, state, physical)
                )
        for suffix, colour in (("", stops.CHECK_BORDER), ("-disabled", stops.CHECK_BORDER_DISABLED)):
            for scale in (1, 2):
                density = "" if scale == 1 else "@2"
                (assets / f"checkbox-frame{suffix}{density}.svg").write_text(checkbox_frame_svg(colour, scale))
        for kind in ("tick", "mixed", "dot"):
            for colour in (stops.CHECK_MARK, stops.CHECK_MARK_DISABLED):
                name = f"{kind}-{colour.lstrip('#')}"
                (assets / f"{name}.svg").write_text(indicator_svg(kind, colour))
                if kind != "mixed":
                    (assets / f"{name}@2.svg").write_text(indicator_svg(kind, colour, 2))
        for direction in STEPPER_ARROWS:
            for disabled in (False, True):
                suffix = "-disabled" if disabled else ""
                (assets / f"stepper-{direction}{suffix}.svg").write_text(stepper_svg(direction, disabled))
        (out / f"gtk-{version}" / "gtk.css").write_text(build_css(version))
    (out / "index.theme").write_text(build_index())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=HERE / THEME_NAME)
    parser.add_argument("--titlebar", action="store_true", help="print the header bar block and exit")
    parser.add_argument("--write-gtk3-hidpi-captions", action="store_true", help="write double-density caption SVGs")
    parser.add_argument("--caption-assets", type=Path, default=HERE / THEME_NAME / "caption")
    parser.add_argument("--dpi", type=int, default=96, help="display DPI for the managed titlebar rules")
    options = parser.parse_args()
    if options.write_gtk3_hidpi_captions:
        # Match GTK 3's 2× backing buffer for the 21px caption background.
        write_caption_faces(options.caption_assets / "large", True, density=2)
    elif options.titlebar:
        assets = options.caption_assets.resolve()
        gtk_version = os.environ.get("GTK_VERSION")
        if options.dpi >= aurorae.LARGE_CAPTION_DPI:
            assets /= "large"
        sys.stdout.write(titlebar_block(
            "title-active", "title-inactive", INACTIVE_CAPTION, assets, gtk3=gtk_version == "3.0", dpi=options.dpi
        ))
    else:
        write_theme(options.out)
        print("wrote", options.out)
