"""Gradient stops and ring colours of the Luna taskbar controls, fitted to tests/references.

A stop is (row, colour): the pixel row whose centre carries the colour; between stops the colour is linear. Every
list is
the piecewise-linear fit (dynamic programming, fewest stops that keep each channel within the stated tolerance of every
measured row) of a profile averaged over text-free columns, so compression noise and dithering are smoothed out.

  TASKBAR      xptaskbar-1x.png (lossless), columns x 1200..1399 and 1600..2399 averaged, tolerance 6; the tray box
               (luna/plasmoids/org.chicago95.trayframe TrayBox.qml) is the same fit over the text-free x 2988..2998
  TASK_NORMAL  xprunning.png, the "Control Panel" button x 106..265, rows 3..27 (the pill's rows 0..24); body profile
               averaged over x 236..257, tolerance 5; ring colours: left column x=106, right column x=265 (rows 8..21),
               top and bottom rows over x 236..257
  TASK_PRESSED the same for the "Windows XP Tour" button x 426..585, body averaged over x 540..575
  START        xptaskbar-1x.png, the Start pill x 0..97, fitted jointly (random-perturbation hill climbing on the pixels
               that are neither flag, text nor outline, mean absolute error 5.5 per channel, the text-free x 30..32
                 weighted
               eightfold): the vertical body stops, one white elliptical glow under the top rim and the dark shade that
               grows over x 81..96; rings from row 0 and row 29 over x 40..59, from column x=0 and from the right
                 end, which is a half
               ellipse of radius 6 by 15 (fitted from where each row's pill ends: x 92.5 on row 0, 95.6 on row 5, 97
               on row 15); the halo is column x=97
  BUTTON       xpdisplayprop-1x.png, the Cancel button x 240..312, y 423..443 (the 75x23 control with its one pixel
               outer ring): body averaged over x 244..251 and 300..307, tolerance 3; the border is #003C74
Radii: the task pill's corner pixels cover .6 of the corner pixel (radius 3); the push button's border coverage along
the
top edge is .5, .9, 1 (radius 3.1).
"""

TASKBAR = [
    (0, "#3168D5"),
    (1, "#3888E9"),
    (2, "#4993E6"),
    (3, "#307BE5"),
    (4, "#286ADD"),
    (6, "#2359D6"),
    (21, "#2661DD"),
    (27, "#235BD9"),
    (29, "#1941A5"),
]

TASK_NORMAL = {
    "body": [(0, "#306FD9"), (1, "#4892F7"), (5, "#3A80F3"), (22, "#3980F4"), (23, "#316FE8"), (24, "#2652BC")],
    "ring": {"left": "#3068DE", "right": "#2651AE", "top": "#306FD9", "bottom": "#2652BC"},
    "bevel": {"left": "#619DF5", "right": "#3674EA", "top": "#4892F7", "bottom": "#316FE8"},
}

TASK_PRESSED = {
    "body": [(0, "#1C62D2"), (1, "#123D94"), (3, "#1951B9"), (13, "#1A50B8"), (23, "#2156B7"), (24, "#0C3CAE")],
    "ring": {"left": "#082A70", "right": "#0E3B9F", "top": "#1C62D2", "bottom": "#0C3CAE"},
    "bevel": {"left": "#143E95", "right": "#2156B7", "top": "#123D94", "bottom": "#2156B7"},
}

START = {
    "body": [
        (1, "#51AA51"),
        (2, "#7FC37F"),
        (3, "#71BB72"),
        (5, "#53AC50"),
        (8, "#3EA443"),
        (12, "#429E43"),
        (17, "#42AC42"),
        (22, "#42AC3C"),
        (26, "#3AA33C"),
        (28, "#338B30"),
    ],
    "glow": [
        {"centre": (20.236, 3.916), "radii": (106.835, 8.107), "opacity": 0.325, "pieces": ("center",)},
        {
            "centre": (-11.604, 32.888),
            "radii": (46.287, 26.934),
            "opacity": 0.334,
            "colour": "#000000",
            "pieces": ("left", "center"),
        },
        {"centre": (-0.701, 8.565), "radii": (46.678, 12.543), "opacity": 0.236, "pieces": ("left", "center")},
    ],
    "shade": ((81, 0), (86, 0.121), (91, 0.22), (94, 0.327), (96, 0.471)),
    "ring": {
        "left": "#246A4D",
        "right": [(0, "#3C813C"), (5, "#366E4A"), (9, "#005C27"), (20, "#126540"), (25, "#1D5A5B"), (29, "#256E3B")],
        "top": "#30842A",
        "bottom": "#287D3F",
    },
    "halo": {"colour": "#2672E7", "opacity": 0.9, "width": 1},
}

BUTTON = {
    "body": [(2, "#FFFFFF"), (6, "#F8F8F6"), (15, "#F1F1EC"), (18, "#ECEBE6"), (20, "#D6D0C5")],
}
