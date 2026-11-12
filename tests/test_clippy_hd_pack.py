"""Exercise every HD clip through the real assistant playback and paint paths."""

import json

import pytest
from clippy_hd_pack import HDPack
from conftest import REPO, load_script
from PIL import Image, ImageChops, ImageDraw
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter

PACK = REPO / "data/clippy/hd-animations"
REQUESTED = {
    "LookLeft",
    "LookRight",
    "LookUp",
    "LookDown",
    "IdleEyeBrowRaise",
    "Wave",
    "Greeting",
    "GoodBye",
    "Thinking",
    "IdleHeadScratch",
    "GestureLeft",
    "GestureRight",
    "GestureUp",
    "GestureDown",
    "Congratulate",
    "Writing",
    "Reading",
    "Sleep",
    "Wake",
}


def test_all_requested_actions_have_distinct_motion_and_complete_frames():
    pack = HDPack(PACK)
    assert REQUESTED <= pack.manifest["animations"].keys()
    for name in REQUESTED:
        sequence = pack.sequences[name]
        assert len(sequence) >= 2
        assert len({bytes(pack.images[index].constBits()) for index, _ in sequence}) > 1, name
        assert 1000 <= sum(duration for _, duration in sequence) <= 10_000, name


def test_four_times_resolution_alpha_and_no_canvas_clipping():
    pack = HDPack(PACK)
    assert (pack.pixel_size.width(), pack.pixel_size.height()) == (496, 372)
    assert (pack.frame_size.width(), pack.frame_size.height()) == (124, 93)
    for filename in {item["file"] for seq in pack.manifest["animations"].values() for item in seq}:
        image = Image.open(PACK / filename)
        alpha = image.getchannel("A")
        low, high = alpha.getextrema()
        assert low == 0 and high >= 250, filename  # Smooth downsampling can round opaque alpha to 254.
        left, top, right, bottom = alpha.getbbox()
        assert 0 < left < right < image.width and 0 < top < bottom < image.height, filename


def test_sleep_wake_endpoints_join_without_a_jump():
    pack = HDPack(PACK)
    assert pack.sequences["Sleep"][-1][0] == pack.sequences["Wake"][0][0]
    assert pack.sequences["Wake"][-1][0] == pack.sequences["Sleep"][0][0]
    for name in REQUESTED - {"Sleep", "Wake"}:
        sequence = pack.sequences[name]
        assert sequence[0][0] == sequence[-1][0], name


def test_gaze_moves_only_eyes_and_pupils_follow_the_requested_direction():
    from clippy_hd import EYES

    base = Image.open(PACK / "blink-0.png").convert("RGBA")
    centers = []
    for index in range(4):
        frame = Image.open(PACK / f"gaze-{index}.png").convert("RGBA")
        channels = ImageChops.difference(base, frame).split()
        pupils = []
        for eye in EYES:
            box = (
                int(8 + eye.left() * 480 / 1448) - 2,
                int(6 + eye.top() * 360 / 1086) - 2,
                int(8 + eye.right() * 480 / 1448) + 2,
                int(6 + eye.bottom() * 360 / 1086) + 2,
            )
            for channel in channels:
                ImageDraw.Draw(channel).rectangle(box, fill=0)
            crop = frame.crop(box)
            dark = [
                (x / crop.width, y / crop.height)
                for y in range(crop.height)
                for x in range(crop.width)
                if max(crop.getpixel((x, y))[:3]) < 70 and crop.getpixel((x, y))[3] > 200
            ]
            assert dark, "Missing pupil"
            pupils.append((sum(p[0] for p in dark) / len(dark), sum(p[1] for p in dark) / len(dark)))
        assert all(channel.getbbox() is None for channel in channels), "Gaze moved body or paper"
        centers.append(pupils)
    for eye in range(2):
        assert centers[0][eye][0] + 0.2 < centers[1][eye][0], "Left/right pupils reversed or stationary"
        assert centers[2][eye][1] + 0.2 < centers[3][eye][1], "Up/down pupils reversed or stationary"


def test_all_runtime_callbacks_and_menu_actions_have_hd_artwork(qt_app, monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    module = load_script("chicago95-clippy")
    pack = HDPack(PACK)
    animations = pack.animations(module.Animation, module.Frame)
    assert set(module.TIP_ANIMATIONS) <= animations.keys()
    assert {"Greeting", "GoodBye", "GetAttention", "Hide", "Show"} <= animations.keys()
    window = module.ClippyWindow(animations, pack, module.SoundPlayer({}, True), qt_app.font())
    try:
        for name in animations:
            finished = []
            window.play(name, on_finished=lambda finished=finished: finished.append(True))
            for _ in range(len(animations[name].frames)):
                canvas = QImage(124, 93, QImage.Format_ARGB32)
                canvas.fill(Qt.transparent)
                painter = QPainter(canvas)
                pack.paint_frame(painter, window.current_frame)
                painter.end()
                assert any(bytes(canvas.constBits())), name
                window.advance_frame()
            assert finished == [True], name
            assert window.playback is None
        menu = window.assistant_menu()
        submenu = next(action.menu() for action in menu.actions() if action.text() == "HD animations")
        actions = {action.text(): action for action in submenu.actions()}
        assert REQUESTED <= actions.keys()
        actions["Writing"].trigger()
        assert window.playback.animation.name == "Writing"
    finally:
        window.frame_timer.stop()
        window.close()


@pytest.mark.parametrize("mutation", ["missing_frame", "bad_duration", "escape"])
def test_broken_pack_fails_with_a_clear_error(tmp_path, mutation):
    manifest = {
        "logical_size": [124, 93],
        "pixel_size": [496, 372],
        "animations": {
            "Test": [{"file": "frame.png", "duration_ms": 100}],
        },
    }
    frame = QImage(496, 372, QImage.Format_ARGB32)
    frame.fill(Qt.transparent)
    frame.save(str(tmp_path / "frame.png"))
    item = manifest["animations"]["Test"][0]
    if mutation == "missing_frame":
        item["file"] = "missing.png"
    elif mutation == "bad_duration":
        item["duration_ms"] = 0
    else:
        item["file"] = "../frame.png"
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        HDPack(tmp_path)
