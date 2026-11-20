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
