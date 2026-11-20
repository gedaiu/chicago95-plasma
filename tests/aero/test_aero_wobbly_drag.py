"""Exercise an actual title-bar drag over a contrasting solid wallpaper in nested KWin."""

import numpy as np
import pytest
from aero_model import reference_session
from plasma_session import missing_programs
from reference import screenshot


def windows_glass_edge_width():
    # Where Notepad crosses the Snap outline, sample the same backdrop through and below the frame.
    image = np.asarray(screenshot("win7dragedge"), dtype=float)
    xs = np.arange(473, 510)
    observed = image[575:580, xs, 1].mean(axis=0)
    background = image[640, :, 1]
    offsets = np.arange(-32, 33)

    def fit_error(sigma):
        kernel = np.exp(-0.5 * (offsets / sigma) ** 2)
        blurred = np.convolve(background, kernel / kernel.sum(), mode="same")[xs]
        # Allow for glass tint, transmission, and a local slope in the reflection.
        model = np.column_stack([np.ones(len(xs)), blurred, xs - xs.mean()])
        coefficients = np.linalg.lstsq(model, observed, rcond=None)[0]
        return np.mean((model @ coefficients - observed) ** 2)

    sigma = min(np.arange(0.25, 10, 0.1), key=fit_error)
    return 2.563 * sigma  # distance between the tenth and ninetieth percentiles of a Gaussian


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
    for x in range(0, stripe.width, 80):
        stripe.paste("#571980", (x, 0, x + 40, stripe.height))
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
            tasks_config=[("previewSize", 180)],
            windows=[("Drag test", "qt", (160, 150, 559, 449))],
            pointer_steps=[
                "move:310,165",
                "press:left",
                "move:330,165",
                "wait:0.1",
                "capture-drag:330,165,350",
                "release:left",
                "move:271,748",
                "wait:1.5",
            ],
        ),
    )
    assert "'better_wobblywindows'" in screen.info["loaded_effects"]
    assert "'wobblywindows'" not in screen.info["loaded_effects"]
    moving = screen.info["drag"]
    moving.save(tmp_path / "moving-glass.png")
    screen.save(tmp_path / "stationary-glass.png")
    # Above the fourth task slot, the hosted preview frame must transmit the wallpaper once.
    # In win7peek.png the preview header transmits about 42 percent of a red-channel step.
    desktop = np.asarray(screen, dtype=int)
    bright, dark = 300, 340
    transmission = (desktop[570, bright, 0] - desktop[570, dark, 0]) / (desktop[90, bright, 0] - desktop[90, dark, 0])
    assert 0.37 <= transmission <= 0.47
    reference_width = windows_glass_edge_width()
    for capture in (screen, moving):
        pixels = np.asarray(capture, dtype=int)
        colours, counts = np.unique(pixels[300], axis=0, return_counts=True)
        counts[np.ptp(colours, axis=1) > 50] = 0
        client = np.all(pixels == colours[np.argmax(counts)], axis=2)
        left = client[230:365].argmax(axis=1)
        if capture is moving:
            assert np.ptp(left) >= 4
        frame = np.flatnonzero(client[185])
        xs = np.arange(frame.min() + 110, frame.max() - 100)
        top = client[:, xs].argmax(axis=0)
        assert np.all((top > 120) & (top < 260))
        # The empty taskbar band must also transmit the alternating wallpaper colours.
        panel = pixels[-16, 680:800, 0]
        bright = pixels[90, 680:800, 0] > 160
        assert np.median(panel[bright]) - np.median(panel[~bright]) > 45
        # Sample the glass immediately above the client, clear of the caption and its buttons.
        profile = pixels[top - 6, xs, 0]
        contrast = np.percentile(profile, 95) - np.percentile(profile, 5)
        assert 0.38 < contrast / np.ptp(pixels[90, xs, 0]) < 0.60
        midpoint = (profile.max() + profile.min()) / 2
        widths = []
        for edge in np.flatnonzero(np.diff(profile > midpoint)):
            if edge < 16 or edge + 16 >= len(profile):
                continue
            step = profile[edge - 16 : edge + 17]
            start, end = np.mean(step[:3]), np.mean(step[-3:])
            progress = np.maximum.accumulate((step - start) / (end - start))
            low, high = np.interp([0.1, 0.9], progress, np.arange(len(step)))
            widths.append(high - low)
        # The edge beneath Notepad in win7dragedge.png spreads across about 8–9 pixels.
        assert widths and abs(np.median(widths) - reference_width) < 3.8
        outside = left[:, None] - np.arange(20, 120)
        rows = np.arange(230, 365)[:, None]
        assert np.median(np.ptp(pixels[rows, outside, 0], axis=1)) >= 140
