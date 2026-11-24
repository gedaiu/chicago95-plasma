"""Classic Windows title bars and caption faces for the GTK 3 and GTK 4 stylesheets.

    gtk_header.py [--active C[,C]] [--inactive C[,C]] [--inactive-text C]
                  [--face C] [--light C] [--shadow C] [--dark C]

libadwaita programs (GNOME Files among them) put their toolbar in the title bar. Here the header becomes a 9x window
top: an 18px title strip in the title colours holding the title and the window buttons, over the toolbar on the face.

The theme's buttons stretch with the header bar (GNOME Files' is twice a title bar's height) and draw the icon theme's
thin symbolic glyphs. Each button here paints one 16x14 face with the window decoration's own glyphs as a centred
background, so the face keeps its size in any bar, and the symbolic glyph is hidden behind it.
"""

import argparse
import base64
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "aurorae"))
from bevel import (  # noqa: E402
    CAPTION_H,
    CAPTION_H_120,
    CAPTION_W,
    CAPTION_W_120,
    caption_button_120,
    caption_face,
    caption_glyph,
    disabled_caption_glyph,
    svg,
)

# GTK 4 names the side of its window controls. GTK 3 and custom headers
# expose the same actions as titlebutton widgets.
CAPTION_BUTTONS = (
    "headerbar windowcontrols.start > button",
    "headerbar windowcontrols.end > button",
    "headerbar button.titlebutton",
)
# 9x leaves 2px before the close button; minimize and maximize sit flush.
CLOSE_GAP = 2
# At 120 DPI the native gap is three device pixels. GTK's two logical
# pixels leave the Close face half a pixel off the compositor grid.
CLOSE_OFFSET_120 = 0.4
STRIP = "toolbarview > .top-bar headerbar:not(.default-decoration)"
TITLE_H = 18
# The toolbar starts 2px under the strip; the title and the buttons are lifted from its row by the same amount.
TOOLBAR_TOP = TITLE_H + 2
CAPTION_TOP = 2
# Tall enough for the address field (23px with its bevel) and the 22px buttons, 4px around.
TOOLBAR_ROW = 31
# 9x toolbar buttons are square; every control in the row is this tall, centred in the row.
TOOL = 22
TOOL_GAP = (TOOLBAR_ROW - TOOL) // 2
# The header's text in pixels, the size of 9x's 8pt at 96 dpi: a desktop that raises the font DPI would otherwise grow
# the title past the strip and the controls past the row.
TEXT_SIZE = "11px"
ICON = 16
ICON_GAP = 2
# The window buttons and the icon leave the toolbar row for the strip; these take back the width they held in it.
BOX_SPACING = 6
SIDEBAR_INSET = 6
CONTROLS_WIDTH = {"end": 3 * CAPTION_W + CLOSE_GAP, "start": ICON + 2 * ICON_GAP}
# Every icon button in the header, wherever Nautilus nests it (stacks, bins, the title box); the window buttons and
# the address field's own button are set back below.
TOOLS = f"{STRIP} button.image-button, {STRIP} splitbutton > button"
SPLIT_ARROW = f"{STRIP} splitbutton > menubutton > button"


def raster_caption(source, converter):
    """Render one SVG face at the physical 120-DPI dimensions for GTK 4."""
    try:
        png = subprocess.run(
            [converter, "-w", str(CAPTION_W_120), "-h", str(CAPTION_H_120), str(source)],
            capture_output=True,
            check=True,
            timeout=10,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return source
    output = source.with_suffix(".png")
    output.write_bytes(png)
    return output


def face_url(kind, colours, pressed, disabled, assets, high_dpi, gtk4, converter):
    shift = 1 if pressed else 0
    if high_dpi:
        view_size = CAPTION_W_120, CAPTION_H_120
        body = caption_button_120(kind, colours, pressed, disabled)
        display_size = (CAPTION_W, CAPTION_H_120 / 1.25) if gtk4 else view_size
        artwork = svg(*display_size, body, view_size=view_size)
    else:
        glyph = (
            disabled_caption_glyph(kind, colours[2], 0, 0)
            if disabled else caption_glyph(kind, "#000000", shift, shift)
        )
        artwork = svg(CAPTION_W, CAPTION_H, caption_face(0, 0, colours, pressed) + glyph)
    if assets is not None:
        state = "disabled" if disabled else "pressed" if pressed else "normal"
        suffix = "-gtk4" if gtk4 and high_dpi else ""
        path = assets / f"{kind}-{state}{suffix}.svg"
        path.write_text(artwork)
        image = f'url("{path.resolve().as_uri()}")'
        if high_dpi and not gtk4:
            # GTK 3 selects assets for its integer-scale backing buffer.
            doubled = path.with_name(f"{path.stem}@2x.svg")
            doubled.write_text(svg(CAPTION_W_120 * 2, CAPTION_H_120 * 2, body, view_size=view_size))
            return f'-gtk-scaled({image}, url("{doubled.resolve().as_uri()}"))'
        if gtk4 and high_dpi and converter:
            return f'url("{raster_caption(path, converter).resolve().as_uri()}")'
        return image
    data = base64.b64encode(artwork.encode()).decode()
    return f'url("data:image/svg+xml;base64,{data}")'


def buttons(suffix="", ancestor=""):
    return ", ".join(f"{ancestor}{selector}{suffix}" for selector in CAPTION_BUTTONS)


GTK4_ONLY = re.compile(r"(?<![\w-])(?:filter|-gtk-icon-size|border-spacing):[^;}]*;?\n?")


def without_gtk4_properties(css):
    """GTK 3 warns on every start about the properties only GTK 4 knows; the sheets shared by both drop them."""
    return GTK4_ONLY.sub("", css)


def rule(selector, **properties):
    body = "".join(f"  {name.replace('_', '-')}: {value};\n" for name, value in properties.items())
    return f"{selector} {{\n{body}}}\n"


def caption_css(face, light, shadow, dark, assets=None, dpi=96, *, gtk4=True, converter=None):
    colours = (face, light, shadow, dark)
    high_dpi = dpi == 120
    face_height = CAPTION_H_120 * 96 / dpi if high_dpi else CAPTION_H
    if assets is not None:
        assets.mkdir(parents=True, exist_ok=True)
    rules = [
        rule(
            buttons(),
            min_width=f"{CAPTION_W}px",
            min_height=f"{face_height:g}px",
            padding="0",
            margin="0",
            border="none",
            border_radius="0",
            box_shadow="none",
            outline="none",
            background_color="transparent",
            background_repeat="no-repeat",
            background_position="left top" if high_dpi and gtk4 else "center",
            background_size=f"{CAPTION_W}px {face_height:g}px",
        ),
        rule(buttons(".close"), margin_left=f"{CLOSE_GAP}px"),
        # libadwaita pads the glyph 4px a side, which would widen each button to 24px around the 16px face.
        rule(buttons(" > image"), opacity="0", min_width="0", min_height="0", padding="0", margin="0"),
        # 9x greyed only the title of an unfocused window: libadwaita fades its whole header to half strength, and the
        # theme greys every label in it, the ones on raised grey buttons too, where they vanish.
        rule("headerbar:backdrop > windowhandle", filter="none"),
        rule("window:backdrop headerbar button:not(.flat):not(:disabled) label", color="#000000"),
    ]
    if high_dpi and gtk4:
        rules.append(rule(buttons(".close"), transform=f"translateX({CLOSE_OFFSET_120:g}px)"))
    faces = [(kind, f".{kind}", "") for kind in ("minimize", "maximize", "close")]
    faces.append(("restore", ".maximize", "window.maximized "))
    for kind, suffix, ancestor in faces:
        for states, pressed, disabled in (
            (("", ":hover", ":backdrop"), False, False),
            ((":active",), True, False),
            ((":disabled", ":backdrop:disabled"), False, True),
        ):
            selector = ", ".join(buttons(suffix + state, ancestor) for state in states)
            rules.append(
                rule(
                    selector,
                    border="none",
                    box_shadow="none",
                    background_color="transparent",
                    background_image=face_url(kind, colours, pressed, disabled, assets, high_dpi, gtk4, converter),
                )
            )
    return "".join(rules)


def gradient(colours):
    """A title colour, or start,end for a left-to-right gradient, as a CSS image."""
    start, _comma, end = colours.partition(",")
    return f"linear-gradient(to right, {start}, {end or start})"


def header_css(active, inactive, inactive_text, face):
    # Lifted into a box exactly the strip's height: from the strip's top, ending TITLE_H below it.
    lifted = dict(margin_top=f"-{TOOLBAR_TOP}px", margin_bottom=f"{TOOLBAR_ROW + TOOLBAR_TOP - TITLE_H}px")
    first = {colours: colours.partition(",")[0] for colours in (active, inactive)}
    return "".join(
        [
            rule(
                f"{STRIP}, {STRIP}:backdrop",
                padding_top=f"{TOOLBAR_TOP}px",
                # The toolbar reaches the pane's edges, as the sidebar's selected row does.
                padding_left="0",
                padding_right="0",
                min_height=f"{TOOLBAR_ROW}px",
                color="#000000",
                background_color=face,
                background_image=gradient(active),
                background_size=f"100% {TITLE_H}px",
                background_repeat="no-repeat",
                background_position="top",
            ),
            rule(f"window:backdrop {STRIP}", background_image=gradient(inactive)),
            # The sidebar's header and the content's are two bars: the sidebar's keeps the start colour, and the
            # content's gradient starts from it, so the strip runs on unbroken.
            rule(f".sidebar-pane {STRIP}", background_image=gradient(first[active])),
            rule(f"window:backdrop .sidebar-pane {STRIP}", background_image=gradient(first[inactive])),
            # The Explorer divider begins below the header. Keep the sidebar
            # bevel on the places list so it stops short of the title strip.
            rule(".nautilus-window .sidebar-pane", border="none", box_shadow="none"),
            rule(
                ".nautilus-window .sidebar-pane placessidebar:dir(ltr)",
                border_right="1px solid #FFFFFF",
                box_shadow="inset -1px 0 var(--sidebar-border-color, #808080)",
            ),
            rule(
                ".nautilus-window .sidebar-pane placessidebar:dir(rtl)",
                border_left="1px solid #FFFFFF",
                box_shadow="inset 1px 0 var(--sidebar-border-color, #808080)",
            ),
            # libadwaita insets the sidebar's rows 6px from its edges: the sidebar's buttons line up with them.
            rule(
                f".sidebar-pane {STRIP}, .sidebar-pane {STRIP}:backdrop",
                padding_left=f"{SIDEBAR_INSET}px",
                padding_right=f"{SIDEBAR_INSET}px",
            ),
            # The location entry stretches to the row while the address field keeps its own 22px: 1px more gap a side
            # makes them the same height.
            rule(f"{STRIP} .linked > entry", margin=f"{TOOL_GAP + 1}px 0"),
            # The location entry's clear icon takes a large icon size from libadwaita: it would make the location page,
            # and with it every page of Files' header and the row, taller than the address field.
            rule(
                f"{STRIP} entry > image",
                min_width=f"{ICON}px",
                min_height=f"{ICON}px",
                margin="0",
                padding="0",
                _gtk_icon_size=f"{ICON}px",
            ),
            rule(f"{STRIP} label, {STRIP} text", font_size=TEXT_SIZE),
            rule(TOOLS, min_width=f"{TOOL}px", min_height=f"{TOOL}px", padding="0", margin=f"{TOOL_GAP}px 0"),
            # A split button's arrow half is narrow, as on 9x's Views button. The row's gap goes around the split button
            # as a whole: on its halves too, it would make the split button, and with it the row, 8px taller.
            rule(f"{STRIP} splitbutton", margin=f"{TOOL_GAP}px 0", padding="0"),
            rule(
                ", ".join(f"{STRIP} splitbutton > {half}" for half in ("button.image-button", "button", "menubutton")),
                margin="0",
            ),
            rule(SPLIT_ARROW, min_height=f"{TOOL}px", padding="0 2px", margin="0"),
            # Files keeps its header's pages (address field, location entry, search) one height: the search page's
            # filter button, sized as a toolbar button inside the search field, would make every page 7px taller.
            rule(
                f"{STRIP} .nautilus-query-editor button.image-button",
                min_width=f"{ICON}px",
                min_height="0",
                padding="0 2px",
                margin="0",
            ),
            # The theme leaves the split button's arrow without an icon in a focused window.
            rule(
                f"{SPLIT_ARROW} > arrow",
                color="#000000",
                min_width="8px",
                min_height="8px",
                _gtk_icon_source='-gtk-icontheme("pan-down-symbolic")',
            ),
            rule(f"{STRIP} arrow", color="#000000"),
            rule(
                f"{STRIP} windowcontrols > button.image-button",
                min_width=f"{CAPTION_W}px",
                min_height=f"{CAPTION_H}px",
                margin="0",
            ),
            rule(f"{STRIP} windowcontrols > button.image-button.close", margin_left=f"{CLOSE_GAP}px"),
            rule(
                f"{STRIP} .nautilus-pathbar button.image-button",
                min_width="0",
                min_height="0",
                margin="0",
                padding="0 3px",
            ),
            rule(f"{STRIP} windowcontrols", **lifted),
            rule(f"{STRIP} windowcontrols.end", margin_left=f"-{CONTROLS_WIDTH['end']}px"),
            rule(f"{STRIP} windowcontrols.start", margin_right=f"-{CONTROLS_WIDTH['start']}px"),
            # libadwaita spaces the header's boxes from code, which CSS cannot undo, and GTK stops a negative margin at
            # a widget's own width: the buttons beside the lifted controls take back the gap instead.
            rule(
                f"{STRIP} windowcontrols.start + button, {STRIP} windowcontrols.start + menubutton",
                margin_left=f"-{BOX_SPACING}px",
            ),
            rule(f"{STRIP} box.end > :nth-last-child(2)", margin_right=f"-{BOX_SPACING}px"),
            rule(
                f"{STRIP} windowcontrols > .icon",
                min_width=f"{ICON}px",
                min_height=f"{ICON}px",
                margin=f"0 {ICON_GAP}px",
                _gtk_icon_size=f"{ICON}px",
            ),
            # Lifted, a button reaches from the strip's top down into the toolbar row, however tall that row is: its
            # face goes 2px under the strip's top, where 9x drew it, not at the button's middle.
            rule(f"{STRIP} windowcontrols > button", background_position=f"center {CAPTION_TOP}px"),
            rule(f"{STRIP} windowtitle", **lifted),
            # Left-aligned after the icon as 9x drew it is out of CSS's reach: GTK centres a header's title.
            rule(f"{STRIP} windowtitle > .title", color="#FFFFFF", font_weight="bold", font_size=TEXT_SIZE),
            rule(f"window:backdrop {STRIP} windowtitle > .title", color=inactive_text),
            rule("toolbarview > .top-bar:backdrop > windowhandle", filter="none"),
            # Files stacks its toolbar over a tab bar, and libadwaita pads stacked bars 3px a side: the content's header
            # would start 3px under the sidebar's, and its row would grow 6px.
            rule("toolbarview > .top-bar .collapse-spacing", padding_top="0", padding_bottom="0"),
            # The theme paints flat header buttons white for the navy bar; under the strip they sit on the face.
            rule(
                ", ".join(
                    f"{STRIP} {button}:not(:disabled){part}"
                    for button in (
                        "button.flat",
                        "menubutton.flat > button",
                        "splitbutton.flat > button",
                        "splitbutton.flat > menubutton > button",
                    )
                    for part in ("", " label", " image", " arrow")
                ),
                color="#000000",
            ),
        ]
    )


PATH_BUTTON = ".nautilus-pathbar .nautilus-path-button"
WHOLE_SCREEN = ("maximized", "fullscreen", "tiled", "tiled-top", "tiled-bottom", "tiled-left", "tiled-right")


def frame_css(face, light, shadow, dark):
    """A self-drawn window's 4px raised frame, the window decoration's rings: the light and dark outer line, white and
    shadow inside it, then the face. A window filling the screen or tiled to an edge has none, like 9x's maximized
    ones. The transparent outer shadow keeps GTK's resize area around the frame."""
    return rule(
        "window.csd, window.csd:backdrop",
        padding="3px",
        border="1px solid",
        border_color=f"{light} {dark} {dark} {light}",
        border_radius="0",
        outline="none",
        box_shadow=f"inset 1px 1px #FFFFFF, inset -1px -1px {shadow}, 0 0 3px 3px transparent",
        background_color=face,
    ) + rule(", ".join(f"window.csd.{state}" for state in WHOLE_SCREEN), padding="0", border="none", box_shadow="none")


def unified_frame_css(face, light, shadow, dark):
    """libhandy's windows (GNOME Boxes among them) skip GTK 3's decoration frame and lay an overlay over their content
    instead: the same raised rings are drawn on it. GTK 3 paints the last inset shadow on top."""
    whole_screen = "".join(f":not(.{state})" for state in WHOLE_SCREEN)
    rings = [
        f"inset 4px 4px {face}",
        f"inset -4px -4px {face}",
        "inset 2px 2px #FFFFFF",
        f"inset -2px -2px {shadow}",
        f"inset 1px 1px {light}",
        f"inset -1px -1px {dark}",
    ]
    # A VM's screen draws on a surface of its own, above the overlay: the content steps inside the frame instead.
    return rule(f"window.unified{whole_screen} > decoration-overlay", box_shadow=", ".join(rings)) + rule(
        f"window.unified{whole_screen} > deck > *", margin="4px"
    )


def path_bar_css(light, shadow, dark):
    """GNOME Files' path bar as Explorer's Address bar: one sunken white field with the folders as plain text in it,
    not a row of raised buttons crowding the slashes between them."""
    flat = dict(margin="0", padding="0 3px", min_height="0", border="none", border_radius="0")
    return "".join(
        [
            # Ctrl+L swaps the field for a location entry: the same sunken field, the same size.
            rule(
                f".nautilus-pathbar, {STRIP} entry",
                margin=f"{TOOL_GAP}px 0",
                padding="1px 2px",
                border_radius="0",
                border_style="solid",
                border_width="1px",
                border_color=f"{shadow} #FFFFFF #FFFFFF {shadow}",
                box_shadow=f"inset 1px 1px {dark}, inset -1px -1px {light}",
                background_color="#FFFFFF",
                background_image="none",
            ),
            rule(
                f"{PATH_BUTTON}, {PATH_BUTTON}:hover, {PATH_BUTTON}:backdrop",
                **flat,
                box_shadow="none",
                background="none",
                color="#000000",
            ),
            # libadwaita dims every folder but the current one, and the theme bolds some: the Address bar did neither.
            rule(
                f"{PATH_BUTTON} label, {PATH_BUTTON} label.heading, {PATH_BUTTON} image",
                opacity="1",
                color="#000000",
                font_weight="normal",
            ),
            rule(f"{PATH_BUTTON} > box", border_spacing="4px"),
            # libadwaita pads the field's insides for a rounded pill; the Address bar was one line of text.
            rule(
                ", ".join(f".nautilus-pathbar {part}" for part in ("scrolledwindow", "box", "button", "menubutton")),
                min_height="0",
                padding_top="0",
                padding_bottom="0",
                margin_top="0",
                margin_bottom="0",
            ),
            rule(f"{PATH_BUTTON}:hover", box_shadow=f"inset 1px 1px #FFFFFF, inset -1px -1px {shadow}"),
            rule(f"{PATH_BUTTON}:active", box_shadow=f"inset 1px 1px {shadow}, inset -1px -1px #FFFFFF"),
        ]
    )


def list_view_css():
    """GNOME Files' list view as Explorer's Details view: the column headers run edge to edge. Files pads the view 24px
    a side, which left a white cell before the first header and after the last, and moves the rows back over it."""
    return "".join(
        [
            rule(".nautilus-list-view columnview", padding_left="0", padding_right="0"),
            rule(".nautilus-list-view columnview > listview", margin_left="0", margin_right="0"),
            rule(".nautilus-list-view columnview > listview > row", margin_left="0", margin_right="0"),
        ]
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gtk", default="4.0", help="the GTK version the sheet is for: 3.0 draws its own frames")
    parser.add_argument("--dpi", type=int, default=96)
    parser.add_argument("--active", default="#000080")
    parser.add_argument("--inactive", default="#808080")
    parser.add_argument("--inactive-text", default="#C0C0C0")
    parser.add_argument("--face", default="#C0C0C0")
    parser.add_argument("--light", default="#DFDFDF")
    parser.add_argument("--shadow", default="#808080")
    parser.add_argument("--dark", default="#000000")
    parser.add_argument("--caption-assets", type=Path, help="write caption artwork for GTK to load from disk")
    args = parser.parse_args()
    sheet = (
        caption_css(
            args.face,
            args.light,
            args.shadow,
            args.dark,
            args.caption_assets,
            args.dpi,
            gtk4=args.gtk == "4.0",
            converter=shutil.which("rsvg-convert"),
        )
        + header_css(args.active, args.inactive, args.inactive_text, args.face)
        + path_bar_css(args.light, args.shadow, args.dark)
        + list_view_css()
    )
    if args.gtk == "4.0":
        sys.stdout.write(sheet + frame_css(args.face, args.light, args.shadow, args.dark))
    else:
        sys.stdout.write(
            without_gtk4_properties(sheet) + unified_frame_css(args.face, args.light, args.shadow, args.dark)
        )


if __name__ == "__main__":
    main()
