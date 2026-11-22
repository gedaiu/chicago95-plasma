"""Compare the rendered caption's enter, leave and focus transitions with three 60 Hz SP1 trials."""

import time

import numpy as np
import pytest
from conftest import REPO
from PIL import Image
from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor, QImage
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

THEME = REPO / "aero/aurorae"
REFERENCES = REPO / "tests/references"


def crossing_time(frames, timestamps):
    """Time from first crossing 10% to first crossing 90% along the measured RGB change."""
    frames = np.asarray(frames, dtype=float)
    base = frames[0]
    difference = frames[-1] - base
    assert np.abs(difference).mean() > 4
    progress = ((frames - base) * difference).sum(axis=(1, 2, 3)) / np.square(difference).sum()
    return timestamps[np.flatnonzero(progress >= 0.9)[0]] - timestamps[np.flatnonzero(progress >= 0.1)[0]]


def native_times(action):
    stem = REFERENCES / f"win7-sp1-caption-{action}-motion"
    sheet = np.asarray(Image.open(stem.with_suffix(".png")))
    timestamps = np.loadtxt(stem.with_suffix(".txt"))
    width = sheet.shape[1] // 10
    trials = sheet.reshape(3, 12, 25, 10, width, 3).transpose(0, 1, 3, 2, 4, 5).reshape(3, 120, 25, width, 3)
    return [
        [
            crossing_time(frames[start:end, 5:17, 3:-4], ts[start:end])
            for frames, ts in zip(trials, timestamps, strict=True)
        ]
        for start, end in ((12, 60), (66, 115))
    ]


@pytest.mark.parametrize(
    "action,width", [("close", 50), ("maximize", 27), ("restore", 27), ("minimize", 30), ("focus", 50)]
)
def test_caption_rgb_transition_matches_vm(qt_app, action, width):
    button = "close" if action == "focus" else action
    view = QQuickView()
    view.setColor(QColor("#528cb9"))
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(width, 20)
    view.setInitialProperties(
        {
            "artwork": str(THEME / "theme" / f"{button}.svg"),
            "activeWindow": True,
            "hovered": False,
            "held": False,
            "closeButton": button == "close",
        }
    )
    view.setSource(QUrl.fromLocalFile(str(THEME / "caption/contents/ui/CaptionFace.qml")))
    assert not view.errors()
    view.show()
    QTest.qWait(250)

    def sample():
        img = view.grabWindow().convertToFormat(QImage.Format_RGBA8888)
        data = np.frombuffer(img.constBits(), dtype=np.uint8).reshape(img.height(), img.bytesPerLine() // 4, 4)
        return data[3:15, 3 : width - 4, :3].copy()

    try:
        for entering, original in zip((True, False), native_times(action), strict=True):
            frames = [sample()]
            start = time.monotonic()
            timestamps = [0]
            if action == "focus":
                view.rootObject().setProperty("activeWindow", not entering)
            else:
                view.rootObject().setProperty("hovered", entering)
            while timestamps[-1] < 280:
                QTest.qWait(8)
                frames.append(sample())
                timestamps.append(1000 * (time.monotonic() - start))
            duration = crossing_time(frames, timestamps)
            # One native display interval plus one Qt sample bounds crossing-time quantization.
            if action != "focus":
                assert duration > 0, "hover must show an intermediate frame"
            tolerance = 25 if action != "focus" else 0
            assert min(original) - tolerance <= duration <= max(original) + tolerance, (duration, original)
    finally:
        view.close()
