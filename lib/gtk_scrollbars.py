"""GTK4 scrollbar artwork; end caps are decorative because GTK4 removed steppers."""

from pathlib import Path


def scrollbar_css(theme):
    assets = Path(theme) / "gtk-3.0/scrollbar"

    def asset(name):
        return f'url("{(assets / name).as_uri()}")'

    rules = ['''/* Chicago95 GTK4 scrollbar artwork: end arrows are not interactive buttons. */
scrollbar, scrollbar > range, scrollbar > range > trough {
  padding: 0; margin: 0; border: none; border-radius: 0;
}
scrollbar.horizontal > range > trough { min-height: 16px; }
scrollbar.vertical > range > trough { min-width: 16px; }
''']
    for orientation, first, last, padding, positions in (
        ("horizontal", "left", "right", "0 16px", "left center, right center"),
        ("vertical", "up", "down", "16px 0", "center top, center bottom"),
    ):
        for state, suffix in (("", ""), (":disabled", "-insense")):
            rules.append(f'''scrollbar.{orientation}{state} > range > trough {{
  padding: {padding};
  background-image: {asset(f'stepper-{first}{suffix}.png')}, {asset(f'stepper-{last}{suffix}.png')},
    linear-gradient(45deg, @bg_color 25%, transparent 25%, transparent 75%, @bg_color 75%, @bg_color),
    linear-gradient(45deg, @bg_color 25%, transparent 25%, transparent 75%, @bg_color 75%, @bg_dark);
  background-size: 16px 16px, 16px 16px, 2px 2px, 2px 2px;
  background-repeat: no-repeat, no-repeat, repeat, repeat;
  background-position: {positions}, 0 0, 1px 1px;
}}''')
    selectors = ",\n".join(f"scrollbar > range > trough > slider{state}" for state in
                           ("", ":hover", ":active", ":disabled", ":backdrop"))
    rules.append(f'''{selectors} {{
  min-width: 12px; min-height: 12px; margin: 0; padding: 0;
  border: 2px solid @border_dark;
  border-image: {asset('scrollbar_button.png')}; border-image-slice: 2;
  box-shadow: none; border-radius: 0; background-color: @scrollbar_bg_color; background-image: none;
}}''')
    rules.append("""scrollbar > range > trough > slider:disabled {
  background-image: linear-gradient(45deg, @bg_color 25%, transparent 25%, transparent 75%, @bg_color 75%, @bg_color),
    linear-gradient(45deg, @bg_color 25%, transparent 25%, transparent 75%, @bg_color 75%, @bg_dark);
  background-size: 2px 2px; background-position: 0 0, 1px 1px;
  background-color: @scrollbar_trough_bg_color;
}""")
    return "\n".join(rules) + "\n"
