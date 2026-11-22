"""Check the Aero caption as painted by KWin on dark glass."""

import numpy as np
import pytest
from aero_model import reference_session
from plasma_session import missing_programs


@pytest.mark.skipif(bool(missing_programs()), reason=f"needs {', '.join(missing_programs())}")
def test_caption_centres_the_icon_and_illuminates_black_letters(desktops, tmp_path):
    desktop = desktops(
        "luna",
        **reference_session(
            settings=[("DECORATION", "aero"), ("BACKGROUND_MODE", "color"), ("BACKGROUND_COLOR", "#101820")],
            windows=[("sample - Thunar", "qt", (160, 150, 559, 449))],
        ),
    )
    desktop.save(tmp_path / "caption.png")
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
def test_caption_hover_lights_the_glass_below_the_live_close_button(desktops):
    options = reference_session(windows=[("Caption hover", "qt", (160, 150, 559, 449))])
    normal = desktops("luna", **options)
    hot = desktops("luna", **options, pointer_steps=["move:530,159"])
    for screen in (hot, normal):
        errors = [
            line
            for line in screen.info["kwin_log"].splitlines()
            if "/org.chicago95.aero/" in line
            and any(term in line for term in ("Error", "Unable to assign", "Binding loop", "not a type"))
        ]
        assert not errors, errors
    # The first three rows below the button, against the same rows in the guest.
    from reference import screenshot

    sheet = np.asarray(screenshot("win7-sp1-caption-close-motion"), dtype=int)
    # Ten columns of native frames. Frame 0 is at rest, frame 60 is fully hot.
    native_delta = (sheet[172:175, 17:31] - sheet[22:25, 17:31]).mean(axis=1)
    delta = (np.asarray(hot, dtype=int) - np.asarray(normal, dtype=int))[171:174, 520:534].mean(axis=1)
    assert np.all(delta[:, 0] > 25)
    assert np.max(np.abs(delta[:, 0] / delta[0, 0] - native_delta[:, 0] / native_delta[0, 0])) < 0.15
