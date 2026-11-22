"""Visual regression coverage for the Windows 7 navigation toolbar in Thunar."""

import os
import shutil
from pathlib import Path

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
def thunar_window(tmp_path, aero_icons):
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
    script = tmp_path / "capture"
    script.write_text(
        '#!/bin/sh\nset -eu\ngsettings set org.gnome.desktop.interface icon-theme Windows-7-SVG\nthunar "$HOME" >thunar.log 2>&1 &\n'
        "gdbus wait --session --timeout 15 org.xfce.Thunar\n"
        'for i in 1 2 3 4 5 6; do sleep 1; spectacle -b -n -f -o "$PWD/window.png"\n'
        """python3 -c 'from PIL import Image; import sys; """
        """sys.exit(Image.open("window.png").convert("RGB").getbbox() is None)' && break\ndone\n"""
    )
    run_session(
        tmp_path,
        script,
        {
            "HOME": str(tmp_path),
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
    )
    return Image.open(tmp_path / "window.png").convert("RGB")
