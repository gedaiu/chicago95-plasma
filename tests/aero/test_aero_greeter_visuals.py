"""Composite the upstream lock/login art at Windows 7's measured positions, then check the live QML pixels."""

import os
import shutil
from pathlib import Path

import numpy as np
import pytest
from conftest import REPO
from login_theme import render_aero_lock
from PIL import Image, ImageChops, ImageOps, ImageStat
from PySide6.QtCore import QObject, QPointF, Qt, QUrl
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest
from reference import qimage_to_pil
from test_aero_imported_art import CACHE, vector_art
from visual.render_session_screen import render_aero_submit


@pytest.fixture(scope="module")
def greeter(tmp_path_factory):
    src = CACHE / "sddm-f51ca15"
    if not (src / "background").is_file():
        pytest.skip("requires the upstream images from aero/fetch-login-art.sh")
    folder = tmp_path_factory.mktemp("greeter")
    art = folder / "aero-art"
    art.mkdir()
    shutil.copytree(REPO / "sddm/Chicago95Plasma/fonts", folder / "fonts")
    shutil.copy(src / "background", art)
    for name in ("AeroLogin", "AeroLockScreen"):
        shutil.copy(REPO / f"sddm/Chicago95Plasma/{name}.qml", folder)
    for artwork in (REPO / "sddm/Chicago95Plasma").glob("Aero*.svg"):
        shutil.copy(artwork, folder)
    for wallpaper in ("AeroBackground4x3.jpg", "AeroBackground1024x768.jpg"):
        shutil.copy(REPO / "sddm/Chicago95Plasma" / wallpaper, folder)
    for icon in src.glob("*.png"):
        if icon.name == "user.png":
            shutil.copy(icon, art)
            continue
        with Image.open(icon) as original:
            (art / icon.with_suffix(".svg").name).write_bytes(vector_art.bitmap_svg(original))
    return folder, src


@pytest.mark.parametrize("state", ("idle", "hover", "held", "held-outside", "released-outside"))
def test_submit_arrow_matches_the_windows_7_sign_in_states(qt_app, tmp_path, state):
    reference = REPO / "tests/references/themes/win7/sign-in/submit" / f"{state}.png"
    with Image.open(reference) as image:
        expected = np.asarray(image.convert("RGB"), dtype=np.int16)
    frame = render_aero_submit(qt_app, tmp_path, (800, 600), "Reference", "Windows 7", state)
    actual = np.asarray(frame.crop((516, 407, 547, 438)), dtype=np.int16)
    delta = np.abs(actual - expected)
    if state in ("hover", "held"):
        # The VM paints its pointer over the lower-left edge of the circle.
        mask = np.ones(delta.shape[:2], dtype=bool)
        mask[22:, 7:27] = False
        delta = delta[mask]
    assert delta.mean() < 7


@pytest.mark.parametrize("locked", [False, True], ids=["login", "unlock"])
def test_portrait_credentials_power_and_failure_render_in_place(qt_app, greeter, locked, tmp_path):
    folder, src = greeter
    # QML stand-ins cannot authenticate, change sessions or power off the host.
    if locked:
        component = 'AeroLockScreen { userName: "AeroTest"; authenticator: QtObject { signal failed(int kind) }'
    else:
        component = (
            'AeroLogin { lastUser: "AeroTest"; users: ["AeroTest"]; sessions: []; lastSession: 0; '
            "greeter: QtObject { signal loginFailed(); property bool canPowerOff: true; "
            "property bool canReboot: true; property bool canSuspend: true; property bool canHibernate: true }"
        )
    scene = folder / "scene.qml"
    scene.write_text("import QtQuick\n" + component + '\nwidth: 800; height: 600; brandText: "Windows 7" }')
    view = QQuickView()
    view.setSource(QUrl.fromLocalFile(str(scene)))
    assert not view.errors()
    view.show()
    try:
        QTest.qWait(80)
        actual = qimage_to_pil(view.grabWindow())
        background = ImageOps.fit(Image.open(folder / "AeroBackground4x3.jpg").convert("RGB"), actual.size)
        expected = background.convert("RGBA")

        def paste(name, xy, size):
            img = Image.open(src / f"{name}.png").convert("RGBA").resize(size, Image.Resampling.LANCZOS)
            expected.alpha_composite(img, xy)

        portrait_top = 149 if locked else 182
        paste("user", (337, portrait_top + 32), (126, 126))
        paste("12223", (305, portrait_top), (190, 190))
        paste("access-button", (34, 538), (38, 28))
        paste("12213", (41, 540), (24, 24))
        if not locked:
            paste("power", (708, 538), (38, 28))
            paste("power-glyph", (715, 540), (24, 24))
        field = view.rootObject().findChild(QObject, "aeroPassword")
        origin = field.mapToScene(QPointF(0, 0)).toPoint()
        x, y = origin.x(), origin.y()
        arrow_y = y - (2 if locked else 3)
        paste("go", (x + 229, arrow_y), (30, 30))
        # Include the button area even on unlock, where it must show the wallpaper.
        for name, box in (
            ("portrait", (305, portrait_top, 495, portrait_top + 190)),
            ("access", (34, 538, 72, 566)),
            ("power", (708, 538, 746, 566)),
            ("submit", (x + 229, arrow_y, x + 259, arrow_y + 30)),
        ):
            diff = ImageChops.difference(actual.crop(box), expected.convert("RGB").crop(box))
            if max(ImageStat.Stat(diff).mean) > 19:
                actual.save(tmp_path / "actual.png")
                expected.save(tmp_path / "reference.png")
                pytest.fail(f"{name} image mismatch; evidence in {tmp_path}")
        if not locked:
            arrow = view.rootObject().findChild(QObject, "aeroPowerOptions")
            QTest.mouseClick(view, Qt.LeftButton, pos=arrow.mapToScene(QPointF(10, 14)).toPoint())
            QTest.qWait(150)
            menu_diff = ImageChops.difference(actual, qimage_to_pil(view.grabWindow()))
            assert menu_diff.crop((600, 400, 766, 538)).getbbox(), "The opened power menu must paint above the button"
            QTest.keyClick(view, Qt.Key_Escape)
        view.rootObject().property("greeter").loginFailed.emit()
        QTest.qWait(40)
        failed = qimage_to_pil(view.grabWindow())
        confirm = view.rootObject().findChild(QObject, "aeroFailureConfirm")
        assert not field.isVisible() and confirm.hasActiveFocus()
        area = (353, 476, 446, 504)
        changed = ImageChops.difference(actual.crop(area), failed.crop(area)).convert("L")
        assert sum(changed.histogram()[35:]) > 50, "A rejected credential must paint the confirmation button"
        QTest.mouseClick(view, Qt.LeftButton, pos=confirm.mapToScene(QPointF(45, 14)).toPoint())
        assert field.isVisible() and field.hasActiveFocus()
    finally:
        view.close()


def test_welcome_screen_draws_the_status_and_cycles_the_spinner(qt_app, tmp_path, monkeypatch):
    session = tmp_path / "chicago95/session"
    session.mkdir(parents=True)
    original = CACHE / "sddm-f51ca15"
    if not (original / "spinner.png").is_file():
        original = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "chicago95/session"
    if not all((original / name).is_file() for name in ("background", "spinner.png")):
        pytest.skip("requires the Windows 7 session background and spinner from Setup")
    shutil.copy(original / "background", session)
    with Image.open(original / "spinner.png") as image:
        strip = image.convert("RGBA")
    (session / "spinner.svg").write_bytes(vector_art.bitmap_svg(strip))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    view = QQuickView()
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(800, 600)
    view.setInitialProperties({"animated": False})
    view.setSource(QUrl.fromLocalFile(str(REPO / "splash/chicago95.splashscreen/contents/splash/SevenSession.qml")))
    assert not view.errors()
    view.show()
    try:
        root = view.rootObject()
        assert root.property("strip").toLocalFile() == str(session / "spinner.svg")
        assert root.property("statusText") == "Welcome"
        QTest.qWait(50)
        spinner = root.findChild(QObject, "sessionSpinner")
        origin = spinner.mapToScene(QPointF(0, 0))
        x, y = round(origin.x()), round(origin.y())
        background = ImageOps.fit(Image.open(session / "background").convert("RGB"), (800, 600))
        # Keep its slot in the Row while capturing the backdrop beneath the spinner.
        spinner.setOpacity(0)
        QTest.qWait(25)
        clean = qimage_to_pil(view.grabWindow())
        spinner.setOpacity(1)
        for frame in (0, 6, 12, 17):
            root.setProperty("frame", frame)
            QTest.qWait(25)
            actual = qimage_to_pil(view.grabWindow())
            box = (x, y, x + 20, y + 20)
            expected = clean.crop(box).convert("RGBA")
            expected.alpha_composite(strip.crop((frame * 20, 0, frame * 20 + 20, 20)))
            diff = ImageChops.difference(actual.crop(box), expected.convert("RGB"))
            assert max(ImageStat.Stat(diff).mean) < 20
            unpainted = ImageChops.difference(actual.crop(box), clean.crop(box))
            assert sum(ImageStat.Stat(diff).mean) < sum(ImageStat.Stat(unpainted).mean)
        # A visible Welcome label must paint immediately to the right of the spinner.
        label = (x + 28, y - 5, 800 - x, y + 25)
        ink = ImageChops.difference(actual.crop(label), background.crop(label)).convert("L")
        assert sum(ink.histogram()[60:]) > 130
        root.setProperty("animated", True)
        QTest.qWait(180)
        assert root.property("frame") != 17
    finally:
        view.close()


@pytest.mark.parametrize("scale", (1, 1.5))
def test_glass_rim_and_shadow_follow_the_account_frame_artwork(greeter, scale):
    from test_aero_imported_art import render

    folder, src = greeter
    size = (round(190 * scale),) * 2
    frame = render((folder / "AeroPortraitFrame.svg").read_bytes(), size)
    reference = Image.open(src / "12223.png").convert("RGBA").resize(size, Image.Resampling.LANCZOS)
    desktop = Image.new("RGBA", size, "#247eb8")
    actual = Image.alpha_composite(desktop, frame).convert("RGB")
    expected = Image.alpha_composite(desktop, reference).convert("RGB")
    diff = ImageChops.difference(actual, expected)
    # Check the thin rim separately from the unpainted center and the outer shadow.
    for box in ((19, 38, 32, 154), (51, 15, 139, 32)):
        strip = diff.crop(tuple(round(v * scale) for v in box))
        assert max(ImageStat.Stat(strip).mean) < 16


def test_unlock_switch_user_button_clears_input_and_fits_above_branding(qt_app, greeter):
    from PySide6.QtTest import QSignalSpy

    folder, _ = greeter
    scene = folder / "switch.qml"
    scene.write_text(
        'import QtQuick\nAeroLockScreen { width: 640; height: 480; userName: "Demo"; brandText: "Fedora" }'
    )
    view = QQuickView()
    view.setSource(QUrl.fromLocalFile(str(scene)))
    assert not view.errors()
    view.show()
    try:
        root = view.rootObject()
        switch = root.findChild(QObject, "aeroSwitchUser")
        assert not switch.isVisible()
        root.setProperty("canSwitchUser", True)
        QTest.qWait(50)
        assert switch.isVisible()
        position = switch.mapToScene(QPointF(0, 0))
        assert position.y() + switch.height() < view.height() - 57
        screenshot = qimage_to_pil(view.grabWindow())
        box = (round(position.x()), round(position.y()), round(position.x()) + 108, round(position.y()) + 28)
        field = root.findChild(QObject, "aeroPassword")
        field.setProperty("text", "sample")
        signal = QSignalSpy(root.switchUserRequested)
        QTest.mouseClick(view, Qt.LeftButton, pos=switch.mapToScene(QPointF(54, 14)).toPoint())
        assert signal.count() == 1 and field.property("text") == ""
        root.setProperty("canSwitchUser", False)
        QTest.qWait(30)
        diff = ImageChops.difference(screenshot.crop(box), qimage_to_pil(view.grabWindow()).crop(box)).convert("L")
        assert sum(diff.histogram()[25:]) > 500
    finally:
        view.close()


@pytest.mark.parametrize(
    "width,height,reference", [(1024, 768, "win7-sp1-aero-lock"), (800, 600, "win7-sp1-aero-lock-800")]
)
def test_lock_password_bounds_match_sp1(qt_app, tmp_path, width, height, reference, exact_original):
    import numpy as np
    from reference import screenshot

    actual = render_aero_lock(qt_app, tmp_path, (width, height), "Reference", "")
    actual.save(tmp_path / "lock.png")

    def bounds(im):
        # The password prompt occupies the left side. Sample its unprinted right half.
        a = np.asarray(im.convert("RGB"))
        left, top = width // 2 - 132, height // 2 + 70
        ys = np.flatnonzero(a[top : top + 82, left + 140 : left + 212].min(axis=(1, 2)) >= 240) + top
        assert len(ys)
        xs = np.flatnonzero(a[ys[2], left : left + 250].min(axis=1) >= 240) + left
        return xs.min(), ys.min(), xs.max(), ys.max()

    native = screenshot(reference)
    if (width, height) == (1024, 768):
        # Compare the uninterrupted wallpaper above the credential group.
        sky = (0, 0, width, 240)
        delta = np.abs(
            np.asarray(native.convert("RGB").crop(sky), dtype=np.int16)
            - np.asarray(actual.convert("RGB").crop(sky), dtype=np.int16)
        )
        assert delta.mean() < 0.03
    left, top, right, _ = bounds(native)
    assert bounds(actual) == pytest.approx(bounds(native), abs=2)
    # Fixed top edge excludes prompt text and the blinking caret.
    edge = (left + 8, top - 3, right - 8, top + 1)
    exact_original(native.crop(edge), actual.crop(edge))
