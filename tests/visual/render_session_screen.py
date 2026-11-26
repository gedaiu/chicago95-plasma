"""Render the installed login components in a Qt process at the reference DPI."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conftest import REPO, load_script  # noqa: E402
from login_theme import login_view, render_aero_lock, render_classic_lock, render_login  # noqa: E402
from PIL import Image  # noqa: E402
from PySide6.QtCore import QObject, QPointF, Qt, QUrl  # noqa: E402
from PySide6.QtQuick import QQuickView  # noqa: E402
from PySide6.QtTest import QSignalSpy, QTest  # noqa: E402
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


def render_aero_entry(app, folder, size, account, brand, state):
    with login_view(
        app, folder, size=size, user=account, users=(account,), loginStyle="aero", brandText=brand,
    ) as view:
        field = view.rootObject().findChild(QObject, "aeroPassword")
        assert field.hasActiveFocus()
        for key in (Qt.Key_A, Qt.Key_B, Qt.Key_C, Qt.Key_D):
            QTest.keyClick(view, key)
        if state in ("selected", "cleared"):
            QTest.keyClick(view, Qt.Key_A, Qt.ControlModifier)
        if state == "cleared":
            QTest.keyClick(view, Qt.Key_Backspace)
        assert field.property("length") == (0 if state == "cleared" else 4)
        selection = field.property("selectionEnd") - field.property("selectionStart")
        assert selection == (4 if state == "selected" else 0)
        QTest.qWait(100)
        return qimage_to_pil(view.grabWindow())


def render_aero_submit(app, folder, size, account, brand, state):
    with login_view(
        app, folder, size=size, user=account, users=(account,), loginStyle="aero", brandText=brand,
    ) as view:
        go = view.rootObject().findChild(QObject, "aeroSubmit")
        greeter = view.rootContext().contextProperty("sddm")
        attempts = QSignalSpy(greeter.loginAttempted)
        inside = go.mapToScene(QPointF(go.width() / 2, go.height() / 2)).toPoint()
        outside = go.mapToScene(QPointF(go.width() + 40, 0)).toPoint()
        QTest.mouseMove(view, outside)
        if state != "idle":
            QTest.mouseMove(view, inside)
            assert go.property("hovered")
        if state in ("held", "held-outside", "released-outside"):
            QTest.mousePress(view, Qt.LeftButton, pos=inside)
            assert go.property("down")
        if state in ("held-outside", "released-outside"):
            QTest.mouseMove(view, outside)
        if state == "released-outside":
            QTest.mouseRelease(view, Qt.LeftButton, pos=outside)
            assert not go.property("down")
        QTest.qWait(200)
        assert attempts.count() == 0
        return qimage_to_pil(view.grabWindow())


def render_luna_lock(folder, size, portrait):
    from chicago95lunapreviews import copy_screen_trees

    theme = folder / "luna"
    copy_screen_trees(REPO / "luna", theme, "sddm", "lockscreen")
    scene = theme / "lock-preview.qml"
    scene.write_text("""import QtQuick
import "lockscreen"

LunaLockScreen {
    authenticator: QtObject { signal failed(int kind) }
}
""")
    view = QQuickView()
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.setInitialProperties({"userName": "ref", "userPicture": QUrl.fromLocalFile(str(portrait))})
    view.resize(*size)
    view.setSource(QUrl.fromLocalFile(str(scene)))
    assert not view.errors(), [error.toString() for error in view.errors()]
    view.show()
    try:
        QTest.qWait(300)
        return qimage_to_pil(view.grabWindow())
    finally:
        view.close()


def render(manifest, component, state, destination):
    from chicago95ui import look_settings, make_app

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
        account, brand = "Reference", "Windows 7"
        edition, logo = "Professional", "AeroBrandFlag.svg"
        if component == "lock-screen":
            actual = render_aero_lock(app, output.parent, size, account, brand, edition=edition, logo=logo)
        elif "menu_down" in capture:
            actual = render_aero_power_menu(app, output.parent, size, capture["menu_down"], account, brand)
        elif "submit" in capture:
            actual = render_aero_submit(app, output.parent, size, account, brand, capture["submit"])
        elif "entry" in capture:
            actual = render_aero_entry(app, output.parent, size, account, brand, capture["entry"])
        else:
            actual = render_login(
                app, output.parent, size=size, user=account, users=(account,),
                loginStyle="aero", brandText=brand, edition=edition, brandLogo=logo,
                failed=capture.get("failed", False),
            )
    elif look == "luna":
        from chicago95lunapreviews import copy_screen_trees

        if component == "lock-screen":
            portrait = output.parent / "portrait.png"
            with Image.open(manifest.parent / capture["frame"]) as native:
                native.crop(capture["portrait_crop"]).save(portrait)
            actual = render_luna_lock(output.parent, size, portrait)
        else:
            copy_screen_trees(REPO / "luna", output.parent / "theme/luna", "sddm")
            portrait = REPO / "luna/images/account-pictures/flower.png"
            account = {"name": "ref", "icon": portrait.as_uri()}
            actual = render_login(app, output.parent, size=size, user="ref", users=(account,), loginStyle="luna")
    elif look in ("1995", "1998"):
        native = Path.home() / ".local/share/fonts/Chicago95" / f"Windows{look[-2:]}" / "MS-Sans-Serif-96-Regular.ttf"
        actual = render_login(
            app, output.parent, size=size, user="Jim Midnite", users=(), loginStyle="classic",
            loginTitle="Welcome to Windows", loginMessage="Type a user name and password to log on to Windows.",
            titleActive="#000080" if look == "1995" else "#000080,#1084d0",
            loginFont=native.as_uri() if native.is_file() else "",
        )
    else:
        name = "Windows 2000" if look == "2000" else "Windows XP"
        logo = (
            REPO / "sddm/Chicago95Plasma/Windows2000Flag.svg"
            if look == "2000"
            else REPO / "luna/images/windows-xp-flag.svg"
        )
        banner = output.parent / "brand-banner.png"
        shutdown = load_script("chicago95-shutdown")
        branding = {
            **look_settings(output.parent / "branding.rc"),
            "style": look,
            "osName": name,
            "osCompany": "Microsoft",
            "osLogo": str(logo),
        }
        assert shutdown.render_login_banner(
            branding if component == "post-login" else {"style": look, "osName": name, "osCompany": "Microsoft"},
            banner, status=component == "post-login",
        )
        if component == "post-login":
            from PySide6.QtCore import QUrl
            from test_loading_screen_reference import splash_view

            with splash_view(
                app, output.parent / "splash", booting=False, size=size, stage=3,
                logonStyle="2000", desktopColor="#3a6ea5",
            ) as view:
                view.rootObject().setProperty("statusBanner", QUrl.fromLocalFile(str(banner)))
                view.rootObject().setProperty("statusStripPhase", capture["strip_phase"])
                QTest.qWait(100)
                actual = qimage_to_pil(view.grabWindow())
        elif component == "lock-screen":
            from showcase import themed

            with themed(app, look):
                actual = render_classic_lock(
                    output.parent, size, banner, typed=capture.get("entry") == "typed",
                    rejected=capture.get("failed", False), xp_classic=look == "2001",
                )
        else:
            actual = render_login(
                app, output.parent, size=size, user="ref", users=("ref",), banner=banner,
                loginStyle="2000", loginTitle="Log On to Windows", titleActive="#0A246A,#A6CAF0", scale=round(scale),
                desktopColor="#000000" if look == "2001" else "",
            )
    if "bounds" in capture:
        actual = actual.crop(capture["bounds"])
    actual.save(output)


if __name__ == "__main__":
    render(*sys.argv[1:])
