"""Classic native slider artwork, in palette roles (no raster scaling).

Horizontal lower-point thumb follows win98mouse.png; other orientations follow
the corresponding QWindowsStyle bevel. Disabled interiors use the classic dither.
"""

THUMBS = {
    ("horizontal", "after", False): (
        "WWWWWWWWWWK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        " W......SK ",
        "  W....SK  ",
        "   W..SK   ",
        "    WSK    ",
        "     K     ",
    ),
    ("horizontal", None, False): (
        "WWWWWWWWWWK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        "W........SK",
        " W......SK ",
        "  W....SK  ",
        "   W..SK   ",
        "    WSK    ",
        "     K     ",
    ),
    ("horizontal", None, True): (
        "WWWWWWWWWWK",
        "W........SK",
        "W.W.W.W.WSK",
        "W..W.W.W.SK",
        "W.W.W.W.WSK",
        "W..W.W.W.SK",
        "W.W.W.W.WSK",
        "W..W.W.W.SK",
        "W.W.W.W.WSK",
        "W..W.W.W.SK",
        "W.W.W.W.WSK",
        "W..W.W.W.SK",
        "W.W.W.W.WSK",
        "W..W.W.W.SK",
        "W.W.W.W.WSK",
        "W..W.W.W.SK",
        " WW.W.W.WK ",
        "  WW.W.WK  ",
        "  WWW.WKW  ",
        "    WSK    ",
        "     K     ",
    ),
    ("horizontal", "after", True): (
        "WWWWWWWWWWK",
        "W........SK",
        "W.W.W.W.WSK",
        "W..W.W.W.SK",
        "W.W.W.W.WSK",
        "W..W.W.W.SK",
        "W.W.W.W.WSK",
        "W..W.W.W.SK",
        "W.W.W.W.WSK",
        "W..W.W.W.SK",
        "W.W.W.W.WSK",
        "W..W.W.W.SK",
        "W.W.W.W.WSK",
        "W..W.W.W.SK",
        "W.W.W.W.WSK",
        "W..W.W.W.SK",
        " W..W.W.SK ",
        "  W..W.SK  ",
        "   W..SK   ",
        "    WSK    ",
        "     K     ",
    ),
    ("horizontal", "before", False): (
        "     K     ",
        "    WSK    ",
        "   WL.SK   ",
        "  WL...SK  ",
        " WL.....SK ",
        "WL.......SK",
        "WL.......SK",
        "WL.......SK",
        "WL.......SK",
        "WL.......SK",
        "WL.......SK",
        "WL.......SK",
        "WL.......SK",
        "WL.......SK",
        "WL.......SK",
        "WL.......SK",
        "WL.......SK",
        "WL.......SK",
        "WL.......SK",
        "WSSSSSSSSSK",
        "KKKKKKKKKKK",
    ),
    ("horizontal", "before", True): (
        "     K     ",
        "    WSK    ",
        "   WLWSK   ",
        "  WLWWWSK  ",
        " WLWWWWWSK ",
        "WLWWWWWWWSK",
        "WLWWWWWWWSK",
        "WLWWWWWWWSK",
        "WLWWWWWWWSK",
        "WLWWWWWWWSK",
        "WLWWWWWWWSK",
        "WLWWWWWWWSK",
        "WLWWWWWWWSK",
        "WLWWWWWWWSK",
        "WLWWWWWWWSK",
        "WLWWWWWWWSK",
        "WLWWWWWWWSK",
        "WLWWWWWWWSK",
        "WLWWWWWWWSK",
        "WSSSSSSSSSK",
        "KKKKKKKKKKK",
    ),
    ("vertical", None, False): (
        "WWWWWWWWWWWWWWWWWWWWK",
        "W..................SK",
        "W..................SK",
        "W..................SK",
        "W..................SK",
        "W..................SK",
        "W..................SK",
        "W..................SK",
        "W..................SK",
        "WSSSSSSSSSSSSSSSSSSSK",
        "KKKKKKKKKKKKKKKKKKKKK",
    ),
    ("vertical", None, True): (
        "WWWWWWWWWWWWWWWWWWWWK",
        "W..................SK",
        "W.WWWWWWWWWWWWWWWWWSK",
        "W.WWWWWWWWWWWWWWWWWSK",
        "W.WWWWWWWWWWWWWWWWWSK",
        "W.WWWWWWWWWWWWWWWWWSK",
        "W.WWWWWWWWWWWWWWWWWSK",
        "W.WWWWWWWWWWWWWWWWWSK",
        "W.WWWWWWWWWWWWWWWWWSK",
        "WSSSSSSSSSSSSSSSSSSSK",
        "KKKKKKKKKKKKKKKKKKKKK",
    ),
    ("vertical", "after", False): (
        "WWWWWWWWWWWWWWWW     ",
        "WLLLLLLLLLLLLLLLW    ",
        "WL..............LW   ",
        "WL...............LW  ",
        "WL................LW ",
        "WL.................SK",
        "WL................SK ",
        "WL...............SK  ",
        "WL..............SK   ",
        "WSSSSSSSSSSSSSSSK    ",
        "KKKKKKKKKKKKKKKK     ",
    ),
    ("vertical", "after", True): (
        "WWWWWWWWWWWWWWWW     ",
        "WLLLLLLLLLLLLLLLW    ",
        "WLWWWWWWWWWWWWWWLW   ",
        "WLWWWWWWWWWWWWWWWLW  ",
        "WLWWWWWWWWWWWWWWWWLW ",
        "WLWWWWWWWWWWWWWWWWWSK",
        "WLWWWWWWWWWWWWWWWWSK ",
        "WLWWWWWWWWWWWWWWWSK  ",
        "WLWWWWWWWWWWWWWWSK   ",
        "WSSSSSSSSSSSSSSSK    ",
        "KKKKKKKKKKKKKKKK     ",
    ),
    ("vertical", "before", False): (
        "     WWWWWWWWWWWWWWWK",
        "    WLLLLLLLLLLLLLLSK",
        "   WL..............SK",
        "  WL...............SK",
        " WL................SK",
        "KS.................SK",
        " KS................SK",
        "  KS...............SK",
        "   KS..............SK",
        "    KSSSSSSSSSSSSSSSK",
        "     KKKKKKKKKKKKKKKK",
    ),
    ("vertical", "before", True): (
        "     WWWWWWWWWWWWWWWK",
        "    WLLLLLLLLLLLLLLSK",
        "   WL.W.W.W.W.W.W.WSK",
        "  WL.W.W.W.W.W.W.W.SK",
        " WL.W.W.W.W.W.W.W.WSK",
        "KS.W.W.W.W.W.W.W.W.SK",
        " KS.W.W.W.W.W.W.W.WSK",
        "  KS.W.W.W.W.W.W.W.SK",
        "   KS.W.W.W.W.W.W.WSK",
        "    KSSSSSSSSSSSSSSSK",
        "     KKKKKKKKKKKKKKKK",
    ),
}


def artwork(rows):
    """Hard-stop one-pixel CSS rows retain transparency and live scheme colours."""
    colours = {
        "W": "#FFFFFF",
        ".": "@bg_color",
        "S": "@border_shade",
        "K": "#000000",
        "L": "@border_light",
        " ": "transparent",
    }
    gradients = []
    for row in rows:
        stops = ", ".join(f"{colours[cell]} {x}px, {colours[cell]} {x + 1}px" for x, cell in enumerate(row))
        gradients.append(f"linear-gradient(to right, {stops})")
    return (
        "background-image: "
        + ", ".join(gradients)
        + ";\n"
        + f"background-size: {len(rows[0])}px 1px;\n"
        + "background-position: "
        + ", ".join(f"0 {y}px" for y in range(len(rows)))
        + ";"
    )


def slider_css(version):
    rules = [
        """/* Classic trackbars: native-size thumbs and four-pixel sunken channel. */
scale { padding: 0; margin: 0; border: none; }
scale trough { padding: 0; margin: 0; border: none; border-image: none;
  border-radius: 0; box-shadow: none; outline-width: 0; background-color: transparent; }
scale highlight, scale fill { background: none; border: none; box-shadow: none; min-width: 0; min-height: 0; }
scale slider, scale slider:hover, scale slider:active, scale slider:disabled {
  padding: 0; margin: 0; border: none; border-image: none; border-radius: 0;
  box-shadow: none; background-color: transparent; background-repeat: no-repeat;
}
scale marks, scale mark, scale mark indicator { padding: 0; margin: 0; border: none; }
scale mark indicator { background: #000000; color: #000000; }
scale.horizontal marks.bottom { padding-top: 1px; }
scale.horizontal marks.top { padding-bottom: 1px; }
scale.vertical marks.bottom { padding-left: 1px; }
scale.vertical marks.top { padding-right: 1px; }
"""
    ]
    for orientation in ("horizontal", "vertical"):
        horizontal = orientation == "horizontal"
        direction = "bottom" if horizontal else "right"
        size = "100% 4px" if horizontal else "4px 100%"
        caps = "1px 3px, 1px 3px, 1px 1px" if horizontal else "3px 1px, 3px 1px, 1px 1px"
        positions = (
            "left 7px, right 7px, right 1px top 8px, left 7px"
            if horizontal
            else "7px top, 7px bottom, left 8px bottom 1px, 7px top"
        )
        # GTK3 moves the thumb centre to the trough endpoints. Its painted track
        # extends into the reserved half-thumb space; GTK4 already includes it.
        pad = ("0 5px" if horizontal else "5px 0") if version == "3.0" else "0"
        rules.append(f"""scale.{orientation} {{ padding: {pad}; min-width: 0; min-height: 0; }}
scale.{orientation} trough {{ min-width: 0; min-height: 0; background: none; }}
scale.{orientation} {{ background-origin: border-box;
  background-image: linear-gradient(@border_shade, @border_shade),
    linear-gradient(#FFFFFF, #FFFFFF), linear-gradient(@bg_color, @bg_color),
    linear-gradient(to {direction}, @border_shade 0px, @border_shade 1px,
    #000000 1px, #000000 2px, @bg_color 2px, @bg_color 3px, #FFFFFF 3px, #FFFFFF 4px);
  background-size: {caps}, {size}; background-position: {positions};
  background-repeat: no-repeat;
}}
scale.{orientation} slider {{ min-width: {11 if horizontal else 21}px; min-height: {21 if horizontal else 11}px; }}
scale.{orientation} mark indicator {{ min-width: {1 if horizontal else (1 if version == "3.0" else 2)}px;
  min-height: {(1 if version == "3.0" else 2) if horizontal else 1}px; }}""")
        for point in (None, "before", "after"):
            selector = f"scale.{orientation}"
            if point:
                other = "after" if point == "before" else "before"
                selector += f".marks-{point}:not(.marks-{other})"
            for disabled in (False, True):
                pseudo = ":disabled" if disabled else ":not(:disabled)"
                rules.append(f"{selector} slider{pseudo} {{\n{artwork(THUMBS[orientation, point, disabled])}\n}}")
    if version == "3.0":
        rules.append(
            "scale.horizontal marks.top { padding-bottom: 2px; }scale.vertical marks.top { padding-right: 2px; }"
        )
    rules.append(
        "scale.horizontal.marks-before { background-position: "
        "left 10px, right 10px, right 1px top 11px, left 10px; }"
        "scale.vertical.marks-before { background-position: "
        "10px top, 10px bottom, left 11px bottom 1px, 10px top; }"
    )
    return "\n".join(rules) + "\n"
