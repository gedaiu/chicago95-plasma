"""Shutdown saturation affects the desktop until the last Luna dialog closes."""
import pytest
from conftest import REPO
from PySide6.QtQml import QJSEngine


@pytest.fixture(params=["legacy", "current"])
def effect(qt_app, request):
    engine = QJSEngine()
    stubs = '''
var handlers = {}, starts = [], cancelled = [];
function signal(key) { return {connect: function(fn) {handlers[key] = fn;}}; }
function win(name, app) { return {caption: name, windowClass: app, visible: true,
 captionChanged: signal(name + 'Caption'), visibleChanged: signal(name + 'Visible')}; }
var desktop = win('Desktop', 'plasmashell');
var panel = win('Panel', 'plasmashell');
var dialog = win('Turn off computer', 'python3 chicago95-shutdown');
var effects = {stackingOrder: [desktop, panel], windowAdded: signal('added'),
 windowClosed: signal('closed'), windowDeleted: signal('deleted'),
 windowShown: signal('shown'), windowHidden: signal('hidden')};
var Effect = {Saturation: 'Saturation'};
var QEasingCurve = {Linear: 'Linear'};
function animationTime(ms) {return ms;}
function set(config) {starts.push(config); return starts.length;}
function cancel(id) {cancelled.push(id);}
'''
    if request.param == "current":
        stubs += "delete effects.windowShown; delete effects.windowHidden;"
    for source in (stubs, (REPO / 'kwin-effects/chicago95shutdown/contents/code/main.js').read_text()):
        result = engine.evaluate(source)
        assert not result.isError(), result.toString()
    return engine


def evaluate(engine, script):
    result = engine.evaluate(script)
    assert not result.isError(), result.toString()
    return result.toVariant()


def test_shutdown_fades_desktop_and_panel_but_leaves_dialog_coloured(effect):
    evaluate(effect, 'effects.stackingOrder.push(dialog); handlers.added(dialog);')
    assert evaluate(effect, 'starts.map(s => [s.window.caption, s.duration, s.animations[0]])') == [
        [name, 2000, {'type': 'Saturation', 'from': 1, 'to': 0}] for name in ('Desktop', 'Panel')
    ]
    evaluate(effect, 'handlers.closed(dialog)')
    assert evaluate(effect, 'cancelled') == [1, 2]


def test_unrelated_dialog_does_not_desaturate_the_desktop(effect):
    evaluate(effect, "handlers.added(win('Turn off computer', 'other-app'))")
    assert evaluate(effect, 'starts.length') == 0


def test_new_windows_are_grayscale_and_hiding_dialog_restores_colour(effect):
    evaluate(effect, "effects.stackingOrder.push(dialog); handlers.added(dialog);")
    evaluate(effect, "var other = win('Other', 'editor'); effects.stackingOrder.push(other); handlers.added(other);")
    assert evaluate(effect, 'starts[2].window.caption') == 'Other'
    evaluate(effect, "dialog.visible = false; handlers['Turn off computerVisible']()")
    assert evaluate(effect, 'cancelled') == [1, 2, 3]


def test_second_shutdown_dialog_keeps_desktop_grayscale_until_both_close(effect):
    evaluate(effect, "var second = win('Turn off computer', 'chicago95-shutdown');")
    evaluate(effect, "effects.stackingOrder.push(dialog, second); handlers.added(dialog); handlers.added(second);")
    evaluate(effect, "handlers.closed(dialog)")
    assert evaluate(effect, 'cancelled') == []
    evaluate(effect, "handlers.closed(second)")
    assert evaluate(effect, 'cancelled') == [1, 2]


def test_logoff_fades_background_and_cancel_restores_it(effect):
    evaluate(effect, "dialog.caption = 'Log Off Windows'; effects.stackingOrder.push(dialog); handlers.added(dialog);")
    assert evaluate(effect, 'starts.map(s => s.window.caption)') == ['Desktop', 'Panel']
    evaluate(effect, 'handlers.closed(dialog)')
    assert evaluate(effect, 'cancelled') == [1, 2]


def test_hidden_dialog_waits_until_shown(effect):
    evaluate(effect, 'dialog.visible = false; effects.stackingOrder.push(dialog); handlers.added(dialog);')
    assert evaluate(effect, 'starts.length') == 0
    evaluate(effect, "dialog.visible = true; handlers['Turn off computerVisible']();")
    assert evaluate(effect, 'starts.length') == 2


def test_title_arriving_after_window_added_activates_effect(effect):
    evaluate(effect, "dialog.caption = ''; effects.stackingOrder.push(dialog); handlers.added(dialog);")
    assert evaluate(effect, 'starts.length') == 0
    evaluate(effect, "dialog.caption = 'Turn off computer'; handlers['Turn off computerCaption']();")
    assert evaluate(effect, 'starts.length') == 2


def test_stipple_claims_open_and_close_animation_without_desaturating(effect):
    evaluate(effect, '''
var grabs = [];
var effect = {grab: function(window, role) {grabs.push([window.caption, role]); return true;}};
Effect.WindowAddedGrabRole = "added";
Effect.WindowClosedGrabRole = "closed";
var backdrop = win("Chicago95 shutdown backdrop", "python3 chicago95-shutdown");
handlers.added(backdrop);
''')
    grabs = evaluate(effect, 'grabs')
    assert ["Chicago95 shutdown backdrop", "added"] in grabs
    assert ["Chicago95 shutdown backdrop", "closed"] in grabs
    assert evaluate(effect, 'starts.length') == 0
