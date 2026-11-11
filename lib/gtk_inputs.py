"""Equivalent native GTK3/GTK4 dropdown and spin-box styling."""

from pathlib import Path


def input_css(theme, version, luna=False):
    theme = Path(theme)
    size = 17 if luna else 16
    face, border, disabled = ("#ECE9D8", "#7F9DB9", "#ACA899") if luna else ("#C0C0C0", "#808080", "#808080")

    def image(direction, insensitive=False):
        if luna:
            suffix = "-disabled" if insensitive else ""
            return f'url("{(theme / f"gtk-{version}/assets/stepper-{direction}{suffix}.svg").as_uri()}")'
        suffix = "-insense" if insensitive else ""
        return f'url("{(theme / f"gtk-3.0/scrollbar/stepper-{direction}{suffix}.png").as_uri()}")'

    # Repeated states outrank the base themes' toggle-button, entry, and disabled rules.
    buttons = "combobox button.combo, combobox button, dropdown > button.toggle"
    rules = [f'''/* Shared native dropdown/spin-box geometry; GTK retains its native button arrangement. */
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
combobox button > box, dropdown > button > box {{ margin: 0; padding: 0; border-spacing: 0; }}
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
''']
    for state, insensitive in (("", False), (":disabled", True)):
        rules.append(f'''combobox{state} arrow, combobox{state} > box > button > box > arrow{state},
dropdown{state} arrow {{ background-image: {image('down', insensitive)}; }}
spinbutton:not(.vertical){state} button.up {{ background-image: {image('up', insensitive)}; }}
spinbutton:not(.vertical){state} button.down {{ background-image: {image('down', insensitive)}; }}''')
    if luna:
        rules.append("""combobox:hover button, dropdown:hover > button.toggle, spinbutton:not(.vertical):hover {
  border-color: #E59700;
}
combobox:active button, dropdown:active > button.toggle, spinbutton:not(.vertical):active {
  border-color: #6F8DDB;
}""")
    if version == "4.0":
        rules.append('''spinbutton > button > image { -gtk-icon-size: 0; min-width: 0; min-height: 0; opacity: 0; }
combobox arrow, dropdown arrow { -gtk-icon-size: 0; }''')
    return "\n".join(rules) + "\n"
