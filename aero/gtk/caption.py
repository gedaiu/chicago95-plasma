"""GTK client-side captions drawn from the same sprite sheets as the Aero KWin decoration."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aurorae"))
from make_aero_aurorae import AURORAE_STATES, BUTTON_FACES, GAP, face_markup, glyph_markup, paint, palette, stops  # noqa: E402

# The 96-DPI reference places the glyphs independently of the stretched button face.
# Coordinates are the glyph origin inside its cell, including the shared border.
GLYPH_ORIGIN = {"maximize": (4, 2), "restore": (6, 2), "close": (18, 2)}
CELL_WIDTHS = {
    **palette.BUTTON_WIDTHS,
    "minimize": palette.BUTTON_WIDTHS["minimize"] - 1,
    "maximize": palette.BUTTON_WIDTHS["maximize"] - 1,
}
FACE_HEIGHT = 20  # includes the shadow and white highlight below the 18px button


def write_gtk4_faces(directory):
    directory.mkdir(parents=True, exist_ok=True)
    for kind, face_name in BUTTON_FACES.items():
        width = CELL_WIDTHS["maximize" if kind == "restore" else kind]
        for state, (window, look) in AURORAE_STATES.items():
            face = stops.FACES[face_name][window][look]
            source_width, _ = face["size"]
            # Put the inner highlight directly beside the single perimeter stroke.
            # An intervening face-coloured row turns the lower edge into a soft band.
            rows = list(face["rows"])
            rows[-4], rows[-3] = rows[-5], rows[-4]
            defs, shapes = face_markup({**face, "rows": rows}, "f", (0, 0))
            if kind == "minimize":
                # At 96 DPI the visible bar has a one-pixel rim and a 10 by 3 white inset.
                colours = stops.GLYPHS[kind][look]
                rim, alpha = colours["outline"]
                glyph_defs = (
                    f'<linearGradient id="bar" x2="0" y2="1"><stop {paint(*colours["top"])}/>'
                    f'<stop offset="1" {paint(*colours["bottom"])}/></linearGradient>'
                )
                glyph = (
                    f'<rect x="10" y="9" width="12" height="5" rx=".6" fill="{rim}" opacity="{alpha / 255:.3f}"/>'
                    '<rect x="11" y="10" width="10" height="3" fill="url(#bar)"/>'
                )
            else:
                glyph_defs, glyph = glyph_markup(kind, stops.GLYPHS[kind][look], origin=GLYPH_ORIGIN[kind])
            # Use the sprite's glass interior. Draw one divider per join and round
            # only the outside ends so the three hit targets read as one control.
            glass = "#7ba3c5" if window == "active" else "#64ade5"
            edge = len(face["left"])
            left = 0 if kind == "minimize" else -4
            right = width if kind == "close" else width + 4
            outline = f'<rect x="{left + 0.5}" y=".5" width="{right - left - 1}" height="{FACE_HEIGHT - 1}" rx="3"/>'
            divider = "" if kind == "minimize" else f'<path d="M.5 1v{FACE_HEIGHT - 2}" stroke="#455664"/>'
            artwork = (
                f'<defs>{defs}{glyph_defs}'
                '<linearGradient id="rim" x2="0" y2="1">'
                '<stop offset=".82" stop-color="#546777"/><stop offset="1" stop-color="#6d8191"/>'
                f'</linearGradient><clipPath id="cap">{outline}</clipPath></defs>'
                f'<g clip-path="url(#cap)"><rect width="{width}" height="{FACE_HEIGHT}" fill="{glass}"/>'
                f'<svg width="{width}" height="{FACE_HEIGHT}" '
                f'viewBox="{edge} 1 {source_width - 2 * edge} {FACE_HEIGHT}" '
                f'preserveAspectRatio="none">{shapes}</svg>{divider}{glyph}</g>'
                f'<g fill="none" stroke="url(#rim)">{outline}</g>'
            )
            # GTK rasterizes CSS background images at their intrinsic size. Supply both
            # densities so 1x stays pixel-aligned and fractional outputs get a HiDPI source.
            for density, suffix in ((1, ""), (2, "@2x")):
                svg = (
                    f'<svg xmlns="http://www.w3.org/2000/svg" width="{density * width}" '
                    f'height="{density * FACE_HEIGHT}" '
                    f'viewBox="0 0 {width} {FACE_HEIGHT}">{artwork}</svg>'
                )
                (directory / f"{kind}-{state}{suffix}.svg").write_text(svg)


def caption_css(assets, gtk4_directory=None):
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
headerbar windowcontrols button, headerbar button.titlebutton {
  padding: 0; margin: 0; border: none; border-radius: 0;
  background-color: transparent; background-repeat: no-repeat; box-shadow: none;
  min-height: 18px;
}
headerbar windowcontrols button > image, headerbar button.titlebutton > image {
  opacity: 0; padding: 0; margin: 0;
}
"""
    ]
    if gtk4_directory is not None:
        rules.append("""
headerbar windowcontrols { border-spacing: 0; }
""")
    for kind, face in BUTTON_FACES.items():
        button = "maximize" if kind == "restore" else kind
        prefix = "window.maximized " if kind == "restore" else ""
        selectors = [
            prefix + "headerbar " + part + "." + button for part in ("windowcontrols button", "button.titlebutton")
        ]
        width, height = stops.FACES[face]["active"]["normal"]["size"]
        stride = width + GAP
        sheet = (assets / f"{kind}.svg").as_uri()
        for index, (state, (window, look)) in enumerate(AURORAE_STATES.items()):
            suffix = (":backdrop" if window == "inactive" else "") + {
                "normal": "",
                "hot": ":hover",
                "pressed": ":active",
                "disabled": ":disabled",
            }[look]
            selector = ", ".join(s + suffix for s in selectors)
            if gtk4_directory is not None:
                cell_width = CELL_WIDTHS[button]
                graphic = (gtk4_directory / f"{kind}-{state}.svg").as_uri()
                hidpi = (gtk4_directory / f"{kind}-{state}@2x.svg").as_uri()
                rules.append(
                    f"{selector} {{ min-width: {cell_width}px; min-height: {FACE_HEIGHT}px; "
                    f'background: -gtk-scaled(url("{graphic}"), url("{hidpi}")) center / '
                    f"{cell_width}px {FACE_HEIGHT}px no-repeat; }}"
                )
                continue
            rules.append(
                f'{selector} {{ min-width: {width}px; background-image: url("{sheet}"); '
                f"background-size: {len(AURORAE_STATES) * stride}px {height}px; "
                f"background-position: {-index * stride}px center; }}"
            )
    return "\n".join(rules)


if __name__ == "__main__":
    if sys.argv[1] == "--write-buttons":
        write_gtk4_faces(Path(sys.argv[2]))
    else:
        directory = (
            Path.home() / ".local/share/chicago95/gtk4-caption" if os.environ.get("GTK_VERSION") == "4.0" else None
        )
        print(caption_css(Path(sys.argv[1]), directory))
