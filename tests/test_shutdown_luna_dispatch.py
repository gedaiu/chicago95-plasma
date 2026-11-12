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
    monkeypatch.undo()  # the real chicago95rc back first, or the style "restored" is this test's XP one
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

    choice = shutdown.ask_luna_choice(lambda commands, **_branding: type("Fake", (), {"commands": commands})(), clicked)

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


@pytest.fixture
def branded(shutdown, tmp_path, monkeypatch, qt_app):
    """An XP look whose branding names Fedora Linux 44 with a logo of its own."""
    config = tmp_path / "chicago95rc"
    monkeypatch.setattr(chicago95ui, "CHICAGO95RC", str(config))
    logo = tmp_path / "fedora-logo-icon.png"
    logo.write_bytes(b"")
    config.write_text(f"[Look]\nwidgetStyle=luna\n[Branding]\nosName=Fedora Linux 44\nosLogo={logo}\n")
    yield logo
    monkeypatch.undo()
    chicago95ui.apply_style(qt_app)


def test_the_xp_log_off_dialog_names_the_branded_system(shutdown, branded):
    assert shutdown.screenshot_dialog(log_off=True).title == "Log Off Fedora Linux"


def test_the_xp_dialogs_take_the_branded_logo(shutdown, branded):
    assert shutdown.luna_branding()["logo"] == str(branded)


@pytest.mark.parametrize("action", ["logoff", "poweroff", "restart"])
def test_luna_status_screens_precede_real_backend_request(shutdown, monkeypatch, action):
    """Exercise the app entry point but intercept timers and every backend command."""
    import sys
    from types import SimpleNamespace

    from PySide6.QtCore import QRect

    events, timers = [], []
    screen = SimpleNamespace(
        set_status=events.append,
        showFullScreen=lambda: events.append("shown"),
    )

    def event_loop():
        for _delay, callback in sorted(timers, key=lambda item: item[0]):
            callback()
        return 0

    app = SimpleNamespace(exec=event_loop, quit=lambda: events.append("quit"))
    monkeypatch.setattr(shutdown.chicago95ui, "make_app", lambda name: app)
    monkeypatch.setattr(shutdown, "virtual_screen_geometry", lambda app: QRect(0, 0, 800, 600))
    monkeypatch.setattr(shutdown, "shutting_down_screen", lambda *args, **kwargs: screen)
    monkeypatch.setattr(shutdown, "luna_dialogs_wanted", lambda: True)
    monkeypatch.setattr(shutdown, "play_shutdown_sound", lambda dry_run: None)
    monkeypatch.setattr(shutdown, "dbus_caller", lambda: ["mock-dbus"])
    monkeypatch.setattr(shutdown, "run_command", lambda command, dry_run: events.append(command))
    monkeypatch.setattr(shutdown, "QTimer", SimpleNamespace(singleShot=lambda delay, cb: timers.append((delay, cb))))
    choice = {"logoff": shutdown.LOG_OFF, "poweroff": shutdown.SHUT_DOWN, "restart": shutdown.RESTART}[action]
    monkeypatch.setattr(shutdown, "log_off_choice", lambda: choice)
    monkeypatch.setattr(shutdown, "turn_off_choice", lambda: choice)
    monkeypatch.setattr(sys, "argv", ["chicago95-shutdown"] + (["--log-off"] if action == "logoff" else []))
    assert shutdown.main() == 0
    expected = ["Logging off...", "shown"]
    if action != "logoff":
        expected += ["Windows is shutting down..."]
    assert events == expected + [shutdown.shutdown_command(choice, ["mock-dbus"]), "quit"]
