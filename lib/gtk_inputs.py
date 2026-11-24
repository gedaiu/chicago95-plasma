"""Equivalent native GTK3 and GTK4 input styling."""

from pathlib import Path


def classic_radio_css(assets, look):
    """Give the Classic radio artwork its measured physical size at 120 DPI."""
    if look == "2001":
        size = 14
        outline = "M4 0H10V1H11V2H12V3H13V4H14V10H13V11H12V12H11V13H10V14H4V13H3V12H2V11H1V10H0V4H1V3H2V2H3V1H4Z"
        shadow = (
            "M4 0H10V1H11V2H12V3H10V2H9V1H5V2H3V3H2V5H1V9H2V10H1V9H0V4H1V3H2V2H3V1H4Z"
            " M0 9H1V10H2V11H1V10H0Z M2 11H3V12H2Z"
        )
        dark = "M5 1H9V2H11V3H9V2H5V3H3V5H2V9H3V11H2V9H1V5H2V3H3V2H5Z"
        inset = "M11 3H12V5H13V9H12V11H11V9H12V5H11Z M3 11H5V12H9V11H11V12H9V13H5V12H3Z"
        dot = "M5 4H9V5H10V9H9V10H5V9H4V5H5Z"
    else:
        size = 12
        outline = "M4 0H8V1H10V2H11V4H12V8H11V10H10V11H8V12H4V11H2V10H1V8H0V4H1V2H2V1H4Z"
        shadow = "M4 0H8V1H10V2H8V1H4V2H2V4H1V8H2V10H1V8H0V4H1V2H2V1H4Z"
        dark = "M4 1H8V2H10V3H8V2H4V3H3V4H2V8H3V9H2V8H1V4H2V2H4Z"
        inset = "M9 3H10V4H11V8H10V10H8V9H9V8H10V4H9Z M2 9H4V10H2Z M4 10H8V11H4Z"
        dot = "M5 4H7V5H8V7H7V8H5V7H4V5H5Z"
    face, shade, border = (
        ("#c0c0c0", "#808080", "#000000") if look == "1998" else ("#d4d0c8", "#808080", "#404040")
    )
    assets.mkdir(parents=True, exist_ok=True)
    paths = ((outline, "white"), (shadow, shade), (dark, border), (inset, face))
    styles = []
    for disabled, selected in ((False, False), (False, True), (True, False), (True, True)):
        state = ("-disabled" if disabled else "") + ("-checked" if selected else "")
        path = assets / f"radio{state}.svg"
        rings = ((outline, face), (shadow, shade), (dark, border), (inset, face)) if disabled else paths
        art = (*rings, (dot, shade if disabled else "#000000")) if selected else rings
        shapes = "\n".join(f'  <path d="{shape}" fill="{colour}"/>' for shape, colour in art)
        path.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">\n'
            f'{shapes}\n</svg>\n'
        )
        selector = (":disabled" if disabled else ":not(:disabled)") + (":checked" if selected else ":not(:checked)")
        selector += ":not(:indeterminate)"
        selectors = f"checkbutton > radio{selector}, radiobutton > radio{selector}"
        styles.append(f'{selectors} {{ background-image: url("{path.resolve().as_uri()}"); -gtk-icon-source: none; }}')
    logical = f"{size * 96 / 120:g}px"
    return (
        "checkbutton > radio, radiobutton > radio { background-color: transparent;\n"
        f"  background-size: {logical} {logical}; "
        "  background-repeat: no-repeat; background-position: left top; box-shadow: none; }\n"
        + "\n".join(styles)
        + "\n"
    )


def input_css(theme, version, luna=False):
    theme = Path(theme)
    size = 17 if luna else 16
    face, border, disabled = (
        ("#ECE9D8", "#7F9DB9", "#ACA899") if luna else ("@bg_color", "@border_shade", "@border_shade")
    )

    def image(direction, insensitive=False):
        if luna:
            suffix = "-disabled" if insensitive else ""
            return f'url("{(theme / f"gtk-{version}/assets/stepper-{direction}{suffix}.svg").as_uri()}")'
        suffix = "-insense" if insensitive else ""
        return f'url("{(theme / f"gtk-3.0/scrollbar/stepper-{direction}{suffix}.png").as_uri()}")'

    # Repeated states outrank the base themes' toggle-button, entry, and disabled rules.
    buttons = "combobox button.combo, combobox button, dropdown > button.toggle"
    box_spacing = " border-spacing: 0;" if version == "4.0" else ""
    rules = [
        f"""/* Shared native dropdown/spin-box geometry; GTK retains its native button arrangement. */
combobox, dropdown {{ padding: 0; margin: 0; border: none; background: transparent; }}
{buttons}, spinbutton:not(.vertical) {{
  min-height: {size}px; min-width: 0; padding: 1px; margin: 0;
  border: 1px solid {border}; border-image: none; border-radius: 0;
  background-color: #FFFFFF; background-image: none; box-shadow: none; color: #000000;
  text-shadow: none; outline-width: 0;
}}
combobox button:checked, combobox button:active, dropdown > button.toggle:checked,
dropdown > button.toggle:active {{ background: #FFFFFF; border-color: {border}; box-shadow: none; }}
combobox:disabled button, dropdown:disabled > button.toggle, spinbutton:disabled {{
  background-color: {face}; background-image: none; color: {disabled}; text-shadow: none;
}}
combobox button > box, dropdown > button > box {{ margin: 0; padding: 0;{box_spacing} }}
combobox cellview, dropdown > button > box > stack > row {{
  padding: 0 2px; margin: 0; border: none; background: transparent; box-shadow: none;
  color: inherit; text-shadow: none;
}}
combobox cellview {{ padding: 0; margin-top: -1px; margin-bottom: -1px; }}
dropdown > button > box > stack > row label {{ padding: 0; margin: 0; color: inherit; text-shadow: none; }}
spinbutton:not(.vertical) entry, spinbutton:not(.vertical) > text {{
  min-height: {size}px; min-width: 0; padding: 0 2px; margin: 0;
  border: none; border-image: none; border-radius: 0; background: transparent; box-shadow: none;
  color: inherit; text-shadow: none;
}}
spinbutton:not(.vertical) button,
spinbutton:not(.vertical) button:hover,
spinbutton:not(.vertical) button:active,
spinbutton:not(.vertical) button:disabled {{
  min-width: {size}px; min-height: {size}px; padding: 0; margin: 0;
  border: none; border-image: none; border-radius: 0; box-shadow: none;
  background-color: transparent; background-repeat: no-repeat; background-position: center;
  background-size: {size}px {size}px; -gtk-icon-source: none;
  color: transparent; text-shadow: none; -gtk-icon-shadow: none;
}}
combobox arrow, combobox > box > button > box > arrow, dropdown arrow {{
  min-width: {size}px; min-height: {size}px; padding: 0; margin: 0;
  border: none; background-repeat: no-repeat; background-position: center;
  background-size: {size}px {size}px; -gtk-icon-source: none;
}}
"""
    ]
    for state, insensitive in (("", False), (":disabled", True)):
        rules.append(f"""combobox{state} arrow, combobox{state} > box > button > box > arrow{state},
dropdown{state} arrow {{ background-image: {image("down", insensitive)}; }}
spinbutton:not(.vertical){state} button.up {{ background-image: {image("up", insensitive)}; }}
spinbutton:not(.vertical){state} button.down {{ background-image: {image("down", insensitive)}; }}""")
    if not luna:
        rules.append("entry:not(:disabled) { background-color: white; background-image: none; }")
        rules.append(f"""{buttons}, combobox button:active, combobox button:checked,
dropdown > button.toggle:active, dropdown > button.toggle:checked, spinbutton:not(.vertical) {{
  border: none; padding: 2px;
  box-shadow: inset 1px 1px #808080, inset -1px -1px #FFFFFF,
              inset 2px 2px #000000, inset -2px -2px #DFDFDF;
}}""")
    if luna:
        rules.append("""combobox:hover button, dropdown:hover > button.toggle, spinbutton:not(.vertical):hover {
  border-color: #E59700;
}
combobox:active button, dropdown:active > button.toggle, spinbutton:not(.vertical):active {
  border-color: #6F8DDB;
}""")
    if version == "4.0":
        rules.append("""spinbutton > button > image { -gtk-icon-size: 0; min-width: 0; min-height: 0; opacity: 0; }
combobox arrow, dropdown arrow { -gtk-icon-size: 0; }""")
    return "\n".join(rules) + "\n"
