"""Firefox's own controls in the look: a style sheet for its buttons, check boxes, radio buttons and drop-downs.

    firefox_chrome.py OUTPUT.css

Firefox draws its controls itself, flat and rounded, whatever the GTK theme; GTK only lends them its colours. A
profile's chrome/userChrome.css is the one place left to restyle them (Setup imports this sheet from it), read once
toolkit.legacyUserProfileCustomizations.stylesheets is on (config/firefox-user.js). The bevels are inset shadows in the
colour scheme's face and the look's 3D lines; the radio button's rings and the marks are CSS borders and gradients,
since Firefox's own windows refuse data: images. A user sheet reaches inside Firefox's shadow trees, so the drop-down's
arrow button takes it too.
"""

import sys
from pathlib import Path

import chicago95ui

WHITE, BLACK = "#ffffff", "#000000"


def check_mark(colour):
    """Windows' check mark, a short and a long stroke, as two diagonal bands of gradient on the 13-pixel box."""
    stroke = f"transparent 38%, {colour} 38%, {colour} 62%, transparent 62%"
    return (
        f"linear-gradient(45deg, {stroke}) 3px 5px / 3px 3px no-repeat, "
        f"linear-gradient(135deg, {stroke}) 5px 2px / 6px 6px no-repeat"
    )


def down_arrow(colour):
    """The drop-down's black triangle, 8 by 4 pixels, as two half-squares of gradient."""
    return (
        f"linear-gradient(to top right, transparent 50%, {colour} 50%) calc(50% - 2px) 50% / 4px 4px no-repeat, "
        f"linear-gradient(to top left, transparent 50%, {colour} 50%) calc(50% + 2px) 50% / 4px 4px no-repeat"
    )


def radio_dot(colour, field):
    return f"radial-gradient(circle, {colour} 0 2px, {field} 2.5px)"


def raised(lines, outline=0):
    """Windows' raised bevel; an outline first draws a black ring round it, as the default button has."""
    ring_shadow = [f"inset 0 0 0 {outline}px {BLACK}"] if outline else []
    first, second = 1 + outline, 2 + outline
    return ", ".join(
        [
            *ring_shadow,
            f"inset -{first}px -{first}px {lines['dark']}",
            f"inset {first}px {first}px {WHITE}",
            f"inset -{second}px -{second}px {lines['shadow']}",
            f"inset {second}px {second}px {lines['light']}",
        ]
    )


def pressed(lines):
    return f"inset 0 0 0 1px {BLACK}, inset 0 0 0 2px {lines['shadow']}"


def sunken(lines):
    return (
        f"inset 1px 1px {lines['shadow']}, inset -1px -1px {WHITE}, "
        f"inset 2px 2px {lines['dark']}, inset -2px -2px {lines['light']}"
    )


def bevel_lines(scheme, bevel):
    return {name: colour.name() for name, colour in chicago95ui.bevel_colors(scheme["face"], bevel).items()}


def user_chrome(scheme, bevel):
    face = scheme["face"].name()
    lines = bevel_lines(scheme, bevel)
    flat = "appearance: none !important; border: none !important; border-radius: 0 !important;"
    return f"""/* Chicago95: Firefox's controls drawn as the look's (lib/firefox_chrome.py) */
@namespace url("http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul");

button:not(.plain, [type="menu"], [type="menu-button"]) {{
  {flat}
  background: {face} !important;
  color: {BLACK} !important;
  box-shadow: {raised(lines)} !important;
  padding: 3px 6px !important;
  min-height: 23px !important;
}}
button[default="true"]:not(.plain) {{
  box-shadow: {raised(lines, outline=1)} !important;
}}
button:not(.plain):hover:active {{
  box-shadow: {pressed(lines)} !important;
  padding: 4px 5px 2px 7px !important;
}}
button:not(.plain):focus-visible {{
  outline: 1px dotted {BLACK} !important;
  outline-offset: -4px !important;
}}
button:not(.plain)[disabled] {{
  color: {lines["shadow"]} !important;
  text-shadow: 1px 1px {WHITE} !important;
}}

.checkbox-check {{
  {flat}
  width: 13px !important;
  height: 13px !important;
  background: {WHITE} !important;
  box-shadow: {sunken(lines)} !important;
}}
.checkbox-check[checked] {{
  background: {check_mark(BLACK)}, {WHITE} !important;
}}
checkbox[disabled] > .checkbox-check {{
  background: {face} !important;
}}
checkbox[disabled] > .checkbox-check[checked] {{
  background: {check_mark(lines["shadow"])}, {face} !important;
}}

.radio-check {{
  appearance: none !important;
  width: 12px !important;
  height: 12px !important;
  box-sizing: border-box !important;
  border: 1px solid !important;
  border-color: {lines["shadow"]} {WHITE} {WHITE} {lines["shadow"]} !important;
  border-radius: 50% !important;
  background: {WHITE} !important;
  box-shadow: inset 1px 1px {lines["dark"]}, inset -1px -1px {lines["light"]} !important;
}}
.radio-check[selected] {{
  background: {radio_dot(BLACK, WHITE)} !important;
}}
radio[disabled] > .radio-check {{
  background: {face} !important;
}}
radio[disabled] > .radio-check[selected] {{
  background: {radio_dot(lines["shadow"], face)} !important;
}}

.radio-check, .checkbox-check {{
  outline: none !important;
}}
radiogroup:focus-visible radio[focused] .radio-label, checkbox:focus-visible .checkbox-label {{
  outline: 1px dotted {BLACK} !important;
  outline-offset: 0 !important;
}}

menulist {{
  {flat}
  background: {WHITE} !important;
  color: {BLACK} !important;
  box-shadow: {sunken(lines)} !important;
  padding: 2px !important;
}}
dropmarker {{
  {flat}
  min-width: 16px !important;
  align-self: stretch !important;
  background: {down_arrow(BLACK)}, {face} !important;
  box-shadow: {raised(lines)} !important;
}}
menulist[open="true"] dropmarker {{
  box-shadow: inset 0 0 0 1px {lines["shadow"]} !important;
}}
dropmarker > * {{
  visibility: hidden !important;
}}
"""


def main():
    css = user_chrome(chicago95ui.read_scheme(), chicago95ui.look_settings()["bevel"])
    Path(sys.argv[1]).write_text(css)


if __name__ == "__main__":
    main()
