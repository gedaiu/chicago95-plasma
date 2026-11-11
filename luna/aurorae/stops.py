"""Gradient stops of the Luna window decoration, fitted to the luna.msstyles bitmaps (tests/luna/luna_sprites.py).

TITLE            the title columns of the palette (luna/palette.py), which equal the middle column of Window.Caption
                 stretched to the window's size within 12 on every row
SIDE_OVERLAY, INACTIVE_SIDE_OVERLAY
                 one horizontal gradient laid over each side of the title: (distance in pixels from the window's outer
                 edge, colour, opacity); fitted by random-perturbation hill climbing on columns 0..27 of Window.Caption
                 (active and inactive state) stretched to 300x30, outside the transparent stair of the corner
INACTIVE_BORDER_LEFT, INACTIVE_BORDER_BOTTOM
                 the four pixel columns (rows) of Window.FrameLeft and Window.FrameBottom in the inactive state, which
                 the right border shares as in the active frame
BUTTON_ART       the 21x21 caption button face of CaptionButton.bmp (blue: states 0..4 and 7) and CloseButton.bmp (red:
                 states 0..4); each is a ring colour, a vertical face gradient (user space y, colour), radial glows, one
                 linear shade, an optional inner rim (colour, opacity) and the glyph colour, fitted jointly by
                 random-perturbation hill climbing on the 19x19 inside of the ring
"""

TITLE = {
    "active": [
        (0, "#0058EE"),
        (1, "#3F97FF"),
        (2, "#2B90FF"),
        (3, "#0372FF"),
        (6, "#0058E6"),
        (16, "#0055EA"),
        (22, "#026AFE"),
        (27, "#0060FC"),
        (29, "#0043CF"),
    ],
    "inactive": [
        (0, "#688DE0"),
        (1, "#98B2E8"),
        (2, "#9DB9EB"),
        (4, "#7EA2E4"),
        (10, "#7A96DF"),
        (24, "#82A9E9"),
        (29, "#7A93DF"),
    ],
    "maximized": [
        (0, "#3E96FF"),
        (1, "#2C8AFF"),
        (2, "#0370FF"),
        (4, "#015CE9"),
        (11, "#0056E8"),
        (20, "#036CFE"),
        (23, "#0162FA"),
        (25, "#0043CF"),
    ],
}

SIDE_OVERLAY = {
    "left": [(0, "#0005B1", 0.78), (3, "#004ADA", 0.7), (7, "#0053E1", 0.48), (16, "#1687FA", 0.12)],
    "right": [(0, "#00005D", 0.83), (3, "#000ECE", 0.49), (8, "#0000B1", 0.21), (28, "#0000A3", 0.05)],
}
INACTIVE_SIDE_OVERLAY = {
    "left": [(0, "#6064C9", 1.0), (4, "#758FDA", 0.76), (16, "#7CB3E6", 0.06)],
    "right": [(0, "#5D55BF", 1.0), (3, "#6F81D4", 0.87), (8, "#6366CD", 0.22), (28, "#6C1DC6", 0.0)],
}
INACTIVE_BORDER_LEFT = ["#5B68CD", "#7480DC", "#758CDD", "#758CDC"]
INACTIVE_BORDER_BOTTOM = ["#7586DC", "#7587DD", "#6D74CD", "#4F53BC"]

BUTTON_CLOSE_STROKE = (5.46, 15.55, 2.37)
BUTTON_RING_RADIUS = 3.27

BUTTON_ART = {
    "blue": {
        0: {
            "ring": "#FFFFFF",
            "face": [
                (1.5, "#3279FE"),
                (3.5, "#3F77FA"),
                (6.0, "#2B66FA"),
                (11.0, "#1E70FD"),
                (17.0, "#0A66FF"),
                (19.5, "#0E4AC7"),
            ],
            "glows": [
                {
                    "centre": (4.0, 8.1),
                    "radii": (3.2, 6.7),
                    "colour": "#FFE9FF",
                    "stops": [(0, 0.164), (0.35, 0.146), (0.7, 0.118), (1, 0.0)],
                },
                {
                    "centre": (2.4, 2.7),
                    "radii": (14.9, 8.8),
                    "colour": "#FFFFFF",
                    "stops": [(0, 0.44), (0.35, 0.201), (0.7, 0.119), (1, 0.0)],
                },
                {
                    "centre": (7.5, 14.2),
                    "radii": (10.2, 8.2),
                    "colour": "#FFBAE1",
                    "stops": [(0, 0.263), (0.35, 0.183), (0.7, 0.06), (1, 0.0)],
                },
            ],
            "shade": {
                "from": (9.9, -1.1),
                "to": (24.0, -1.4),
                "colour": "#001945",
                "stops": [(0, 0.0), (0.5, 0.0), (1, 0.84)],
            },
            "glyph": "#FFFFFF",
            "rim": ("#00009E", 0.155),
        },
        1: {
            "ring": "#FFFFFF",
            "face": [
                (1.5, "#3C88FF"),
                (3.5, "#4C8EFF"),
                (6.0, "#2E79FF"),
                (11.0, "#2B88FF"),
                (17.0, "#156CFF"),
                (19.5, "#1257CC"),
            ],
            "glows": [
                {
                    "centre": (6.4, 7.8),
                    "radii": (13.3, 26.0),
                    "colour": "#FFD6FF",
                    "stops": [(0, 0.303), (0.35, 0.156), (0.7, 0.0), (1, 0.0)],
                },
                {
                    "centre": (13.2, 15.1),
                    "radii": (8.9, 8.0),
                    "colour": "#53FFFF",
                    "stops": [(0, 0.504), (0.35, 0.308), (0.7, 0.0), (1, 0.0)],
                },
                {
                    "centre": (9.5, 5.8),
                    "radii": (0.5, 13.4),
                    "colour": "#FF91FF",
                    "stops": [(0, 0.0), (0.35, 0.0), (0.7, 0.079), (1, 0.0)],
                },
                {
                    "centre": (3.1, 3.8),
                    "radii": (10.8, 20.5),
                    "colour": "#E4FFFF",
                    "stops": [(0, 0.447), (0.35, 0.0), (0.7, 0.0), (1, 0.0)],
                },
            ],
            "shade": {
                "from": (5.6, 3.2),
                "to": (28.3, 1.9),
                "colour": "#000015",
                "stops": [(0, 0.0), (0.5, 0.0), (1, 1.0)],
            },
            "glyph": "#FFFFFF",
            "rim": ("#0000BD", 0.135),
        },
        2: {
            "ring": "#FFFFFF",
            "face": [
                (1.5, "#002C78"),
                (3.5, "#0044A9"),
                (6.0, "#0041AC"),
                (11.0, "#004AB7"),
                (17.0, "#0052B6"),
                (19.5, "#0651BB"),
            ],
            "glows": [
                {
                    "centre": (1.1, 1.2),
                    "radii": (5.2, 6.0),
                    "colour": "#B2FFFF",
                    "stops": [(0, 1.0), (0.35, 0.0), (0.7, 0.0), (1, 0.0)],
                },
                {
                    "centre": (3.6, 6.3),
                    "radii": (8.4, 33.8),
                    "colour": "#00B0FF",
                    "stops": [(0, 0.315), (0.35, 0.0), (0.7, 0.0), (1, 0.118)],
                },
                {
                    "centre": (10.5, 10.6),
                    "radii": (15.9, 16.2),
                    "colour": "#FFFFFF",
                    "stops": [(0, 0.0), (0.35, 0.0), (0.7, 0.0), (1, 0.609)],
                },
            ],
            "shade": {
                "from": (0.6, 3.9),
                "to": (13.1, 7.5),
                "colour": "#030000",
                "stops": [(0, 0.549), (0.5, 0.046), (1, 0.0)],
            },
            "glyph": "#78A2D8",
            "rim": ("#000000", 0.059),
        },
        3: {
            "ring": "#87AAF2",
            "face": [
                (1.5, "#1963ED"),
                (3.5, "#1A58E4"),
                (6.0, "#0B4DE8"),
                (11.0, "#0E52EE"),
                (17.0, "#095BFA"),
                (19.5, "#0752E3"),
            ],
            "glows": [
                {
                    "centre": (2.9, 4.5),
                    "radii": (18.2, 20.2),
                    "colour": "#DAE1FF",
                    "stops": [(0, 0.296), (0.35, 0.138), (0.7, 0.059), (1, 0.001)],
                }
            ],
            "shade": {
                "from": (6.2, -1.6),
                "to": (26.6, -3.2),
                "colour": "#00005E",
                "stops": [(0, 0.0), (0.5, 0.045), (1, 0.766)],
            },
            "glyph": "#8C9DE7",
            "rim": ("#003CC6", 0.252),
        },
        4: {
            "ring": "#BDC9F0",
            "face": [
                (1.5, "#5485FF"),
                (3.5, "#587EF1"),
                (6.0, "#4871F3"),
                (11.0, "#4A79F1"),
                (17.0, "#427BF4"),
                (19.5, "#4372E0"),
            ],
            "glows": [
                {
                    "centre": (3.7, 4.8),
                    "radii": (14.7, 19.2),
                    "colour": "#DADAE3",
                    "stops": [(0, 0.365), (0.35, 0.182), (0.7, 0.118), (1, 0.064)],
                }
            ],
            "shade": {
                "from": (2.7, -0.8),
                "to": (25.1, -8.1),
                "colour": "#000033",
                "stops": [(0, 0.0), (0.5, 0.086), (1, 0.293)],
            },
            "glyph": "#FFFFFF",
            "rim": ("#000956", 0.078),
        },
        7: {
            "ring": "#9AACE7",
            "face": [
                (1.5, "#6586E5"),
                (3.5, "#687FDD"),
                (6.0, "#5E76DD"),
                (11.0, "#5E79E0"),
                (17.0, "#6086E7"),
                (19.5, "#5E83E0"),
            ],
            "glows": [
                {
                    "centre": (2.9, 5.3),
                    "radii": (16.7, 20.6),
                    "colour": "#D5F2FF",
                    "stops": [(0, 0.208), (0.35, 0.135), (0.7, 0.092), (1, 0.056)],
                }
            ],
            "shade": {
                "from": (5.5, 10.9),
                "to": (24.2, -5.1),
                "colour": "#0000A4",
                "stops": [(0, 0.0), (0.5, 0.048), (1, 0.229)],
            },
            "glyph": "#919FE6",
            "rim": ("#270041", 0.035),
        },
    },
    "red": {
        0: {
            "ring": "#FFFFFF",
            "face": [
                (1.5, "#FF663A"),
                (3.5, "#F96335"),
                (6.0, "#EF5A39"),
                (11.0, "#F64D14"),
                (17.0, "#F14005"),
                (19.5, "#C12D05"),
            ],
            "glows": [
                {
                    "centre": (3.0, 3.4),
                    "radii": (7.2, 11.5),
                    "colour": "#FFFBFF",
                    "stops": [(0, 0.475), (0.35, 0.196), (0.7, 0.09), (1, 0.0)],
                },
                {
                    "centre": (6.9, 13.5),
                    "radii": (14.7, 14.4),
                    "colour": "#CADCFF",
                    "stops": [(0, 0.301), (0.35, 0.113), (0.7, 0.0), (1, 0.0)],
                },
                {
                    "centre": (9.5, 3.2),
                    "radii": (28.9, 5.9),
                    "colour": "#B8D2FF",
                    "stops": [(0, 0.298), (0.35, 0.0), (0.7, 0.0), (1, 0.025)],
                },
            ],
            "shade": {
                "from": (10.2, 3.7),
                "to": (22.4, 2.9),
                "colour": "#480500",
                "stops": [(0, 0.021), (0.5, 0.055), (1, 0.552)],
            },
            "glyph": "#FFFFFF",
            "rim": ("#4E0000", 0.118),
        },
        1: {
            "ring": "#FFFFFF",
            "face": [
                (1.5, "#FF6F5D"),
                (3.5, "#FF6A5B"),
                (6.0, "#FF6352"),
                (11.0, "#FF6453"),
                (17.0, "#FF5240"),
                (19.5, "#D54636"),
            ],
            "glows": [
                {
                    "centre": (3.4, 4.1),
                    "radii": (9.8, 14.5),
                    "colour": "#FFFFF8",
                    "stops": [(0, 0.557), (0.35, 0.209), (0.7, 0.079), (1, 0.0)],
                },
                {
                    "centre": (12.3, 14.7),
                    "radii": (22.0, 15.6),
                    "colour": "#FFFFBD",
                    "stops": [(0, 0.507), (0.35, 0.082), (0.7, 0.0), (1, 0.0)],
                },
                {
                    "centre": (10.7, 3.7),
                    "radii": (21.6, 7.8),
                    "colour": "#FFFFF9",
                    "stops": [(0, 0.226), (0.35, 0.0), (0.7, 0.0), (1, 0.0)],
                },
            ],
            "shade": {
                "from": (6.2, 4.8),
                "to": (27.9, 4.1),
                "colour": "#511700",
                "stops": [(0, 0.0), (0.5, 0.0), (1, 1.0)],
            },
            "glyph": "#FFFFFF",
            "rim": ("#C50000", 0.134),
        },
        2: {
            "ring": "#FFFFFF",
            "face": [
                (1.5, "#7A1C08"),
                (3.5, "#B42F10"),
                (6.0, "#B83117"),
                (11.0, "#C63C1B"),
                (17.0, "#C13C19"),
                (19.5, "#C83C20"),
            ],
            "glows": [
                {
                    "centre": (9.9, 12.9),
                    "radii": (0.5, 0.5),
                    "colour": "#FFFFFF",
                    "stops": [(0, 0.0), (0.35, 0.0), (0.7, 0.0), (1, 0.0)],
                },
                {
                    "centre": (10.6, 10.9),
                    "radii": (15.2, 15.9),
                    "colour": "#FFBBAE",
                    "stops": [(0, 0.0), (0.35, 0.0), (0.7, 0.0), (1, 0.703)],
                },
                {
                    "centre": (3.7, 7.1),
                    "radii": (6.5, 17.0),
                    "colour": "#FF924E",
                    "stops": [(0, 0.24), (0.35, 0.0), (0.7, 0.015), (1, 0.121)],
                },
            ],
            "shade": {
                "from": (-0.4, -6.5),
                "to": (15.3, -3.4),
                "colour": "#000907",
                "stops": [(0, 0.823), (0.5, 0.066), (1, 0.0)],
            },
            "glyph": "#DE9987",
            "rim": ("#000000", 0.053),
        },
        3: {
            "ring": "#7A97E3",
            "face": [
                (1.5, "#7B75BD"),
                (3.5, "#7876C0"),
                (6.0, "#7670B8"),
                (11.0, "#7671B6"),
                (17.0, "#7670B3"),
                (19.5, "#6E6CB2"),
            ],
            "glows": [
                {
                    "centre": (3.3, 4.7),
                    "radii": (14.7, 21.5),
                    "colour": "#78BBFF",
                    "stops": [(0, 0.24), (0.35, 0.134), (0.7, 0.092), (1, 0.051)],
                }
            ],
            "shade": {
                "from": (5.6, 10.7),
                "to": (25.3, -3.9),
                "colour": "#004B00",
                "stops": [(0, 0.0), (0.5, 0.024), (1, 0.088)],
            },
            "glyph": "#9799CD",
            "rim": ("#000052", 0.033),
        },
        4: {
            "ring": "#BDC9F0",
            "face": [
                (1.5, "#C78298"),
                (3.5, "#B97C99"),
                (6.0, "#B8718B"),
                (11.0, "#B6748A"),
                (17.0, "#B67382"),
                (19.5, "#A47184"),
            ],
            "glows": [
                {
                    "centre": (3.7, 4.5),
                    "radii": (13.3, 15.6),
                    "colour": "#ABDEFB",
                    "stops": [(0, 0.332), (0.35, 0.097), (0.7, 0.082), (1, 0.0)],
                }
            ],
            "shade": {
                "from": (2.5, 2.1),
                "to": (20.8, -6.9),
                "colour": "#310017",
                "stops": [(0, 0.0), (0.5, 0.111), (1, 0.25)],
            },
            "glyph": "#FFFFFF",
            "rim": ("#221D43", 0.086),
        },
    },
}
