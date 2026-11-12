"""GTK 4's headers as 9x windows, for the title bar block in gtk.css.

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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "aurorae"))
from bevel import CAPTION_H, CAPTION_W, caption_face, caption_glyph, svg  # noqa: E402

# The theme's own rules name a side (windowcontrols.end > button) and come in through an @import in the same sheet:
# naming the header bar too outranks every one of them.
SIDES = ("headerbar windowcontrols.start > button", "headerbar windowcontrols.end > button")
# 9x leaves 2px before the close button; minimize and maximize sit flush.
CLOSE_GAP = 2
STRIP = "toolbarview > .top-bar headerbar:not(.default-decoration)"
TITLE_H = 18
# The toolbar starts 2px under the strip; the title and the buttons are lifted from its row by the same amount.
TOOLBAR_TOP = TITLE_H + 2
CAPTION_TOP = 2
TOOLBAR_ROW = 30
SIDEBAR_BUTTON_GAP = 3


def face_url(kind, colours, pressed):
    shift = 1 if pressed else 0
    body = caption_face(0, 0, colours, pressed) + caption_glyph(kind, "#000000", shift, shift)
    data = base64.b64encode(svg(CAPTION_W, CAPTION_H, body).encode()).decode()
    return f'url("data:image/svg+xml;base64,{data}")'


def buttons(suffix="", ancestor=""):
    return ", ".join(f"{ancestor}{side}{suffix}" for side in SIDES)


def rule(selector, **properties):
    body = "".join(f"  {name.replace('_', '-')}: {value};\n" for name, value in properties.items())
    return f"{selector} {{\n{body}}}\n"


def caption_css(face, light, shadow, dark):
    colours = (face, light, shadow, dark)
    rules = [
        rule(
            buttons(),
            min_width=f"{CAPTION_W}px",
            min_height=f"{CAPTION_H}px",
            padding="0",
            margin="0",
            border="none",
            border_radius="0",
            box_shadow="none",
            outline="none",
            background_color="transparent",
            background_repeat="no-repeat",
            background_position="center",
            background_size=f"{CAPTION_W}px {CAPTION_H}px",
        ),
        rule(buttons(".close"), margin_left=f"{CLOSE_GAP}px"),
        # libadwaita pads the glyph 4px a side, which would widen each button to 24px around the 16px face.
        rule(buttons(" > image"), opacity="0", min_width="0", min_height="0", padding="0", margin="0"),
        # 9x greyed only the title of an unfocused window: libadwaita fades its whole header to half strength, and the
        # theme greys every label in it, the ones on raised grey buttons too, where they vanish.
        rule("headerbar:backdrop > windowhandle", filter="none"),
        rule("window:backdrop headerbar button:not(.flat):not(:disabled) label", color="#000000"),
    ]
    faces = [(kind, f".{kind}", "") for kind in ("minimize", "maximize", "close")]
    faces.append(("restore", ".maximize", "window.maximized "))
    for kind, suffix, ancestor in faces:
        for state, pressed in (("", False), (":hover", False), (":backdrop", False), (":active", True)):
            rules.append(
                rule(
                    buttons(suffix + state, ancestor),
                    border="none",
                    box_shadow="none",
                    background_color="transparent",
                    background_image=face_url(kind, colours, pressed),
                )
            )
    return "".join(rules)


def gradient(colours):
    """A title colour, or start,end for a left-to-right gradient, as a CSS image."""
    start, _comma, end = colours.partition(",")
    return f"linear-gradient(to right, {start}, {end or start})"


def header_css(active, inactive, inactive_text, face):
    lifted = dict(margin_top=f"-{TOOLBAR_TOP}px", margin_bottom=f"{TOOLBAR_TOP}px")
    first = {colours: colours.partition(",")[0] for colours in (active, inactive)}
    return "".join(
        [
            rule(
                f"{STRIP}, {STRIP}:backdrop",
                padding_top=f"{TOOLBAR_TOP}px",
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
            # The address field makes the content's row taller than the sidebar's: both rows take its height, and
            # the sidebar's buttons keep theirs in the middle of it.
            rule(
                f".sidebar-pane {STRIP} button",
                margin_top=f"{SIDEBAR_BUTTON_GAP}px",
                margin_bottom=f"{SIDEBAR_BUTTON_GAP}px",
            ),
            rule(f"{STRIP} windowcontrols", **lifted),
            # Lifted, a button reaches from the strip's top down into the toolbar row, however tall that row is: its
            # face goes 2px under the strip's top, where 9x drew it, not at the button's middle.
            rule(f"{STRIP} windowcontrols > button", background_position=f"center {CAPTION_TOP}px"),
            rule(f"{STRIP} windowtitle", **lifted),
            rule(f"{STRIP} windowtitle > .title", color="#FFFFFF", font_weight="bold"),
            rule(f"window:backdrop {STRIP} windowtitle > .title", color=inactive_text),
            rule("toolbarview > .top-bar:backdrop > windowhandle", filter="none"),
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


def path_bar_css(light, shadow, dark):
    """GNOME Files' path bar as Explorer's Address bar: one sunken white field with the folders as plain text in it,
    not a row of raised buttons crowding the slashes between them."""
    flat = dict(margin="0", padding="0 3px", min_height="0", border="none", border_radius="0")
    return "".join(
        [
            rule(
                ".nautilus-pathbar",
                padding="2px",
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
            rule(f"{PATH_BUTTON} label, {PATH_BUTTON} image", opacity="1", color="#000000", font_weight="normal"),
            rule(f"{PATH_BUTTON} > box", border_spacing="4px"),
            rule(f"{PATH_BUTTON}:hover", box_shadow=f"inset 1px 1px #FFFFFF, inset -1px -1px {shadow}"),
            rule(f"{PATH_BUTTON}:active", box_shadow=f"inset 1px 1px {shadow}, inset -1px -1px #FFFFFF"),
        ]
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gtk", default="4.0", help="the GTK version the sheet is for: 3.0 draws its own frames")
    parser.add_argument("--active", default="#000080")
    parser.add_argument("--inactive", default="#808080")
    parser.add_argument("--inactive-text", default="#C0C0C0")
    parser.add_argument("--face", default="#C0C0C0")
    parser.add_argument("--light", default="#DFDFDF")
    parser.add_argument("--shadow", default="#808080")
    parser.add_argument("--dark", default="#000000")
    args = parser.parse_args()
    sys.stdout.write(caption_css(args.face, args.light, args.shadow, args.dark))
    sys.stdout.write(header_css(args.active, args.inactive, args.inactive_text, args.face))
    sys.stdout.write(path_bar_css(args.light, args.shadow, args.dark))
    if args.gtk == "4.0":
        sys.stdout.write(frame_css(args.face, args.light, args.shadow, args.dark))


if __name__ == "__main__":
    main()
