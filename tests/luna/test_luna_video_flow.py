"""Actual video frames pin the state layouts; timing is deliberately not fitted."""

from contextlib import contextmanager

import pytest
from conftest import REPO
from PIL import Image, ImageChops, ImageDraw
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest
from reference import qimage_to_pil


@contextmanager
def screen(qt_app, source, properties, size=(1920, 1080)):
    view = QQuickView()
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(*size)
    view.setInitialProperties(properties)
    view.setSource(QUrl.fromLocalFile(str(REPO / "luna/splash" / source)))
    assert not view.errors(), [error.toString() for error in view.errors()]
    view.show()
    QTest.qWait(100)
    yield view, qimage_to_pil(view.grabWindow()).convert("RGB")
    view.close()


def item_named(item, name):
    if item.objectName() == name:
        return item
    for child in item.childItems():
        found = item_named(child, name)
        if found is not None:
            return found
    return None


SCREENS = [
    (
        "LunaWelcome.qml",
        {"userName": "Arnav Thorat"},
        "xp-video-welcome-68.png",
        [(715, 495, 945, 570), (990, 495, 1250, 540), (990, 540, 1055, 560)],
    ),
    ("LunaStatus.qml", {"statusText": "Logging off..."}, "xp-video-logoff-37.png", [(990, 570, 1130, 610)]),
    ("LunaStatus.qml", {}, "xp-video-shutdown-42.png", [(860, 570, 1130, 610)]),
]


@pytest.mark.parametrize("source,properties,reference,masks", SCREENS)
def test_screen_backdrop_and_layout_match_video_frame(qt_app, tmp_path, source, properties, reference, masks):
    expected = Image.open(REPO / "tests/references" / reference).convert("RGB")
    with screen(qt_app, source, properties) as (view, actual):
        actual.save(tmp_path / "actual.png")
        # Text/font and user-avatar differences are explicit; screen geometry,
        # wordmark, blue/orange bands and absence of selection glow are compared.
        for image in (actual, expected):
            draw = ImageDraw.Draw(image)
            for box in masks:
                draw.rectangle(box, fill="black")
        expected.save(tmp_path / "expected-masked.png")
        actual.save(tmp_path / "actual-masked.png")
        diff = ImageChops.difference(actual, expected)
        diff.save(tmp_path / "difference.png")
        worst = ImageChops.lighter(ImageChops.lighter(*diff.split()[:2]), diff.split()[2])
        histogram = worst.histogram()
        assert sum(histogram[13:]) / (1920 * 1080) < 0.025


def test_loading_tile_has_no_selected_background_and_has_dark_status(qt_app):
    expected = Image.open(REPO / "tests/references/xp-video-welcome-68.png").convert("RGB")
    with screen(qt_app, "LunaWelcome.qml", {"userName": "Arnav Thorat"}) as (view, image):
        root = view.rootObject()
        caption = root.findChild(QObject, "welcomeCaption")
        assert caption.property("visible")
        assert caption.property("text") == "welcome"
        assert not root.findChild(QObject, "loginWordmark").property("visible")
        assert abs(caption.x() + caption.width() - 928) <= 1
        frame = item_named(root, "avatarFrame")
        assert (frame.width(), frame.height()) == (52, 52)
        status = item_named(root, "userStatus")
        assert status.property("color").name() == "#083399"
        for point in ((1080, 548), (1150, 550), (1250, 555)):
            assert max(abs(a - b) for a, b in zip(image.getpixel(point), expected.getpixel(point), strict=True)) <= 12


@pytest.mark.parametrize("size", [(800, 600), (1280, 720), (1920, 1080)])
def test_loading_controls_keep_native_dimensions_at_each_resolution(qt_app, size):
    with screen(qt_app, "LunaWelcome.qml", {"userName": "Alex"}, size) as (view, image):
        root = view.rootObject()
        assert root.property("topBandHeight") == 78
        assert root.property("bottomBandTop") == size[1] - 96
        frame = item_named(root, "avatarFrame")
        assert (frame.width(), frame.height()) == (52, 52)


@pytest.mark.parametrize(
    "status,reference",
    [
        ("Logging off...", "xp-video-logoff-37.png"),
        ("Windows is shutting down...", "xp-video-shutdown-42.png"),
    ],
)
def test_status_wordmark_and_caption_match_reference_positions(qt_app, status, reference):
    expected = Image.open(REPO / "tests/references" / reference).convert("RGB")
    with screen(qt_app, "LunaStatus.qml", {"statusText": status}) as (view, actual):
        caption = view.rootObject().findChild(QObject, "screenStatus")
        assert caption.property("text") == status
        assert abs(caption.x() + caption.width() - 1111) <= 1
        # Compare foreground locally: a missing logo must not disappear into the
        # full-screen error budget. Separate lettering from the coloured flag.
        for box, kind in [((985, 532, 1110, 565), "lettering"), ((1040, 460, 1125, 530), "flag")]:
            masks = []
            for image in (actual, expected):
                crop = image.crop(box)
                mask = Image.new("L", crop.size)
                mask.putdata(
                    [
                        255
                        if (
                            min(r, g, b) > 190
                            if kind == "lettering"
                            else (r > 170 and b < 120) or (g > 120 and b < 100)
                        )
                        else 0
                        for r, g, b in crop.get_flattened_data()
                    ]
                )
                masks.append(mask)
            a, b = masks
            assert a.getbbox() is not None
            assert max(abs(x - y) for x, y in zip(a.getbbox(), b.getbbox(), strict=True)) <= 5
            assert 0.65 < sum(a.get_flattened_data()) / sum(b.get_flattened_data()) < 1.5
