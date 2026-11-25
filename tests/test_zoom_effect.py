"""The KWin zoom effect for title-bar motion to the taskbar and window resizing on maximize.

The effect's geometry is pure functions; its wiring is checked against stub KWin globals that record animate()."""

import json

import pytest
from conftest import REPO
from PySide6.QtQml import QJSEngine

EFFECT = REPO / "kwin-effects/chicago95zoom/contents/code/main.js"
FRAME = {"x": 100, "y": 50, "width": 400, "height": 300}
ICON = {"x": 200, "y": 452, "width": 160, "height": 22}
STUBS = """
var handlers = {}, started = [], config = {};
function signal(name) { return { connect: function (handler) { handlers[name] = handler; } }; }
var effect = { configChanged: signal("configChanged"), animationEnded: signal("animationEnded"),
               readConfig: function (key, fallback) { return key in config ? config[key] : fallback; } };
var effects = { windowAdded: signal("windowAdded"), stackingOrder: [], hasActiveFullScreenEffect: false };
var Effect = { Size: "Size", Translation: "Translation" };
var QEasingCurve = { InCubic: "InCubic", OutCubic: "OutCubic", Linear: "Linear" };
function animationTime(ms) { return ms; }
function animate(settings) { started.push(settings); return [started.length]; }
function cancel() {}
"""


@pytest.fixture
def zoom(qt_app):
    engine = QJSEngine()
    for source, name in ((STUBS, "stubs"), (EFFECT.read_text(), str(EFFECT))):
        result = engine.evaluate(source, name)
        assert not result.isError(), result.toString()
    return engine


def call(engine, function, *arguments):
    values = [engine.toScriptValue(value) for value in arguments]
    return engine.globalObject().property(function).call(values).toVariant()


def evaluate(engine, script):
    result = engine.evaluate(script)
    assert not result.isError(), result.toString()
    return result.toVariant()


def test_a_rect_drawn_where_its_window_is_needs_no_scaling_nor_moving(zoom):
    assert call(zoom, "placement", FRAME, FRAME) == {
        "size": {"value1": 400, "value2": 300},
        "translation": {"value1": 0, "value2": 0},
    }


def test_minimizing_folds_the_window_into_its_title_bar_then_flies_that_to_the_taskbar_button(zoom):
    title_bar = call(zoom, "metrics")["titleBarHeight"]
    steps = call(zoom, "segments", call(zoom, "minimizeKeyframes", FRAME, ICON), FRAME, 260)

    assert [(step["from"]["size"], step["to"]["size"], step["duration"]) for step in steps] == [
        ({"value1": 400, "value2": 300}, {"value1": 400, "value2": title_bar}, 130),
        ({"value1": 400, "value2": title_bar}, {"value1": 160, "value2": 22}, 130),
    ]


def test_the_folded_bar_keeps_the_windows_top_edge(zoom):
    title_bar = call(zoom, "metrics")["titleBarHeight"]
    fold = call(zoom, "segments", call(zoom, "minimizeKeyframes", FRAME, ICON), FRAME, 260)[0]

    assert fold["to"]["translation"] == {"value1": 0, "value2": -(300 - title_bar) / 2}


def maximize_window(zoom, *, instant=False):
    evaluate(
        zoom,
        f"""config = {{ Maximize: true, InstantMaximize: {json.dumps(instant)} }};
        handlers.configChanged();
        var window = {{
            visible: true, geometry: {json.dumps(FRAME)}, minimizedChanged: signal("minimizedChanged"),
            windowMaximizedStateAboutToChange: signal("aboutToMaximize"),
            windowMaximizedStateChanged: signal("maximized")
        }};
        handlers.windowAdded(window);
        handlers.aboutToMaximize(window);
        window.geometry = {{x: 0, y: 0, width: 640, height: 452}};
        handlers.maximized(window);""",
    )
    return evaluate(zoom, "started.map(({duration, keepAlive, animations}) => ({duration, keepAlive, animations}))")


def test_maximize_uses_one_continuous_transform(zoom):
    assert maximize_window(zoom) == [{
        "duration": 260,
        "keepAlive": False,
        "animations": [
            {"type": "Size", "from": {"value1": 400, "value2": 300}, "to": {"value1": 640, "value2": 452}},
            {"type": "Translation", "from": {"value1": -20, "value2": -26}, "to": {"value1": 0, "value2": 0}},
        ],
    }]


def test_xp_instant_maximize_bypasses_a_saved_zoom_animation(zoom):
    assert maximize_window(zoom, instant=True) == []


def minimize_window(zoom, icon):
    window = json.dumps({"geometry": FRAME, "iconGeometry": icon, "minimized": True})
    evaluate(
        zoom,
        f"""var window = Object.assign({window}, {{ minimizedChanged: signal("minimizedChanged"),
            windowMaximizedStateAboutToChange: signal("aboutToMaximize"),
            windowMaximizedStateChanged: signal("maximized") }});
        handlers.windowAdded(window);
        handlers.minimizedChanged();""",
    )
    return evaluate(zoom, "started.map(function (settings) { return settings.animations[0].type; })")


def choose(zoom, minimize_on):
    evaluate(zoom, f"config = {{ Minimize: {json.dumps(minimize_on)} }}; handlers.configChanged();")


def test_a_minimized_window_zooms_only_while_minimize_is_chosen_for_the_title_bar_zoom(zoom):
    choose(zoom, False)
    off = minimize_window(zoom, ICON)
    choose(zoom, True)

    assert (off, minimize_window(zoom, ICON)) == ([], ["Size"])


def test_a_window_without_a_taskbar_button_is_left_to_minimize_without_zooming(zoom):
    choose(zoom, True)

    assert minimize_window(zoom, {"x": 0, "y": 0, "width": 0, "height": 0}) == []


LUNA_TITLE_BAR = 30


def test_minimizing_folds_the_window_into_the_decorations_own_title_bar_height(zoom):
    keyframes = call(zoom, "minimizeKeyframes", FRAME, ICON, LUNA_TITLE_BAR)
    folded = call(zoom, "segments", keyframes, FRAME, 260)[0]["to"]["size"]
    assert folded == {"value1": 400, "value2": LUNA_TITLE_BAR}


def test_luna_title_strip_travels_from_the_frame_to_the_center_of_the_task_button(zoom):
    texture = {"x": 90, "y": 40, "width": 420, "height": 320}
    button = {"x": 20, "y": 452, "width": 160, "height": 40}
    minimized = call(zoom, "titleStripGeometry", FRAME, texture, button, LUNA_TITLE_BAR, True)
    restored = call(zoom, "titleStripGeometry", FRAME, texture, button, LUNA_TITLE_BAR, False)
    assert minimized["uniforms"] == {
        "canvasX": -70,
        "canvasY": 0,
        "canvasWidth": 490,
        "canvasHeight": 447,
        "sourceWidth": 420,
        "sourceHeight": 320,
        "stripX": 10,
        "stripY": 10,
        "stripWidth": 400,
        "stripHeight": 30,
        "taskX": -70,
        "taskY": 417,
        "taskWidth": 160,
        "minimizing": 1,
    }
    assert restored == {**minimized, "uniforms": {**minimized["uniforms"], "minimizing": 0}}


def test_classic_style_moves_the_inset_caption_band_at_the_measured_device_pixel_speed(zoom):
    uniforms = call(zoom, "titleStripGeometry", FRAME, FRAME, ICON, 18, True, 4)["uniforms"]
    assert (uniforms["stripX"], uniforms["stripY"], uniforms["stripWidth"], uniforms["stripHeight"]) == (4, 4, 392, 18)
    assert call(zoom, "classicStripDuration", uniforms, 1, 3) == 133
    assert call(zoom, "classicStripDuration", uniforms, 1.25, 3) == 167
    assert call(zoom, "classicStripDuration", uniforms, 1.25, 4.4) == 114
    assert call(zoom, "classicStripDuration", {**uniforms, "taskX": 354}, 1, 3) == 133
    assert call(zoom, "classicStripDuration", {**uniforms, "taskX": 404, "taskY": 4}, 1, 3) == 133


def test_windows_98_title_strip_caps_long_travel_without_sluggish_high_dpi_motion(zoom):
    uniforms = call(zoom, "titleStripGeometry", FRAME, FRAME, ICON, 18, True, 4)["uniforms"]
    assert call(zoom, "classicStripDuration", uniforms, 1.25, 3, 300) == 167
    assert call(zoom, "classicStripDuration", uniforms, 3, 3, 300) == 300
