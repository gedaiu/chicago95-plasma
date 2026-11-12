"""Interactive, recorded Luna flow rehearsal. Authentication is always simulated.

Uses the shipped QML screens. The desktop is a captured image; the 500ms fade
rehearses KWin's default login effect, not the actual compositor handoff.
"""

import json
import shutil
import time
from pathlib import Path

from login_preview import LOGGED_IN_ROLE, NAME_ROLE
from PySide6.QtCore import QProcess, QTimer, QUrl
from PySide6.QtWidgets import QCheckBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class FlowTestDialog(QDialog):
    def __init__(self, preview, luna_root, parent=None, desktop_image=None):
        super().__init__(parent)
        self.setWindowTitle("Test Luna startup flow")
        self.preview = preview
        self.started = time.monotonic()
        self.events = []
        self.frames = []
        self.output = None
        self.capture = None
        self.encoder = None
        self.automating = False
        self.auto_step = 0
        self.power_action = None
        self.desktop_path = Path(desktop_image) if desktop_image else Path(preview.scratch) / "desktop.png"
        from chicago95lunapreviews import copy_screen_trees

        copy_screen_trees(luna_root, Path(preview.scratch) / "theme/luna", "splash", "sddm")
        context = preview.context
        preview.load(Path(preview.scratch) / "theme/luna/splash/LunaFlow.qml", context)
        self.root = preview.rootObject()
        if self.root is None:
            raise RuntimeError("Could not load the Luna flow test")
        self.root.stageChanged.connect(self.stage_changed)
        self.root.sessionRequested.connect(self.session_requested)
        self.root.desktopShown.connect(self.desktop_shown)
        context["sddm"].loginAttempted.connect(self.authenticate)
        context["sddm"].powerRequested.connect(lambda action: self.log_event("power-simulated", action=action))
        self.fail = QCheckBox("Fail authentication")
        self.fail.setChecked(True)
        self.hold = QCheckBox("Hold loading screen")
        self.status = QLabel("Preparing desktop capture…")
        self.status.setWordWrap(True)
        self.note = QLabel(
            "Simulation: real Luna screens, dummy accounts and a desktop snapshot. No real login or logout."
        )
        self.note.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.addWidget(preview)
        layout.addWidget(self.note)
        layout.addWidget(self.status)
        row = QHBoxLayout()
        self.buttons = {}
        for text, callback in (
            ("Restart", self.restart),
            ("Continue", self.advance),
            ("Switch user", self.switch_user),
            ("Log off", self.log_off),
            ("Shut down", self.shut_down),
            ("Reboot", lambda: self.shut_down(reboot=True)),
            ("Run scenario", self.run_scenario),
            ("Record…", self.record),
            ("Close", self.close),
        ):
            button = QPushButton(text)
            button.setAutoDefault(False)
            button.clicked.connect(callback)
            row.addWidget(button)
            self.buttons[text] = button
        layout.addLayout(row)
        options = QHBoxLayout()
        options.addWidget(self.fail)
        options.addWidget(self.hold)
        layout.addLayout(options)
        self.boot = QTimer(self)
        self.boot.setSingleShot(True)
        self.boot.timeout.connect(self.advance)
        self.loading = QTimer(self)
        self.loading.setSingleShot(True)
        self.loading.timeout.connect(self.advance)
        self.recorder = QTimer(self)
        self.recorder.setInterval(50)
        self.recorder.timeout.connect(self.record_frame)
        self.auto_timer = QTimer(self)
        self.auto_timer.setSingleShot(True)
        self.auto_timer.timeout.connect(self.auto_login)
        self.stage_changed()
        if desktop_image:
            self.desktop_captured(0)
        else:
            self.capture = QProcess(self)
            self.capture.finished.connect(lambda code, status: self.desktop_captured(code))
            self.capture.errorOccurred.connect(lambda error: self.capture_failed())
            # Keep this test window out of the desktop snapshot.
            QTimer.singleShot(0, self.hide)
            self.capture.start(
                "spectacle", ["--background", "--nonotify", "--fullscreen", "--output", str(self.desktop_path)]
            )

    def log_event(self, name, **details):
        self.events.append({"event": name, "seconds": round(time.monotonic() - self.started, 4), **details})

    def capture_failed(self):
        self.show()
        self.status.setText(
            "Desktop capture failed. Close and retry when Spectacle is available; no substitute desktop is used."
        )
        self.log_event("capture-failed")

    def desktop_captured(self, code):
        if code or not self.desktop_path.is_file():
            self.capture_failed()
            return
        self.root.setProperty("desktopImage", QUrl.fromLocalFile(str(self.desktop_path)))
        self.log_event("desktop-snapshot-ready")
        self.show()
        self.restart()

    def stage_changed(self):
        stage = self.root.property("stage")
        self.log_event(stage, user=self.root.property("userName"))
        self.status.setText(
            {
                "boot": "Boot preview — Continue skips ahead.",
                "login": "Select an account and use a dummy password.",
                "loading": "Loading the selected account; Continue releases the desktop.",
                "fading": "Fading to the captured desktop.",
                "logging-off": "Logging off the simulated account.",
                "shutting-down": "Showing the shutdown screen; no power action is performed.",
                "powered-off": "Simulated power off. Restart begins another rehearsal.",
                "desktop": "Desktop reached. Switch user or log off to test another account.",
            }[stage]
        )
        for key in ("Switch user", "Log off", "Shut down", "Reboot"):
            self.buttons[key].setEnabled(stage == "desktop")

    def restart(self):
        self.power_action = None
        self.loading.stop()
        self.boot.stop()
        self.root.restart()
        self.boot.start(3000)

    def advance(self):
        self.loading.stop()
        stage = self.root.property("stage")
        if stage == "boot":
            self.boot.stop()
            self.root.showLogin()
            if self.automating:
                self.auto_timer.start(400)
        elif stage == "logging-off":
            if self.power_action:
                self.root.showShutdown()
                self.loading.start(1500)
            else:
                self.root.showLogin()
                if self.automating:
                    self.auto_timer.start(600)
        elif stage == "shutting-down":
            action = self.power_action
            self.log_event("power-simulated", action=action)
            if action == "restart":
                self.restart()
            else:
                self.root.setProperty("stage", "powered-off")
                if self.automating:
                    self.log_event("scenario-complete")
                    self.automating = False
                    QTimer.singleShot(400, self.stop_recording)
        elif stage == "loading":
            if not self.root.desktopReady():
                self.status.setText("Desktop capture is not ready; keeping the loading screen visible.")

    def authenticate(self, user, session):
        if self.root.property("stage") != "login":
            return
        if self.fail.isChecked():
            self.log_event("authentication-failed", user=user)
            self.preview.context["sddm"].loginFailed.emit()
            if self.automating:
                self.auto_timer.start(600)
        else:
            self.log_event("authentication-succeeded", user=user, session=session)
            self.preview.context["sddm"].loginSucceeded.emit()

    def session_requested(self, user):
        self.log_event("session-start-requested", user=user)
        if not self.hold.isChecked():
            self.loading.start(1500)

    def set_logged_in(self, user, value):
        model = self.preview.context["userModel"]
        for row in range(model.rowCount()):
            index = model.index(row, 0)
            if model.data(index, NAME_ROLE) == user:
                model.setData(index, value, LOGGED_IN_ROLE)

    def desktop_shown(self):
        self.set_logged_in(self.root.property("userName"), True)
        if self.automating:
            self.auto_timer.start(700)

    def switch_user(self):
        self.log_event("switch-user", user=self.root.property("userName"))
        self.root.showLogin()

    def log_off(self):
        self.power_action = None
        user = self.root.property("userName")
        self.set_logged_in(user, False)
        self.log_event("log-off", user=user)
        self.root.showLogoff()
        self.loading.start(1500)

    def shut_down(self, reboot=False):
        if self.root.property("stage") != "desktop":
            return
        self.power_action = "restart" if reboot else "poweroff"
        self.log_event("shutdown-requested", action=self.power_action)
        self.root.showLogoff()
        self.loading.start(1500)

    def run_scenario(self):
        if not self.recorder.isActive():
            self.record()
        if not self.recorder.isActive():
            return
        self.automating = True
        self.auto_step = 0
        self.hold.setChecked(False)
        self.restart()

    def auto_login(self):
        # Drive the same click/keyboard paths as a person; never call authentication directly.
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtTest import QTest

        if self.root.property("stage") == "desktop":
            if self.auto_step >= 5:
                self.shut_down()
                return
            if self.auto_step == 4:
                self.log_off()
                return
            self.switch_user()
            self.auto_timer.start(600)
            return
        names = ("Alex", "Alex", "Taylor", "Alex", "Taylor")
        name = names[self.auto_step]
        self.fail.setChecked(self.auto_step == 0)
        self.auto_step += 1

        def find(item):
            if item.objectName() == "userTile-" + name and item.isVisible():
                return item
            for child in item.childItems():
                result = find(child)
                if result is not None:
                    return result
            return None

        tile = find(self.root)
        if tile is None:
            self.log_event("scenario-error", reason="missing user tile")
            self.automating = False
            self.stop_recording()
            return
        self.activateWindow()
        self.preview.setFocus()
        QTest.mouseClick(self.preview, Qt.LeftButton, pos=tile.mapToScene(QPointF(30, 30)).toPoint())
        QTest.keyClicks(self.preview, "test-only")
        QTest.keyClick(self.preview, Qt.Key_Return)

    def record(self):
        if self.recorder.isActive():
            self.stop_recording()
            return
        folder = QFileDialog.getExistingDirectory(self, "Save flow recording")
        if folder:
            self.start_recording(Path(folder) / time.strftime("luna-flow-%Y%m%d-%H%M%S"))

    def start_recording(self, output):
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=False)
        (self.output / "frames").mkdir()
        self.frames = []
        self.log_event("recording-started")
        self.recorder.start()
        self.buttons["Record…"].setText("Stop recording")

    def record_frame(self):
        path = self.output / "frames" / f"{len(self.frames):06d}.png"
        if not self.preview.grabFramebuffer().save(str(path)):
            self.log_event("recording-error", reason="frame save failed")
            self.recorder.stop()
            return
        self.frames.append({"file": str(path.relative_to(self.output)), "seconds": time.monotonic() - self.started})

    def stop_recording(self):
        if not self.recorder.isActive():
            return
        self.record_frame()
        self.recorder.stop()
        self.buttons["Record…"].setText("Record…")
        self.log_event("recording-stopped")
        manifest = {
            "kind": "simulated-flow",
            "events": self.events,
            "frames": self.frames,
            "limits": [
                "QML boot preview, not Plymouth",
                "Mock authentication",
                "Desktop snapshot and simulated 500ms fade",
            ],
        }
        (self.output / "events.json").write_text(json.dumps(manifest, indent=2))
        entries = []
        for index, frame in enumerate(self.frames):
            entries.append(f"file '{frame['file']}'")
            if index + 1 < len(self.frames):
                entries.append(f"duration {self.frames[index + 1]['seconds'] - frame['seconds']:.6f}")
        (self.output / "frames.txt").write_text("\n".join(entries) + "\n")
        if shutil.which("ffmpeg"):
            self.encoder = QProcess(self)
            self.encoder.setWorkingDirectory(str(self.output))
            self.encoder.setStandardErrorFile(str(self.output / "encoding.log"))
            self.encoder.finished.connect(
                lambda code, status: self.status.setText(
                    f"Recording saved to {self.output}"
                    if code == 0
                    else f"Video encoding failed; frames and events saved in {self.output}"
                )
            )
            self.encoder.start(
                "ffmpeg",
                [
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    "frames.txt",
                    "-vf",
                    "fps=20",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "flow.mp4",
                ],
            )
        else:
            self.status.setText(f"Frames and events saved in {self.output}; install ffmpeg to encode video.")

    def closeEvent(self, event):
        self.automating = False
        self.auto_timer.stop()
        self.boot.stop()
        self.loading.stop()
        self.stop_recording()
        if self.capture and self.capture.state() != QProcess.NotRunning:
            self.capture.terminate()
            self.capture.waitForFinished(1000)
        if self.encoder and self.encoder.state() != QProcess.NotRunning:
            self.encoder.waitForFinished(5000)
        super().closeEvent(event)
