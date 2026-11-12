import pytest
from conftest import load_script
from PySide6.QtCore import QRect

from .luna_tools_support import grab_picture, hex_rgb, reference, save_preview

SCREEN = QRect(0, 0, 800, 600)


@pytest.fixture
def shutdown():
    return load_script("chicago95-shutdown")


@pytest.fixture
def screen_picture(luna_look, shutdown):
    screen = shutdown.shutting_down_screen(SCREEN, hold_until_input=False)
    screen.show()
    yield grab_picture(screen)
    screen.close()


def test_luna_look_wants_the_xp_dialogs(luna_look, shutdown):
    assert shutdown.luna_dialogs_wanted()


def test_luna_screenshot_dialog_is_the_xp_turn_off_dialog(luna_look, shutdown):
    dialog = shutdown.screenshot_dialog(log_off=False)
    assert (dialog.width(), dialog.height()) == (314, 200)


def test_luna_log_off_screenshot_dialog_is_the_xp_log_off_dialog(luna_look, shutdown):
    dialog = shutdown.screenshot_dialog(log_off=True)
    assert type(dialog).__name__ == "LogOffDialog"


def test_classic_look_keeps_the_black_safe_screen(shutdown):
    assert type(shutdown.shutting_down_screen(SCREEN, hold_until_input=False)).__name__ == "SafeScreen"


def test_luna_shutting_down_screen_is_the_xp_blue_one(luna_look, shutdown):
    assert type(shutdown.shutting_down_screen(SCREEN, hold_until_input=False)).__name__ == "ShuttingDownScreen"


@pytest.mark.parametrize(
    ("point", "colour"),
    [((400, 20), "#00309C"), ((400, 300), "#5A7EDC"), ((400, 504), "#C1814D")],
)
def test_luna_shutting_down_screen_bands_have_the_xp_colours_at(screen_picture, point, colour):
    assert screen_picture.getpixel(point) == hex_rgb(colour)


def test_luna_shutting_down_screen_has_no_classic_black_or_orange_safe_screen(screen_picture):
    assert screen_picture.getpixel((5, 300)) != (0, 0, 0)


def test_luna_shutting_down_screen_draws_white_lettering_where_the_reference_does(screen_picture):
    save_preview("shutdown", screen_picture, reference("xpshuttingdown.png"))
    text_band = screen_picture.crop((300, 330, 560, 360))
    assert (255, 255, 255) in [colour for _count, colour in text_band.getcolors(maxcolors=1 << 20)]


@pytest.mark.parametrize('chooser', ['luna_turn_off_choice', 'luna_log_off_choice'])
def test_power_dialog_loads_effect_before_showing(shutdown, monkeypatch, chooser):
    events = []
    monkeypatch.setattr(shutdown.subprocess, 'run', lambda command, **kw: events.append(command))
    monkeypatch.setattr(shutdown, 'ask', lambda dialog: events.append('show') or False)
    assert getattr(shutdown, chooser)() is None
    assert events[0][-2:] == ['org.kde.kwin.Effects.loadEffect', 'chicago95shutdown']
    assert events[1] == 'show'


@pytest.mark.parametrize('failure', [FileNotFoundError(), __import__('subprocess').TimeoutExpired('gdbus', 2)])
def test_missing_compositor_does_not_block_dialog(shutdown, monkeypatch, failure):
    def unavailable(*args, **kwargs):
        raise failure
    monkeypatch.setattr(shutdown.subprocess, 'run', unavailable)
    shutdown.ensure_luna_grayscale_effect()


@pytest.mark.parametrize('button, choice', [('switch_user', 'SWITCH_USER'), ('log_off', 'LOG_OFF')])
def test_luna_log_off_dialog_button_returns_its_own_choice(shutdown, monkeypatch, button, choice):
    monkeypatch.setattr(shutdown, 'ensure_luna_grayscale_effect', lambda: None)
    monkeypatch.setattr(shutdown, 'ask', lambda dialog: dialog.commands[button]() or True)
    assert shutdown.luna_log_off_choice() == getattr(shutdown, choice)
