"""Aero glass frame colours as plain data, no Qt.

Measured from the Windows 7 aero.msstyles DWM atlas (tests/aero/aero_sprites.py serves it; the bitmaps are not in
the repository). DWMWindow's LEFTFRAME is an 11-pixel row per state, active first: the window's outer dark line, a
white highlight inside it, the transparent glass band DWM tints and blurs, then a light and a dark line against the
client area. Each line is (colour, alpha) per state; sample_column is the LEFTFRAME column it was read from
(tests/aero/test_aero_palette.py).
"""

FRAME_LINES = {
    "outer": {"active": ("#000000", 204), "inactive": ("#000000", 153), "width": 2, "sample_column": 0},
    "highlight": {"active": ("#FFFFFF", 204), "inactive": ("#FEFEFE", 153), "width": 1, "sample_column": 2},
    "client_light": {"active": ("#FEFEFE", 145), "inactive": ("#FEFEFE", 145), "width": 1, "sample_column": 8},
    "client_dark": {"active": ("#181818", 146), "inactive": ("#181818", 146), "width": 2, "sample_column": 9},
}
