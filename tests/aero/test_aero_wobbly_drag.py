"""Exercise an actual title-bar drag over a contrasting solid wallpaper in nested KWin."""

import numpy as np
import pytest
from aero_model import reference_session
from plasma_session import missing_programs


@pytest.mark.skipif(bool(missing_programs()), reason=f"needs {', '.join(missing_programs())}")
def test_wobbly_drag_leaves_the_wallpaper_clear_outside_the_bent_frame(desktops, tmp_path):
    settings = [
        ("DECORATION", "aero"),
        ("BACKGROUND_MODE", "color"),
        ("BACKGROUND_COLOR", "#ef1980"),
        ("ANIM_WOBBLY", "yes"),
    ]
    desktop = desktops(
        "luna",
        **reference_session(
            settings=settings,
            windows=[("Drag test", "qt", (160, 150, 559, 449))],
            pointer_steps=[
                "move:310,165",
                "press:left",
                "move:330,165",
                "wait:0.1",
                "capture-drag:330,165,350",
                "release:left",
            ],
        ),
    )
    loaded = desktop.info["loaded_effects"]
    assert "'wobblywindows'" in loaded and "'blur'" in loaded and "'aeroglassblur'" not in loaded
    moving = desktop.info["drag"]
    moving.save(tmp_path / "moving.png")
    desktop.save(tmp_path / "settled.png")
    desktop_pixel = np.asarray(moving)[100, 50]
    pixels = np.asarray(moving, dtype=int)
    # The opaque client is flat-coloured. Follow its left and right edge separately on each row.
    colours, counts = np.unique(np.asarray(desktop)[300], axis=0, return_counts=True)
    counts[np.all(colours == desktop_pixel, axis=1)] = 0
    client_colour = colours[np.argmax(counts)]
    sample = pixels[205:385]
    client = np.max(abs(sample - client_colour), axis=2) < 3
    assert np.min(client.sum(axis=1)) > 200
    left = client.argmax(axis=1)
    right = client.shape[1] - 1 - client[:, ::-1].argmax(axis=1)
    assert max(np.ptp(left), np.ptp(right)) >= 4, "the frame must visibly bend during capture"
    x = np.arange(client.shape[1])
    outside = (x < left[:, None] - 14) | (x > right[:, None] + 14)
    # Shadows darken the wallpaper. A rectangular Aero overlay also changes its hue.
    assert desktop_pixel[0] > 200 and desktop_pixel[1] < 50
    assert np.count_nonzero(outside & (sample[:, :, 1] > desktop_pixel[1] + 16)) < 60


@pytest.mark.skipif(bool(missing_programs()), reason=f"needs {', '.join(missing_programs())}")
def test_moving_glass_blurs_stripes_within_the_wobbling_frame(desktops, tmp_path):
    import os
    from pathlib import Path

    from PIL import Image
    from PySide6.QtCore import QLibraryInfo

    plugin_dir = Path(os.environ.get("AERO_TEST_PLUGIN_DIR", QLibraryInfo.path(QLibraryInfo.PluginsPath)))
    if not (plugin_dir / "kwin/effects/plugins/better_wobblywindows.so").exists():
        pytest.skip("requires Better Wobbly Windows built for the installed KWin")
    wallpaper = tmp_path / "stripes.png"
    stripe = Image.new("RGB", (1024, 768), "#ef1980")
    for x in range(0, stripe.width, 8):
        stripe.paste("#571980", (x, 0, x + 4, stripe.height))
    stripe.save(wallpaper)
    screen = desktops(
        "luna",
        **reference_session(
            settings=[
                ("DECORATION", "aero"),
                ("BACKGROUND_MODE", "image"),
                ("BACKGROUND_IMAGE", str(wallpaper)),
                ("BACKGROUND_FILL", "stretch"),
                ("ANIM_WOBBLY", "blurred"),
            ],
            windows=[("Drag test", "qt", (160, 150, 559, 449))],
            pointer_steps=[
                "move:310,165",
                "press:left",
                "move:330,165",
                "wait:0.1",
                "capture-drag:330,165,350",
                "release:left",
            ],
        ),
    )
    assert "'better_wobblywindows'" in screen.info["loaded_effects"]
    assert "'wobblywindows'" not in screen.info["loaded_effects"]
    moving = screen.info["drag"]
    moving.save(tmp_path / "moving-glass.png")
    pixels = np.asarray(moving, dtype=int)
    colours, counts = np.unique(pixels[300], axis=0, return_counts=True)
    client = np.all(pixels == colours[np.argmax(counts)], axis=2)
    left = client[230:365].argmax(axis=1)
    assert np.ptp(left) >= 4
    xs = left.mean().astype(int) + np.arange(140, 230)
    top = client[:, xs].argmax(axis=0)
    assert np.all((top > 120) & (top < 260))
    inside = pixels[top - 10, xs, 0]
    bare = pixels[90, xs, 0]
    assert np.ptp(bare) >= 140
    assert np.percentile(inside, 95) - np.percentile(inside, 5) < np.ptp(bare) * 0.20
    # Nearby wallpaper beyond the moving glass must retain its sharp stripes.
    outside = left[:, None] - np.arange(20, 52)
    rows = np.arange(230, 365)[:, None]
    assert np.median(np.ptp(pixels[rows, outside, 0], axis=1)) > np.ptp(bare) * 0.85
