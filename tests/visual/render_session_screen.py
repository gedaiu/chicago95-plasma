"""Render the installed login components in a Qt process at the reference DPI."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conftest import REPO, load_script  # noqa: E402
from login_theme import login_view, render_aero_lock, render_login  # noqa: E402
from PIL import Image  # noqa: E402
from PySide6.QtCore import QObject, QPointF, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from reference import qimage_to_pil  # noqa: E402


def render_aero_power_menu(app, folder, size, steps, account, brand):
    with login_view(
        app, folder, size=size, user=account, users=(account,),
        loginStyle="aero", brandText=brand, can_sleep=False, can_hibernate=True,
    ) as view:
        root = view.rootObject()
        button = root.findChild(QObject, "aeroPowerOptions")
        menu = root.findChild(QObject, "aeroPowerMenu")
        QTest.mouseClick(view, Qt.LeftButton, pos=button.mapToScene(QPointF(10, 14)).toPoint())
        QTest.qWait(150)
        assert menu.property("opened")
        for _ in range(steps):
            QTest.keyClick(view, Qt.Key_Down)
        QTest.qWait(150)
        background = menu.property("background")
        bounds = background.mapRectToScene(background.boundingRect())
        frame = view.grabWindow()
        box = tuple(round(edge * frame.devicePixelRatio()) for edge in bounds.getCoords())
        return qimage_to_pil(frame).crop(box)


def render(manifest, component, state, destination):
    from chicago95ui import make_app

    manifest = Path(manifest)
    output = Path(destination)
    metadata = json.loads(manifest.read_text())
    capture = metadata["session_screens"][component][state]
    look = metadata["look"]
    scale = capture.get("scale", 1)
    if "screen_size" in capture:
        physical_size = capture["screen_size"]
    else:
        with Image.open(manifest.parent / capture["frame"]) as reference:
            physical_size = reference.size
    size = tuple(round(value / scale) for value in physical_size)
    os.environ["QT_SCALE_FACTOR"] = str(scale)
    app = make_app("Session screen parity")
    if look == "aero":
        account, brand = "Reference", "Windows 7 Professional"
        if component == "lock-screen":
            actual = render_aero_lock(app, output.parent, size, account, brand)
        elif "menu_down" in capture:
            actual = render_aero_power_menu(app, output.parent, size, capture["menu_down"], account, brand)
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
