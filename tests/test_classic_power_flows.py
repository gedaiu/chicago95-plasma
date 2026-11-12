"""Drive actual classic power dialogs; intercept every backend command and timer.

POWER_FLOW_OUTPUT optionally retains renders for the review recording. These are
app-flow checks, not proof of OS shutdown or compositor transitions.
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QDialog, QPushButton

STYLES = ("1995", "1998", "2000", "2001")


def cases():
    for style, choices in (
        ("1995", (0, 1, 2, 3)),
        ("1998", (4, 0, 1, 2)),
        ("2000", (3, 0, 1, 4)),
        ("2001", (3, 0, 1, 4, 5)),
    ):
        for action in (*choices, "cancel", "logoff", "cancel-logoff"):
            yield style, action


@pytest.mark.parametrize("style,action", list(cases()))
def test_classic_dialog_flow(shutdown, qt_app, monkeypatch, tmp_path, style, action):
    events, timers = [], []
    folder = Path(os.environ.get("POWER_FLOW_OUTPUT", tmp_path)) / style / str(action)
    folder.mkdir(parents=True, exist_ok=True)
    look = {
        **shutdown.chicago95ui.look_settings(),
        "style": style,
        "widgetStyle": "classic",
        "osCompany": "Microsoft",
        "osLogo": "",
        "companyLogo": "",
        "edition": "Professional",
        "osName": {"1995": "Windows 95", "1998": "Windows 98", "2000": "Windows 2000", "2001": "Windows XP"}[style],
    }
    monkeypatch.setattr(shutdown.chicago95ui, "look_settings", lambda: look)
    monkeypatch.setattr(shutdown, "dbus_caller", lambda: ["mock-dbus"])
    monkeypatch.setattr(shutdown, "play_shutdown_sound", lambda dry_run: None)
    monkeypatch.setattr(shutdown, "virtual_screen_geometry", lambda app: QRect(0, 0, 800, 600))
    monkeypatch.setattr(shutdown, "run_command", lambda command, dry_run: events.append((command, dry_run)))
    monkeypatch.setattr(shutdown, "QTimer", SimpleNamespace(singleShot=lambda delay, cb: timers.append((delay, cb))))

    def answer(dialog):
        dialog.show()
        if isinstance(action, int):
            if hasattr(dialog, "combo"):
                dialog.combo.setCurrentIndex(dialog.combo.findData(action))
                assert dialog.combo.toolTip() == dialog.description.text()
                assert dialog.combo.itemData(dialog.combo.currentIndex(), Qt.ToolTipRole) == dialog.combo.toolTip()
            else:
                radio = dialog.radios[[choice for choice, _ in dialog.choices].index(action)]
                radio.click()
                assert radio.toolTip()
        qt_app.processEvents()
        dialog.grab().save(str(folder / "dialog.png"))
        cancelled = str(action).startswith("cancel")
        button_text = {"&No", "Cancel"} if cancelled else {"&Yes", "OK"}
        button = next(button for button in dialog.findChildren(QPushButton) if button.text() in button_text)
        assert button.toolTip()
        button.click()
        result = dialog.result() == QDialog.Accepted
        if not cancelled and isinstance(action, int):
            assert dialog.choice == action
        dialog.close()
        return result

    def event_loop():
        qt_app.processEvents()
        for widget in qt_app.topLevelWidgets():
            if isinstance(widget, shutdown.SafeScreen) and widget.isVisible():
                widget.grab().save(str(folder / "safe-screen.png"))
        assert not events, "Backend ran before the status screen was presented"
        for _, callback in sorted(timers, key=lambda item: item[0]):
            callback()
        for widget in qt_app.topLevelWidgets():
            if isinstance(widget, shutdown.SafeScreen):
                widget.close()
        return 0

    monkeypatch.setattr(
        shutdown.chicago95ui, "make_app", lambda name: SimpleNamespace(exec=event_loop, quit=lambda: None)
    )
    monkeypatch.setattr(shutdown, "ask", answer)
    args = ["chicago95-shutdown", "--dry-run"]
    if action in ("logoff", "cancel-logoff"):
        args.append("--log-off")
    monkeypatch.setattr(sys, "argv", args)
    assert shutdown.main() == 0
    if str(action).startswith("cancel"):
        assert events == []
    else:
        choice = shutdown.LOG_OFF if action == "logoff" else action
        assert events == [(shutdown.shutdown_command(choice, ["mock-dbus"]), True)]


@pytest.mark.parametrize("style", STYLES)
@pytest.mark.parametrize("logoff", [False, True])
def test_classic_tooltips_render_without_accepting(shutdown, qt_app, tmp_path, style, logoff):
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QHelpEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QToolTip

    dialog = (shutdown.LogOffDialog if logoff else shutdown.ShutDownDialog)({"style": style})
    dialog.show()
    dialog.activateWindow()
    QTest.qWait(30)
    buttons = [button for button in dialog.findChildren(QPushButton) if button.toolTip() and button.isEnabled()]
    if not logoff:
        buttons += [dialog.combo] if hasattr(dialog, "combo") else dialog.radios
    for index, button in enumerate(buttons):
        point = button.rect().center()
        QTest.mouseMove(button, point)
        qt_app.sendEvent(button, QHelpEvent(QEvent.ToolTip, point, button.mapToGlobal(point)))
        QTest.qWait(30)
        assert QToolTip.isVisible()
        assert QToolTip.text() == button.toolTip()
        assert dialog.isVisible()
        tooltip = next(
            widget for widget in qt_app.topLevelWidgets() if widget.isVisible() and widget.windowType() == Qt.ToolTip
        )
        folder = Path(os.environ.get("POWER_FLOW_OUTPUT", tmp_path)) / style / ("logoff" if logoff else "0")
        folder.mkdir(parents=True, exist_ok=True)
        assert tooltip.grab().save(str(folder / f"tooltip-{index}.png"))
    QToolTip.hideText()
    dialog.close()


@pytest.mark.parametrize("logoff", [False, True])
def test_control_panel_power_test_always_uses_dry_run(qt_app, tmp_path, monkeypatch, logoff):
    from conftest import load_script

    panel = load_script("chicago95-control-panel")
    preview = panel.ShutDownPreview()
    (tmp_path / "config").mkdir()
    (tmp_path / "config/chicago95rc").write_text("[StartMenu]\nstyle=2000\n")
    preview.shot = tmp_path / "dialog.png"
    launches = []

    class Process:
        def __init__(self, parent):
            pass

        def setProcessEnvironment(self, environment):
            self.environment = environment

        def start(self, program, arguments):
            launches.append((self.environment, arguments))

    monkeypatch.setattr(panel, "QProcess", Process)
    preview.open_test(logoff)
    environment, arguments = launches[0]
    assert "--dry-run" in arguments
    assert ("--log-off" in arguments) == logoff
    config = Path(environment.value("XDG_CONFIG_HOME"))
    assert config != tmp_path / "config"
    assert (config / "chicago95rc").read_text() == "[StartMenu]\nstyle=2000\n"
    preview.close()
