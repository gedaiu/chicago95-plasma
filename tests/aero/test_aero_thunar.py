"""Visual regression coverage for the Windows 7 navigation toolbar in Thunar."""

import os
import shutil
from pathlib import Path

import numpy as np
import pytest
from conftest import REPO, run_bash_with_steps
from PIL import Image
from plasma_session import run_session
from reference import screenshot


@pytest.fixture
def aero_icons(tmp_path):
    source = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "icons/Windows-7-SVG"
    if not (source / "index.theme").is_file():
        pytest.skip("requires the Windows 7 SVG icon theme from Setup")
    folder = tmp_path / ".local/share/icons"
    folder.mkdir(parents=True)
    (folder / source.name).symlink_to(source)
    return source.name


@pytest.fixture
def thunar_window(tmp_path, aero_icons, request):
    scale = getattr(request, "param", 1)
    if not all(shutil.which(name) for name in ("thunar", "kwin_wayland", "spectacle")):
        pytest.skip("needs Thunar, KWin and Spectacle")
    # Preseed the isolated profile so Setup preserves it and updates navigation in place.
    profile = tmp_path / ".config/xfce4/xfconf/xfce-perchannel-xml/thunar.xml"
    profile.parent.mkdir(parents=True)
    shutil.copyfile(REPO / "config/thunar/thunar.xml", profile)
    (tmp_path / ".themes").mkdir()
    (tmp_path / ".themes/Chicago95Aero").symlink_to(REPO / "aero/gtk/Chicago95Aero")
    run_bash_with_steps(tmp_path, "SETUP_HAS_THUNAR=1 SETUP_WIDGET_STYLE=aero step_explorer")
    (tmp_path / ".config/gtk-3.0/settings.ini").write_text(f"[Settings]\ngtk-icon-theme-name={aero_icons}\n")
    # Put just the client at the top left so the toolbar crop is independent of KWin decorations.
    (tmp_path / ".config/kwinrulesrc").write_text(
        "[General]\nrules=thunar\n[thunar]\nwmclass=thunar\nwmclassmatch=2\n"
        "position=0,0\npositionrule=2\nnoborder=true\nnoborderrule=2\n"
    )
    runtime = tmp_path / "run"
    runtime.mkdir(mode=0o700)
    shutil.copyfile(REPO / "tests/eis_pointer.py", tmp_path / "eis_pointer.py")
    script = tmp_path / "capture"
    script.write_text(
        f"#!/bin/sh\nset -eu\nkscreen-doctor output.Virtual-0.scale.{scale} >/dev/null\n"
        "gsettings set org.gnome.desktop.interface icon-theme Windows-7-SVG\n"
        "thunar /usr/share/icons >thunar.log 2>&1 &\n"
        "gdbus wait --session --timeout 15 org.xfce.Thunar\n"
        'for i in 1 2 3 4 5 6; do sleep 1; spectacle -b -n -f -o "$PWD/window.png"\n'
        """python3 -c 'from PIL import Image; import sys; """
        """sys.exit(Image.open("window.png").convert("RGB").getbbox() is None)' && break\ndone\n"""
        # Go up two breadcrumbs and then back once so both arrows are enabled.
        "python3 eis_pointer.py wait:0.5 move:211,15 click:left wait:0.5 move:153,15 click:left "
        "wait:0.5 move:15,15 click:left move:520,75 wait:0.5\n"
        'spectacle -b -n -f -o "$PWD/history.png"\n'
    )
    run_session(
        tmp_path,
        script,
        {
            "HOME": str(tmp_path),
            "WORK": str(tmp_path),
            "XDG_RUNTIME_DIR": str(runtime),
            "GDK_BACKEND": "wayland",
            "GIO_USE_VFS": "local",
            "GIO_USE_VOLUME_MONITOR": "unix",
            "XDG_SESSION_TYPE": "wayland",
            "PATH": "/usr/bin:/bin",
            "GTK_THEME": "Chicago95Aero",
            "GTK_A11Y": "none",
            "GSETTINGS_BACKEND": "keyfile",
        },
        (1024, 768),
        scale=scale,
    )
    return Image.open(tmp_path / "window.png").convert("RGB")


@pytest.mark.parametrize("thunar_window", [1, 1.5], indirect=True)
def test_thunar_navigation_matches_explorer_band(thunar_window, tmp_path):
    # The Explorer client begins at x=7, y=31. Compare a clear part of the
    # address field and the glass above it, independent of the folder name.
    original = screenshot("win7explorer1").convert("RGB").crop((7, 31, 525, 63))
    scale = thunar_window.width / 1024

    def pixels(image, box, density):
        crop = image.crop(tuple(round(value * density) for value in box))
        return np.asarray(crop, dtype=float)

    for box in ((480, 0, 505, 2), (480, 8, 505, 21)):
        target = pixels(original, box, 1).mean(axis=(0, 1))
        rendered = pixels(thunar_window, box, scale).mean(axis=(0, 1))
        assert np.abs(target - rendered).max() < 14, (target, rendered)
    # The first non-toolbar row starts at 32 logical pixels, also at 150%.
    rows = pixels(thunar_window, (420, 0, 435, 45), scale).mean(axis=1)
    start = round(27 * scale)
    first_white = start + np.flatnonzero(rows[start:].min(axis=1) > 248)[0]
    assert abs(first_white / scale - original.height) <= 2

    field = pixels(thunar_window, (480, 0, 481, 29), scale).mean(axis=1)
    interior = np.flatnonzero(np.abs(field - field[round(15 * scale)]).max(axis=1) < 3)
    centreline = (interior[0] + interior[-1]) / 2
    # Measure the painted bounds of both arrows in both history states.
    with Image.open(tmp_path / "history.png") as active:
        for image, enabled in ((thunar_window, False), (active.convert("RGB"), True)):
            heights, centres = [], []
            for left, right in ((3, 32), (34, 64)):
                button = pixels(image, (left, 0, right, 29), scale)
                glass = np.median(button[: round(2 * scale)], axis=0)
                y, x = np.where(np.abs(button - glass).max(axis=2) > 22)
                assert (button.min(axis=2).max() > 224) == enabled
                assert 18 * scale <= np.ptp(x) + 1 <= 21 * scale
                heights.append(np.ptp(y) + 1)
                centres.append((y.min() + y.max()) / 2)
            assert all(18 * scale <= height <= 21 * scale for height in heights)
            assert abs(heights[0] - heights[1]) <= 1
            assert abs(centres[0] - centres[1]) <= 0.5
            assert all(abs(centre - centreline) <= scale for centre in centres)

    # Explorer repeats this separator after each directory. Thunar opens /usr/share/icons
    # here, so its path includes the root plus three directory buttons.
    native_divider = np.asarray(original.crop((96, 10, 104, 21))).max(axis=2) < 115
    logical = thunar_window.resize((1024, 768), Image.Resampling.LANCZOS) if scale != 1 else thunar_window
    ink = np.asarray(logical).max(axis=2) < 115
    matches = [x for x in range(90, 400) if np.count_nonzero(ink[10:21, x : x + 8] != native_divider) <= 7]
    assert len(matches) == 4
    assert min(np.diff(matches)) > 20

    # Compare the visible drive artwork with the address field's centreline.
    # Its transparent SVG canvas used to hide a three-pixel vertical offset.
    upper, lower = round(7 * scale), round(24 * scale)
    drive = pixels(thunar_window, (94, 7, 116, 24), scale)
    visible = np.abs(drive - field[upper:lower, None]).max(axis=2) > 42
    rows = upper + np.flatnonzero(visible.any(axis=1))
    assert 6 * scale <= np.ptp(rows) + 1 <= 10 * scale
    assert abs((rows[0] + rows[-1]) / 2 - centreline) <= scale
