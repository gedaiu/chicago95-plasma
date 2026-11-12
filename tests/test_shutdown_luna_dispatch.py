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

    choice = shutdown.log_off_choice()

    assert (choice, type(dialogs[0]).__name__) == (None, "LogOffDialog")


def test_log_off_asks_the_classic_log_off_dialog_when_widget_style_is_classic(shutdown, asked_dialogs):
    dialogs = asked_dialogs("classic")

    shutdown.log_off_choice()

    assert type(dialogs[0]) is shutdown.LogOffDialog


def test_ask_luna_choice_returns_shut_down_when_the_turn_off_button_is_pressed(shutdown, monkeypatch):
    clicked = {"turn_off": shutdown.SHUT_DOWN, "restart": shutdown.RESTART, "stand_by": shutdown.STAND_BY}

    def press_every_button(dialog):
        dialog.commands["turn_off"]()
        return True

    monkeypatch.setattr(shutdown, "ask", press_every_button)

    choice = shutdown.ask_luna_choice(lambda commands: type("Fake", (), {"commands": commands})(), clicked)

    assert choice == shutdown.SHUT_DOWN


@pytest.mark.parametrize("style", ["1995", "1998", "2000", "2001", "luna"])
@pytest.mark.parametrize("log_off", [False, True])
def test_power_dialogs_stay_on_top_and_are_tools_in_every_look(shutdown, qt_app, style, log_off):
    from PySide6.QtCore import Qt

    if style == "luna":
        import chicago95lunadialogs

        dialog_type = chicago95lunadialogs.LogOffDialog if log_off else chicago95lunadialogs.TurnOffDialog
        dialog = dialog_type({name: lambda: None for name in ("turn_off", "restart", "stand_by", "log_off", "cancel")})
    else:
        dialog_type = shutdown.LogOffDialog if log_off else shutdown.ShutDownDialog
        dialog = dialog_type({"style": style})
    assert dialog.windowType() == Qt.Tool
    assert dialog.windowFlags() & Qt.WindowStaysOnTopHint
    assert dialog.windowFlags() & Qt.FramelessWindowHint
    dialog.close()
