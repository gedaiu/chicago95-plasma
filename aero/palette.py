"""Aero glass frame colours as plain data, no Qt.

Measured from the Windows 7 aero.msstyles DWM atlas (tests/aero/aero_sprites.py serves it; the bitmaps are not in
the repository). DWMWindow's LEFTFRAME is an 11-pixel row per state, active first: the window's outer dark line, a
white highlight inside it, the transparent glass band DWM tints and blurs, then a light and a dark line against the
client area. Each line is (colour, alpha) per state; sample_column is the LEFTFRAME column it was read from
(tests/aero/test_aero_palette.py). The widths are the screenshots': DWM draws each line one pixel wide.
"""

FRAME_LINES = {
    "outer": {"active": ("#000000", 204), "inactive": ("#000000", 153), "width": 1, "sample_column": 0},
    "highlight": {"active": ("#FFFFFF", 204), "inactive": ("#FEFEFE", 153), "width": 1, "sample_column": 2},
    "client_light": {"active": ("#FEFEFE", 145), "inactive": ("#FEFEFE", 145), "width": 1, "sample_column": 8},
    "client_dark": {"active": ("#181818", 146), "inactive": ("#181818", 146), "width": 1, "sample_column": 9},
}

# The frame's glass: a fill KWin's blur shows the window's surroundings through. Windows 7 mixes its colorization
# colour (Sky, #74B8FC), the blurred background and an afterglow; the frame has no streaks, so it matches their
# average: the median glass along win7dragedge.png's (active, #528BB9) and win7screenres.png's (inactive, #5DABE8)
# right borders over the plain #4395D1 desktop. One background cannot separate opacity from colour, so opacity keeps
# Windows 7's default 49% share for the background (inactive: the least that keeps the colour in range, which lands
# on Sky itself) and the colour is solved to give the median.
REFERENCE_DESKTOP = "#4395D1"
GLASS = {"active": ("#6081A2", 130), "inactive": ("#77C1FF", 128)}

# Geometry measured on win7dragedge.png (active Notepad) and win7screenres.png (inactive window), in pixels at 96 DPI.
BORDER = 8  # sides and bottom: outer, highlight, 4 glass, client light, client dark
TITLE_HEIGHT = 30  # outer, highlight, 26 glass, client light, client dark
TOP_RADIUS, BOTTOM_RADIUS = 6, 5
# The caption buttons, right to left from 6 pixels inside the outer edge, directly under the outer line; neighbours
# share their border pixel (Notepad's at x 412..441..467..516, rows 220..237). DWM draws each 22-row sprite into 18.
BUTTON_HEIGHT = 18
BUTTON_WIDTHS = {"minimize": 30, "maximize": 27, "close": 50}
BUTTON_RIGHT_INSET = 6
# Where a caption button's glyph is centred: its face's content margins (left, right, top, bottom) in the atlas.
BUTTON_CONTENT = {"caption-end": (3, 1, 2, 4), "caption": (2, 3, 2, 4), "close": (1, 2, 2, 4)}

# The superbar, 40 rows: a dark line and a highlight along its top (the composited TaskBand2 BARTOP part and the
# screenshots agree), then glass. TASKBAR_GLASS is win7dragedge.png's rows 730..767 without DWM's streaks (each
# row's median over the empty columns, tests/aero/aero_model.plain_bar), over the plain #4395D1 desktop; the
# generator solves each row's fill at the frame glass' opacity so it shows the same there.
TASKBAR_HEIGHT = 40
TASKBAR_EDGE = (("#000000", 153), ("#FFFFFF", 102))
TASKBAR_GLASS = ["#4580B1"] * 3 + ["#4480B1"] * 10 + ["#4580B1"] * 16 + ["#4581B1"] * 3 + ["#4681B1"] * 6

# Windows 7 darkens the bar behind the orb: black over the glass at opacity, below the bar's top line and highlight
# (rows START_SHADE_TOP..39), within an ellipse anchored at the bar's bottom-left corner whose height is height_scale
# of its width: flat out to flat pixels, fading out by reach, sooner in the upper rows than at the foot. Fitted to
# win7screenres.png outside the orb and the first pinned icon, within four levels, the same in every reference.
START_SHADE = {"opacity": 64, "flat": 56, "reach": 94, "height_scale": 0.55}
START_SHADE_TOP = 2
