from conftest import REPO, run_bash_with_steps
from PIL import Image
from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

ORB = REPO / "aero/plasmoids/org.chicago95.start/contents/ui/aero/WindowsOrb.qml"


def test_orb_displays_the_middle_40_rows_of_each_frame_without_recolouring(qt_app, tmp_path):
    strip = Image.new("RGB", (54, 162))
    strip.putdata([(x * 4, y, (x + y) % 256) for y in range(162) for x in range(54)])
    strip.save(tmp_path / "frames.png")
    view = QQuickView()
    view.setSource(QUrl.fromLocalFile(str(ORB)))
    assert not view.errors()
    item = view.rootObject()
    item.setProperty("source", QUrl.fromLocalFile(str(tmp_path / "frames.png")))
    view.show()
    try:
        for hovered, engaged, frame in [
            (False, False, 0),
            (True, False, 1),
            (True, True, 2),
            (False, True, 2),
            (False, False, 0),
        ]:
            item.setProperty("hovered", hovered)
            item.setProperty("engaged", engaged)
            QTest.qWait(360)
            image = view.grabWindow()
            expected = strip.crop((0, frame * 54 + 7, 54, frame * 54 + 47))
            resized = expected.resize((image.width(), image.height()), Image.Resampling.BILINEAR)
            tolerance = 0 if image.devicePixelRatio() == 1 else 2
            for y in range(image.height()):
                for x in range(image.width()):
                    actual = image.pixelColor(x, y).getRgb()[:3]
                    assert max(abs(a - b) for a, b in zip(actual, resized.getpixel((x, y)), strict=True)) <= tolerance
    finally:
        view.close()


def test_setup_recognises_saved_copies_of_windows_logos_and_keeps_custom_art(tmp_path):
    saved = tmp_path / "start-logo.png"
    saved.write_bytes((REPO / "plasmoids/org.chicago95.start/contents/images/logo-xp-16.png").read_bytes())
    command = 'SETUP_TASKBAR_STYLE=aero SETUP_START_LOGO="$HOME/start-logo.png" panel_start_logo'
    assert run_bash_with_steps(tmp_path, command) == ["xp"]
    saved.write_bytes(b"custom")
    assert run_bash_with_steps(tmp_path, command) == [str(saved)]


def test_vector_orb_stays_centered_in_each_state(qt_app):
    view = QQuickView()
    view.setColor(QColor("#203e55"))
    view.setSource(QUrl.fromLocalFile(str(ORB)))
    item = view.rootObject()
    item.setProperty("source", QUrl.fromLocalFile(str(ORB.with_name("windows7-orb.svg"))))
    view.show()
    samples = []
    try:
        for hovered, held in ((False, False), (True, False), (True, True)):
            item.setProperty("hovered", hovered)
            item.setProperty("engaged", held)
            QTest.qWait(350)
            image = view.grabWindow()
            dpr = image.devicePixelRatio()
            # Upper left pane of the flag stays red, the glass just to its left lights on hover.
            pane = image.pixelColor(round(24 * dpr), round(14 * dpr))
            assert pane.red() > pane.green() > pane.blue()
            samples.append(image.pixelColor(round(15 * dpr), round(15 * dpr)).red())
        assert samples[0] < samples[2] < samples[1]
    finally:
        view.close()


def test_windows_orb_states_match_the_original_strip_at_both_scales(qt_app):
    import hashlib
    import os
    from pathlib import Path

    import pytest
    from PIL import ImageChops, ImageStat
    from test_aero_buttons import rendered

    def contrast(image, scale, y):
        line = image.convert("L").crop((round(10 * scale), y - 1, round(44 * scale), y + 2))
        levels = [ImageStat.Stat(line.crop((0, i, line.width, i + 1))).mean[0] for i in range(3)]
        return levels[1] - (levels[0] + levels[2]) / 2

    source = Path(os.environ.get("AERO_ORB_REFERENCE", Path.home() / ".local/share/chicago95/icons/windows7-orb.png"))
    if not source.is_file():
        pytest.skip("requires the pinned SevenStart sprite as AERO_ORB_REFERENCE")
    assert (
        hashlib.sha256(source.read_bytes()).hexdigest()
        == "356976eb28cc7b8c25263143c1472fc1b47d889f7844b39aa76c695c8d09187c"
    )
    original = Image.open(source).convert("RGBA")
    for scale in (1, 1.5):
        width, height = round(54 * scale), round(40 * scale)
        glass = rendered(
            (REPO / "aero/plasma-style/theme/widgets/startbutton.svg").read_text(), (round(58 * scale), height)
        ).crop((0, 0, width, height))
        panes = rendered(ORB.with_name("windows7-orb.svg").read_text(), (width, 3 * width))
        for state, limit in enumerate((10, 20, 18)):
            offset = state * width + round(7 * scale)
            actual = Image.new("RGBA", glass.size, "#386486")
            actual.alpha_composite(glass)
            actual.alpha_composite(panes.crop((0, offset, width, offset + height)))
            expected = Image.new("RGBA", (54, 40), "#386486")
            expected.alpha_composite(original.crop((0, state * 54 + 7, 54, state * 54 + 47)))
            difference = ImageChops.difference(
                actual.convert("RGB"), expected.resize(actual.size, Image.Resampling.BILINEAR).convert("RGB")
            )
            assert max(ImageStat.Stat(difference).mean) <= limit, (scale, state)
            if state == 2:
                # A single horizontal seam can disappear in the full-orb average. Compare
                # each middle scanline with its neighbours across the width of the glass.
                reference = expected.resize(actual.size, Image.Resampling.BILINEAR)
                for y in range(round(15 * scale), round(26 * scale)):
                    assert abs(contrast(actual, scale, y) - contrast(reference, scale, y)) < 12, (scale, y)


def test_orb_hover_rise_time_matches_sp1(qt_app):
    from time import monotonic

    import numpy as np
    import pytest
    from reference import qimage_to_pil, screenshot

    native = np.asarray(screenshot("win7-sp1-start-orb-hover").convert("RGB"), dtype=float)
    reference = np.stack(np.hsplit(native, native.shape[1] // 7))

    def rise_ms(times, frames):
        delta = np.abs(frames - frames[0]).mean(axis=(1, 2, 3))
        assert delta[-1] > 8
        low, high = [np.flatnonzero(delta >= fraction * delta[-1])[0] for fraction in (0.1, 0.9)]
        return times[high] - times[low]

    view = QQuickView()
    view.setColor(QColor("#386486"))
    view.setSource(QUrl.fromLocalFile(str(ORB)))
    root = view.rootObject()
    root.setProperty("source", QUrl.fromLocalFile(str(ORB.with_name("windows7-orb.svg"))))
    view.show()
    try:
        QTest.qWait(80)
        frames, times = [], []
        start = monotonic()
        while monotonic() - start < 0.55:
            image = qimage_to_pil(view.grabWindow()).convert("RGB").resize((54, 40))
            frames.append(np.asarray(image.crop((7, 12, 14, 24)), dtype=float))
            times.append((monotonic() - start) * 1000)
            if len(frames) == 1:
                root.setProperty("hovered", True)
            QTest.qWait(10)
        # Three displayed frames allow for independent guest and Qt sampling clocks.
        expected = rise_ms(np.arange(len(reference)) * 1000 / 60, reference)
        assert rise_ms(times, np.stack(frames)) == pytest.approx(expected, abs=50)
    finally:
        view.close()
