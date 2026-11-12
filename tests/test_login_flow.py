"""Flow rehearsal ordering. Native KWin integration lives in record_login_flow.py."""

import json

import pytest
from conftest import REPO, load_script
from login_flow import FlowTestDialog
from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest


@pytest.fixture
def flow(qt_app, tmp_path):
    image = QImage(800, 600, QImage.Format_RGB32)
    image.fill(QColor("#123456"))
    image.save(str(tmp_path / "desktop.png"))
    panel = load_script("chicago95-control-panel")
    preview = panel.LogOnPreview(interactive=True)
    preview.refresh({"LOGIN_STYLE": "luna"})
    dialog = FlowTestDialog(preview, REPO / "luna", desktop_image=tmp_path / "desktop.png")
    dialog.show()
    QTest.qWait(100)
    yield dialog
    dialog.close()


def test_boot_cannot_skip_authentication_or_loading(flow):
    flow.root.desktopReady()
    assert flow.root.property("stage") == "boot"
    flow.advance()
    flow.root.desktopReady()
    assert flow.root.property("stage") == "login"


def test_failure_stays_on_login_and_success_waits_for_desktop(flow):
    flow.advance()
    flow.root.property("login").setProperty("selectedName", "Taylor")
    flow.authenticate("Taylor", 0)
    assert flow.root.property("stage") == "login"
    flow.fail.setChecked(False)
    flow.hold.setChecked(True)
    flow.authenticate("Taylor", 0)
    assert flow.root.property("stage") == "loading"
    assert flow.root.property("userName") == "Taylor"
    flow.root.setProperty("desktopImage", QUrl())
    flow.advance()
    assert flow.root.property("stage") == "loading"


def test_recorded_scenario_switches_users_and_preserves_event_order(flow, tmp_path):
    flow.start_recording(tmp_path / "recording")
    flow.root.setProperty("fadeMilliseconds", 40)
    flow.run_scenario()
    flow.advance()
    for _ in range(240):
        QTest.qWait(100)
        if not flow.automating and not flow.recorder.isActive():
            break
    assert not flow.automating, flow.events
    names = [event["event"] for event in flow.events]
    assert names.count("authentication-failed") == 1
    assert names.count("desktop") == 4
    assert names.count("switch-user") == 2
    assert names.count("log-off") == 1
    logoff = names.index("log-off")
    assert names[logoff + 1 : logoff + 3] == ["logging-off", "login"]
    shutdown = names.index("shutdown-requested")
    assert names[shutdown + 1 : shutdown + 6] == [
        "logging-off", "shutting-down", "power-simulated", "powered-off", "scenario-complete"
    ]
    assert "scenario-complete" in names
    first = names.index("authentication-succeeded")
    assert names[first : first + 5] == [
        "authentication-succeeded",
        "loading",
        "session-start-requested",
        "fading",
        "desktop",
    ]
    data = json.loads((tmp_path / "recording/events.json").read_text())
    assert len(data["frames"]) > 30
    assert all(b["seconds"] > a["seconds"] for a, b in zip(data["frames"], data["frames"][1:], strict=False))
    assert "test-only" not in json.dumps(data)


def test_loading_stays_visible_until_explicit_desktop_release(flow):
    flow.advance()
    flow.root.property("login").setProperty("selectedName", "Alex")
    flow.fail.setChecked(False)
    flow.hold.setChecked(True)
    flow.authenticate("Alex", 0)
    QTest.qWait(200)
    assert flow.root.property("stage") == "loading"
    flow.advance()
    assert flow.root.property("stage") == "fading"
    QTest.qWait(650)
    assert flow.root.property("stage") == "desktop"


def test_installed_preview_tree_is_used_without_checkout(monkeypatch, tmp_path):
    panel = load_script("chicago95-control-panel")
    monkeypatch.setattr(panel, "repo_of", lambda values: tmp_path / "missing-checkout")
    monkeypatch.setattr(panel.Path, "home", lambda: tmp_path)
    assert panel.luna_root_of({}) == tmp_path / ".local/share/chicago95/luna"


@pytest.mark.parametrize("reboot,final_stage", [(False, "powered-off"), (True, "boot")])
def test_power_rehearsal_waits_for_both_status_screens(flow, reboot, final_stage):
    flow.boot.stop()
    flow.root.setProperty("stage", "desktop")
    flow.shut_down(reboot=reboot)
    assert flow.root.property("stage") == "logging-off"
    assert not any(event["event"] == "power-simulated" for event in flow.events)
    flow.advance()
    assert flow.root.property("stage") == "shutting-down"
    assert not any(event["event"] == "power-simulated" for event in flow.events)
    flow.advance()
    assert flow.root.property("stage") == final_stage
    power = next(event for event in flow.events if event["event"] == "power-simulated")
    assert power["action"] == ("restart" if reboot else "poweroff")
