"""Composite the upstream lock/login art at Windows 7's measured positions, then check the live QML pixels."""

import os
import shutil
from pathlib import Path

import pytest
from conftest import REPO
from PIL import Image, ImageChops, ImageOps, ImageStat
from PySide6.QtCore import QObject, QPointF, Qt, QUrl
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest
from reference import qimage_to_pil
from test_aero_imported_art import CACHE, vector_art


@pytest.fixture(scope="module")
def greeter(tmp_path_factory):
    src = CACHE / "sddm-f51ca15"
    if not (src / "background").is_file():
        pytest.skip("requires the upstream images from aero/fetch-login-art.sh")
    folder = tmp_path_factory.mktemp("greeter")
    art = folder / "aero-art"
    art.mkdir()
    shutil.copy(src / "background", art)
    for name in ("AeroLogin", "AeroLockScreen"):
        shutil.copy(REPO / f"sddm/Chicago95Plasma/{name}.qml", folder)
    for icon in src.glob("*.png"):
        with Image.open(icon) as original:
            (art / icon.with_suffix(".svg").name).write_bytes(vector_art.bitmap_svg(original))
    return folder, src


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
        background = ImageOps.fit(Image.open(src / "background").convert("RGB"), actual.size)
        expected = background.convert("RGBA")

        def paste(name, xy, size):
            img = Image.open(src / f"{name}.png").convert("RGBA").resize(size, Image.Resampling.LANCZOS)
            expected.alpha_composite(img, xy)

        paste("user", (337, 198), (126, 126))
        paste("12223", (305, 166), (190, 190))
        paste("access-button", (34, 538), (38, 28))
        paste("12213", (41, 540), (24, 24))
        if not locked:
            paste("power", (708, 538), (38, 28))
            paste("power-glyph", (715, 540), (24, 24))
        field = view.rootObject().findChild(QObject, "aeroPassword")
        origin = field.mapToScene(QPointF(0, 0)).toPoint()
        x, y = origin.x(), origin.y()
        paste("go", (x + 229, y - 3), (30, 30))
        # Include the button area even on unlock, where it must show the wallpaper.
        for name, box in (
            ("portrait", (305, 166, 495, 356)),
            ("access", (34, 538, 72, 566)),
            ("power", (708, 538, 746, 566)),
            ("submit", (x + 229, y - 3, x + 259, y + 27)),
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
        area = (200, y + 28, 600, y + 50)
        changed = ImageChops.difference(actual.crop(area), failed.crop(area)).convert("L")
        assert sum(changed.histogram()[35:]) > 50, "A rejected credential must paint an error below the field"
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
        spinner.setVisible(False)
        QTest.qWait(25)
        clean = qimage_to_pil(view.grabWindow())
        spinner.setVisible(True)
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
