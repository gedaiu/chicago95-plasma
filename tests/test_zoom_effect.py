"""The title bar zoom (kwin-effects/chicago95zoom): Windows 95/98's minimize, restore and maximize motion, where the
window folds into its title bar and that bar flies to its taskbar button or its new place.

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


def test_maximizing_folds_flies_and_unfolds_in_three_equal_steps(zoom):
    new_frame = {"x": 0, "y": 0, "width": 640, "height": 452}
    steps = call(zoom, "segments", call(zoom, "maximizeKeyframes", FRAME, new_frame), new_frame, 270)

    assert ([step["duration"] for step in steps], steps[-1]["to"]["size"]) == (
        [90, 90, 90],
        {"value1": 640, "value2": 452},
    )


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
