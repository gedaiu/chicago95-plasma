"""Render the installed login components in a Qt process at the reference DPI."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conftest import REPO, load_script  # noqa: E402
from login_theme import render_aero_lock, render_login  # noqa: E402
from PIL import Image  # noqa: E402


def render(manifest, component, state, destination):
    from chicago95ui import make_app

    manifest = Path(manifest)
    output = Path(destination)
    metadata = json.loads(manifest.read_text())
    capture = metadata["session_screens"][component][state]
    look = metadata["look"]
    scale = capture.get("scale", 1)
    with Image.open(manifest.parent / capture["frame"]) as reference:
        size = tuple(round(value / scale) for value in reference.size)
    os.environ["QT_SCALE_FACTOR"] = str(scale)
    app = make_app("Session screen parity")
    if look == "aero":
        account, brand = "Reference", "Windows 7 Professional"
        if component == "lock-screen":
            actual = render_aero_lock(app, output.parent, size, account, brand)
        else:
            actual = render_login(
                app, output.parent, size=size, user=account, users=(account,),
                loginStyle="aero", brandText=brand, failed=capture.get("failed", False),
            )
    elif look == "luna":
        from chicago95lunapreviews import copy_screen_trees

        copy_screen_trees(REPO / "luna", output.parent / "theme/luna", "sddm")
        portrait = REPO / "luna/images/account-pictures/flower.png"
        account = {"name": "ref", "icon": portrait.as_uri()}
        actual = render_login(app, output.parent, size=size, user="ref", users=(account,), loginStyle="luna")
    elif look in ("1995", "1998"):
        actual = render_login(
            app, output.parent, size=size, user="Jim Midnite", users=(), loginStyle="classic",
            loginTitle="Welcome to Windows", loginMessage="Type a user name and password to log on to Windows.",
            titleActive="#000080" if look == "1995" else "#000080,#1084d0",
        )
    else:
        name = "Windows 2000" if look == "2000" else "Windows XP"
        banner = output.parent / "brand-banner.png"
        shutdown = load_script("chicago95-shutdown")
        assert shutdown.render_login_banner({"style": look, "osName": name, "osCompany": "Microsoft"}, banner)
        actual = render_login(
            app, output.parent, size=size, user="ref", users=("ref",), banner=banner,
            loginStyle="2000", loginTitle="Log On to Windows", titleActive="#0A246A,#A6CAF0", scale=round(scale),
            desktopColor="#000000" if look == "2001" else "",
        )
    actual.save(output)


if __name__ == "__main__":
    render(*sys.argv[1:])
