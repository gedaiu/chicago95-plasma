"""Generate the Windows 7 caption faces and header layout for GTK 3 and GTK 4."""

import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aurorae"))
from make_aero_aurorae import AURORAE_STATES, BUTTON_FACES, button_state, palette  # noqa: E402

CELL_WIDTHS = {
    **palette.BUTTON_WIDTHS,
    "maximize": palette.BUTTON_WIDTHS["maximize"] - 1,
    "restore": 40 / 1.5,
}
FACE_HEIGHT = palette.BUTTON_HEIGHT
GTK4_CAPTION_TOP = 4
MAXIMIZED_CAPTION_TOP = -2 / 3


def write_face(directory, kind, state, width, artwork, large_artwork=None):
    for density, suffix in ((1, ""), (2, "@2x")):
        face = large_artwork if density == 2 and large_artwork else artwork
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{density * width}" '
            f'height="{density * FACE_HEIGHT}" viewBox="0 0 {width} {FACE_HEIGHT}">{face}</svg>'
        )
        (directory / f"{kind}-{state}{suffix}.svg").write_text(svg)


def write_caption_faces(directory, gtk4=False):
    directory.mkdir(parents=True, exist_ok=True)
    for kind in BUTTON_FACES:
        width = CELL_WIDTHS[kind] if gtk4 else palette.BUTTON_WIDTHS["maximize" if kind == "restore" else kind]
        for state, (window, look) in AURORAE_STATES.items():
            defs, shapes = button_state(kind, window, look, "face", cell_width=width)
            # GTK 3's wider Maximize cell uses the existing fractional-scale
            # ring. The narrow GTK 4 cell benefits from the aligned version.
            pixel_density = 2 if gtk4 or kind in ("minimize", "restore") else None
            large_defs, large_shapes = button_state(
                kind, window, look, "face", large=True, cell_width=width, pixel_density=pixel_density,
                crisp_glyph=gtk4 and kind == "close" and look in ("hot", "pressed"),
            )
            write_face(
                directory,
                kind,
                state,
                width,
                f"<defs>{defs}</defs>{shapes}",
                f"<defs>{large_defs}</defs>{large_shapes}",
            )


def caption_css(directory, gtk4):
    rules = [
        """
headerbar, headerbar.titlebar, .titlebar.default-decoration {
  background: linear-gradient(to bottom, #e5f2fc, #c3dbee 48%, #b1cfe5 50%, #dae9f5);
  color: #172836;
  border-bottom: 1px solid #93aabe;
  border-radius: 5px 5px 0 0;
  box-shadow: inset 0 1px rgba(255,255,255,.85);
  min-height: 28px;
}
headerbar:backdrop {
  background: linear-gradient(to bottom, #ecf1f5, #cad5de);
}
window:not(.nautilus-window) headerbar.titlebar:not(:backdrop) {
  background: linear-gradient(to bottom, #2d6ca5, #246399);
  box-shadow: inset 0 1px rgba(255,255,255,.5);
}
window.maximized:not(.nautilus-window) headerbar.titlebar:not(:backdrop) {
  background: linear-gradient(to bottom, #1d4775, #174273);
  color: white;
  border-bottom-color: #142e47;
  box-shadow: none;
}
headerbar windowcontrols button, headerbar button.titlebutton {
  padding: 0; margin: 0; border: none; border-radius: 0;
  background-color: transparent; background-repeat: no-repeat; box-shadow: none;
  background-position: center; background-origin: padding-box; background-clip: padding-box;
  min-height: 18px;
}
headerbar windowcontrols button:disabled, headerbar button.titlebutton:disabled {
  background-color: transparent; background-repeat: no-repeat;
  background-position: center; background-origin: padding-box; background-clip: padding-box;
  border: none; border-radius: 0; box-shadow: none;
}
headerbar windowcontrols button > image, headerbar button.titlebutton > image {
  opacity: 0; padding: 0; margin: 0;
}
"""
    ]
    if gtk4:
        rules.append(f"""
headerbar windowcontrols {{ border-spacing: 0; }}
headerbar windowcontrols button > image {{ min-width: 0; min-height: 0; -gtk-icon-size: 1px; }}
headerbar windowcontrols button, headerbar windowcontrols button:disabled {{
  background-position: center {GTK4_CAPTION_TOP}px;
}}
""")
    else:
        rules.append("""
headerbar.titlebar { padding: 0 5px; }
headerbar.titlebar .title, headerbar.titlebar .subtitle { margin: 0; padding: 0; }
headerbar.titlebar .title { font-size: 12px; font-weight: normal; text-shadow: 0 0 3px white; }
headerbar.titlebar .subtitle { font-size: 10px; }
headerbar.titlebar button.titlebutton + button.titlebutton:dir(ltr) { margin-left: -6px; }
headerbar.titlebar button.titlebutton + button.titlebutton:dir(rtl) { margin-right: -6px; }
headerbar.titlebar button.image-button:not(.titlebutton) {
  min-width: 22px; min-height: 22px; margin: 0; padding: 0 2px;
  background: transparent; border: 1px solid transparent; box-shadow: none;
}
headerbar.titlebar button.image-button:not(.titlebutton):hover {
  background: linear-gradient(#f3faff, #ccdfef); border-color: #869caf;
}
headerbar.titlebar button.image-button:not(.titlebutton):active,
headerbar.titlebar button.image-button:not(.titlebutton):checked {
  background: #bed5e8; border-color: #718da4;
}
headerbar.titlebar button.image-button:not(.titlebutton) image { -gtk-icon-style: symbolic; }
headerbar button.titlebutton { margin-bottom: 12px;
  transition: background-image 160ms linear, box-shadow 160ms linear; }
headerbar button.titlebutton.close { transition-duration: 176ms; }
headerbar button.titlebutton:hover { transition-duration: 80ms; box-shadow: 0 1px 4px #60d2ff; }
headerbar button.titlebutton.close:hover { transition-duration: 40ms; box-shadow: 0 1px 4px #ff805e; }
headerbar button.titlebutton:active, headerbar button.titlebutton:disabled {
  transition-duration: 0ms; box-shadow: none;
}
""")
    rules.append(f"""
window.maximized:not(.nautilus-window) headerbar windowcontrols button,
window.maximized:not(.nautilus-window) headerbar button.titlebutton {{
  background-position: center {MAXIMIZED_CAPTION_TOP:.6f}px;
}}
""")
    if gtk4:
        rules.append(f"""
window.maximized:not(.nautilus-window) headerbar windowcontrols button.maximize,
window.maximized:not(.nautilus-window) headerbar button.titlebutton.maximize {{
  background-position: right {MAXIMIZED_CAPTION_TOP:.6f}px;
}}
""")
    for kind in BUTTON_FACES:
        button = "maximize" if kind == "restore" else kind
        prefix = "window.maximized " if kind == "restore" else ""
        selectors = [
            prefix + "headerbar " + part + "." + button for part in ("windowcontrols button", "button.titlebutton")
        ]
        width = CELL_WIDTHS[kind] if gtk4 else palette.BUTTON_WIDTHS[button]
        for state, (window, look) in AURORAE_STATES.items():
            suffix = (":backdrop" if window == "inactive" else "") + {
                "normal": "",
                "hot": ":hover",
                "pressed": ":active",
                "disabled": ":disabled",
            }[look]
            selector = ", ".join(s + suffix for s in selectors)
            graphic = (directory / f"{kind}-{state}.svg").as_uri()
            hidpi = (directory / f"{kind}-{state}@2x.svg").as_uri()
            rules.append(
                f"{selector} {{ min-width: {math.floor(width)}px; min-height: {FACE_HEIGHT}px; "
                f'background-image: -gtk-scaled(url("{graphic}"), url("{hidpi}")); '
                f"background-size: {width}px {FACE_HEIGHT}px; }}"
            )
    return "\n".join(rules)


if __name__ == "__main__":
    if sys.argv[1] == "--write-buttons":
        directory = Path(sys.argv[2])
        write_caption_faces(directory, gtk4=True)
        write_caption_faces(directory / "gtk3")
    else:
        directory = Path(sys.argv[1])
        gtk4 = os.environ.get("GTK_VERSION") == "4.0"
        print(caption_css(directory if gtk4 else directory / "gtk3", gtk4))
