"""Reuse Chicago95's bitmap notebook borders in GTK4, including all tab positions."""

import re
from pathlib import Path


def notebook_css(theme):
    source = Path(theme) / "gtk-3.0/gtk-notebooks.css"
    css = source.read_text()
    css = re.sub(r'url\("([^\"]+)"\)', lambda m: f'url("{(source.parent / m[1]).as_uri()}")', css)
    css = re.sub(r"notebook tab\b", "notebook > header > tabs > tab", css)
    css = re.sub(r"notebook tabs\b", "notebook > header > tabs", css)
    # GTK3 only paints the tab outline with keyboard focus; GTK4 paints any outline.
    css = css.replace("outline: 1px dotted @outline_color;", "outline: none;")
    reset = ",\n".join(
        f"notebook > header.{position} > tabs > tab{state}"
        for position in ("top", "bottom", "left", "right")
        for state in ("", ":checked", ":hover")
    )
    reset += " { margin: 0; padding: 1px; outline: none; }\n"
    return reset + """/* Chicago95 GTK4 notebook parity: retain GTK3's original bitmap borders. */
notebook > header > tabs > tab {
  min-width: 0; min-height: 0; margin: 0; padding: 1px;
  border-width: 0; box-shadow: none; background-image: none;
  outline-width: 0;
}
notebook > header > tabs > tab:hover,
notebook > header > tabs > tab:checked { box-shadow: none; }
notebook > header > tabs > tab label { padding: 0; margin: 0; }
notebook > header > tabs > arrow {
  border: none; box-shadow: none; padding: 0; margin: 0;
}
""" + css + """
notebook:focus > header > tabs > tab:checked,
notebook > header > tabs > tab:checked:focus {
  outline: 1px dotted @outline_color; outline-offset: -5px;
}
"""
