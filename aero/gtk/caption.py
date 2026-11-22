"""Generate Aero captions for GTK3 and tinted toolbar-style window controls for GTK4."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aurorae"))
from make_aero_aurorae import AURORAE_STATES, BUTTON_FACES, GAP, palette  # noqa: E402

# The large toolbar button uses a four-stop bevel with its split at 49/50%.
# Tint those same grey levels for each window action.
BLUE_TINT = (50, 24, 0)
RED_TINT = (0, 70, 78)
GLYPHS = {
    "minimize": '<path d="M10 12h10" stroke-width="2"/>',
    "maximize": '<path d="M8.5 5.5h10v8h-10z M9 7.5h9"/>',
    "restore": '<path d="M10 6V4h9v8h-2 M7 7.5h9v7H7z"/>',
    "close": '<path d="m21 6 8 8m0-8-8 8" stroke-width="2.5"/>',
}
CELL_WIDTHS = {
    **palette.BUTTON_WIDTHS,
    "minimize": palette.BUTTON_WIDTHS["minimize"] - 1,
    "maximize": palette.BUTTON_WIDTHS["maximize"] - 1,
}
FACE_HEIGHT = palette.BUTTON_HEIGHT


def write_gtk4_faces(directory):
    directory.mkdir(parents=True, exist_ok=True)
    for kind in BUTTON_FACES:
        width = CELL_WIDTHS["maximize" if kind == "restore" else kind]
        tint = RED_TINT if kind == "close" else BLUE_TINT
        for state, (window, look) in AURORAE_STATES.items():
            strength = {"normal": 1, "hot": 1.3, "pressed": 1.45, "disabled": 0.15}[look]
            if window == "inactive":
                strength *= 0.50
            levels = (247, 232, 220, 207)
            offsets = (0, 49, 50, 100)
            if look == "pressed":
                levels, offsets = (207, 232), (0, 100)
            gradient = []
            for offset, level in zip(offsets, levels, strict=True):
                colour = "".join(f"{max(0, round(level - strength * channel)):02x}" for channel in tint)
                gradient.append(f'<stop offset="{offset}%" stop-color="#{colour}"/>')

            # Extend joined sides outside the viewport so only the two ends are rounded.
            left = 0 if kind == "minimize" else -4
            right = width if kind == "close" else width + 4
            glyph_colour = "#777" if look == "disabled" else "#151515"
            border = "#707070" if look == "normal" else "#586976"
            divider = "" if kind == "minimize" else f'<path d="M.5 1v{FACE_HEIGHT - 2}" stroke="{border}"/>'
            artwork = (
                f'<defs><linearGradient id="face" x2="0" y2="1">{"".join(gradient)}</linearGradient>'
                f'<linearGradient id="rim" x2="0" y2="1"><stop offset=".85" stop-color="{border}"/>'
                '<stop offset="1" stop-color="#808b94"/></linearGradient></defs>'
                f'<rect x="{left + 0.5}" y=".5" width="{right - left - 1}" height="{FACE_HEIGHT - 1}" '
                f'rx="3" fill="url(#face)" stroke="url(#rim)"/>'
                f'<rect x="{left + 1.5}" y="1.5" width="{right - left - 3}" height="{FACE_HEIGHT - 3}" '
                f'rx="2" fill="none" stroke="#fafafa"/>'
                f'{divider}<g fill="none" stroke="{glyph_colour}">{GLYPHS[kind]}</g>'
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
    for kind in BUTTON_FACES:
        button = "maximize" if kind == "restore" else kind
        prefix = "window.maximized " if kind == "restore" else ""
        selectors = [
            prefix + "headerbar " + part + "." + button for part in ("windowcontrols button", "button.titlebutton")
        ]
        width, height = palette.BUTTON_WIDTHS[button], palette.BUTTON_HEIGHT
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
                f'{selector} {{ min-width: {width}px; min-height: {height}px; background-image: url("{sheet}"); '
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
