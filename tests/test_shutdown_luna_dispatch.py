import chicago95ui
import pytest


@pytest.fixture
def asked_dialogs(shutdown, tmp_path, monkeypatch, qt_app):
    config = tmp_path / "chicago95rc"
    monkeypatch.setattr(chicago95ui, "CHICAGO95RC", str(config))
    dialogs = []

    def record(dialog):
        dialogs.append(dialog)
        return False

    monkeypatch.setattr(shutdown, "ask", record)

    def choose(widget_style):
        config.write_text(f"[Look]\nwidgetStyle={widget_style}\n")
        return dialogs

    yield choose
    chicago95ui.apply_style(qt_app)


def test_turn_off_choice_asks_the_314_by_200_luna_dialog_when_widget_style_is_luna(shutdown, asked_dialogs):
    dialogs = asked_dialogs("luna")

    choice = shutdown.turn_off_choice()

    assert (choice, type(dialogs[0]).__name__, (dialogs[0].width(), dialogs[0].height())) == (
        None,
        "TurnOffDialog",
        (314, 200),
    )


def test_turn_off_choice_asks_the_shut_down_dialog_when_widget_style_is_classic(shutdown, asked_dialogs):
    dialogs = asked_dialogs("classic")

    shutdown.turn_off_choice()

    assert type(dialogs[0]) is shutdown.ShutDownDialog


def test_log_off_asks_the_luna_log_off_dialog_when_widget_style_is_luna(shutdown, asked_dialogs):
    dialogs = asked_dialogs("luna")

    confirmed = shutdown.log_off_confirmed()

    assert (confirmed, type(dialogs[0]).__name__) == (False, "LogOffDialog")


def test_log_off_asks_the_classic_log_off_dialog_when_widget_style_is_classic(shutdown, asked_dialogs):
    dialogs = asked_dialogs("classic")

    shutdown.log_off_confirmed()

    assert type(dialogs[0]) is shutdown.LogOffDialog


def test_ask_luna_choice_returns_shut_down_when_the_turn_off_button_is_pressed(shutdown, monkeypatch):
    clicked = {"turn_off": shutdown.SHUT_DOWN, "restart": shutdown.RESTART, "stand_by": shutdown.STAND_BY}

    def press_every_button(dialog):
        dialog.commands["turn_off"]()
        return True

    monkeypatch.setattr(shutdown, "ask", press_every_button)

    choice = shutdown.ask_luna_choice(lambda commands: type("Fake", (), {"commands": commands})(), clicked)

    assert choice == shutdown.SHUT_DOWN
