"""Check the Aero caption as painted by KWin on dark glass."""

import numpy as np
import pytest
from aero_model import reference_session
from plasma_session import missing_programs


@pytest.mark.skipif(bool(missing_programs()), reason=f"needs {', '.join(missing_programs())}")
def test_caption_centres_the_icon_and_illuminates_black_letters(desktops, tmp_path, exact_original):
    desktop = desktops(
        "luna",
        **reference_session(
            settings=[("DECORATION", "aero"), ("BACKGROUND_MODE", "color"), ("BACKGROUND_COLOR", "#101820")],
            windows=[("sample - Thunar", "qt", (160, 150, 559, 449))],
        ),
    )
    from caption_cluster import compare_cluster, native_cluster

    desktop.save(tmp_path / "caption.png")
    scores, group = compare_cluster(desktop.crop((420, 140, 575, 190)), 1)
    group.save(tmp_path / "caption-buttons.png")
    exact_original(native_cluster(1)[0], group)
    assert scores == (1, 1, 1), scores
    pixels = np.asarray(desktop.convert("RGB"), dtype=int)
    caption = pixels[153:177, 160:303]
    icons = caption[:, :27]
    icon_y, icon_x = np.where(icons[:, :, 1] - icons[:, :, 0] > 100)
    ink_y, ink_x = np.where(caption[:, 26:].max(axis=2) < 30)
    assert icon_x.max() - icon_x.min() + 1 == 16
    assert 3 <= 26 + ink_x.min() - icon_x.max() <= 7
    assert abs((icon_y.min() + icon_y.max()) - (ink_y.min() + ink_y.max())) <= 4
    # DWM's halo brightens the underlying glass while retaining its tint.
    glow = caption[:, 26:]
    assert (glow.min(axis=2) > 145).sum() > 50
    assert np.percentile(glow.max(axis=2), 99) < 225
    assert np.median(pixels[156:174, 310:360]) < 100


@pytest.mark.skipif(bool(missing_programs()), reason=f"needs {', '.join(missing_programs())}")
@pytest.mark.parametrize("scale", [1, 1.5])
def test_caption_hover_lights_the_glass_below_the_live_close_button(desktops, tmp_path, scale):
    options = reference_session(windows=[("Caption hover", "qt", (160, 150, 559, 449))])
    normal = desktops("luna", **options, scale=scale)
    hot = desktops("luna", **options, scale=scale, pointer_steps=["move:530,159"])
    neighbour = desktops("luna", **options, scale=scale, pointer_steps=["move:490,159"])
    normal.save(tmp_path / "caption-rest.png")
    hot.save(tmp_path / "caption-hover.png")
    neighbour.save(tmp_path / "caption-neighbour-hover.png")
    for screen in (hot, normal, neighbour):
        errors = [
            line
            for line in screen.info["kwin_log"].splitlines()
            if "/org.chicago95.aero/" in line
            and any(term in line for term in ("Error", "Unable to assign", "Binding loop", "not a type"))
        ]
        assert not errors, errors
    # Locate the darker pixel of each divider. A neighbouring halo may tint
    # the glass behind a seam, while the seam itself still limits that tint.
    y = round(159 * scale)
    for x, other_hover in ((477, hot), (504, neighbour)):
        columns = range(round(x * scale) - 2, round(x * scale) + 3)
        seam = min(columns, key=lambda column: sum(normal.getpixel((column, y))))
        rest = np.asarray(normal.getpixel((seam, y)), dtype=int)
        nearest = np.asarray(other_hover.getpixel((seam, y)), dtype=int)
        assert np.max(np.abs(rest - nearest)) < 20, (scale, x, rest, nearest)
    for hovered, face in ((neighbour, (479, 153, 502, 168)), (hot, (507, 153, 547, 168))):
        box = tuple(round(v * scale) for v in face)
        delta = np.asarray(hovered.crop(box), dtype=int) - np.asarray(normal.crop(box), dtype=int)
        assert np.abs(delta).mean() > 5
    if scale == 1.5:
        return  # The halo profile below uses the 96 DPI recording.
    # The first three rows below the button, against the same rows in the guest.
    from reference import screenshot

    sheet = np.asarray(screenshot("win7-sp1-caption-close-motion"), dtype=int)
    # Ten columns of native frames. Frame 0 is at rest, frame 60 is fully hot.
    native_delta = (sheet[172:175, 17:31] - sheet[22:25, 17:31]).mean(axis=1)
    delta = (np.asarray(hot, dtype=int) - np.asarray(normal, dtype=int))[171:174, 520:534].mean(axis=1)
    assert np.all(delta[:, 0] > 25)
    assert np.max(np.abs(delta[:, 0] / delta[0, 0] - native_delta[:, 0] / native_delta[0, 0])) < 0.15


@pytest.mark.skipif(bool(missing_programs()), reason=f"needs {', '.join(missing_programs())}")
def test_kwin_caption_glyphs_on_a_150_percent_screen(desktops, tmp_path, exact_original):
    from caption_cluster import compare_cluster, native_cluster

    desktop = desktops(
        "luna",
        **reference_session(
            settings=[("DECORATION", "aero"), ("BACKGROUND_MODE", "color"), ("BACKGROUND_COLOR", "#101820")],
            windows=[("High DPI caption", "qt", (160, 150, 559, 449))],
            scale=1.5,
        ),
    )
    desktop.save(tmp_path / "kwin-150.png")
    assert desktop.size == (1536, 1152)
    scores, group = compare_cluster(desktop.crop((625, 210, 860, 286)), 1.5)
    group.save(tmp_path / "caption-buttons.png")
    native, _ = native_cluster(1.5)
    exact_original(native, group)
    assert scores == (1, 1, 1), scores
    # All four grey levels of the Minimize bar should reach the same columns.
    # A half-pixel offset previously produced a visible step along its top.
    assert np.array_equal(np.asarray(group)[17:21, 15:31], np.asarray(native)[17:21, 15:31])


@pytest.mark.skipif(bool(missing_programs()), reason=f"needs {', '.join(missing_programs())}")
def test_clicking_maximize_draws_restore_on_a_150_percent_screen(desktops, tmp_path, exact_original):
    from caption_cluster import compare_cluster, native_cluster
    from PIL import ImageOps

    desktop = desktops(
        "luna",
        **reference_session(
            settings=[("DECORATION", "aero"), ("BACKGROUND_MODE", "color"), ("BACKGROUND_COLOR", "#101820")],
            windows=[("High DPI caption", "qt", (160, 150, 559, 449))],
            scale=1.5,
            pointer_steps=["move:490,159", "click:left", "move:440,300", "wait:0.6"],
        ),
    )
    # Windows clips the first row of a maximized caption against the screen edge.
    corner = desktop.crop((desktop.width - 210, 0, desktop.width, 50))
    scores, group = compare_cluster(ImageOps.expand(corner, border=(0, 1, 0, 0)), 1.5, maximized=True)
    group.save(tmp_path / "maximized-caption.png")
    exact_original(native_cluster(1.5, maximized=True)[0], group)
    assert scores == (1, 1, 1), scores
