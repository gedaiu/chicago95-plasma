#!/usr/bin/env python3
"""Record the simulated flow and test screen handoff in an isolated real KWin/Plasma session.

Run: python tests/record_login_flow.py --output /tmp/luna-flow-run
No PAM authentication, reboot, logout, or changes to the current desktop.
"""

import argparse
import ast
import importlib.machinery
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "lib"), str(REPO / "luna/lib"), str(REPO / "tests")]


def mark(work, name, **details):
    event = {"event": name, "monotonic": time.monotonic(), **details}
    (work / f"{name}.json").write_text(json.dumps(event))


def wait_for(work, name, process=None, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        path = work / f"{name}.json"
        if path.exists():
            return json.loads(path.read_text())
        if process and process.poll() is not None:
            raise RuntimeError(f"{name}: child exited with {process.returncode}")
        time.sleep(0.05)
    raise RuntimeError(f"Timed out waiting for {name}")


def capture(work, name):
    subprocess.run(
        ["spectacle", "-b", "-n", "-f", "-o", str(work / f"{name}.png")],
        check=True,
        timeout=15,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    mark(work, name)


def worker(work, role):
    from login_preview import login_context
    from PySide6.QtCore import QPointF, Qt, QTimer, QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQuick import QQuickView
    from PySide6.QtTest import QTest

    app = QGuiApplication([])
    app.setApplicationName("ksplashqml" if role == "loading" else f"luna-test-{role}")
    app.setDesktopFileName(app.applicationName())
    view = QQuickView()
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(800, 600)
    context = login_context(
        REPO / "sddm/Chicago95Plasma", user="Alex", users=("Alex", "Sam", "Taylor"), loginStyle="luna", previewMode=True
    )
    for name, value in context.items():
        view.rootContext().setContextProperty(name, value)
    source = {"boot": "splash/LunaSplash.qml", "greeter": "sddm/LunaLogin.qml", "loading": "splash/LunaWelcome.qml"}[
        role
    ]
    view.setSource(QUrl.fromLocalFile(str(REPO / "luna" / source)))
    assert not view.errors(), [error.toString() for error in view.errors()]
    root = view.rootObject()
    if role == "greeter":
        for key, value in [
            ("greeter", context["sddm"]),
            ("users", context["userModel"]),
            ("sessions", context["sessionModel"]),
            ("theme", context["config"]),
        ]:
            root.setProperty(key, value)
    if role == "loading":
        auth = wait_for(work, "authentication-succeeded")
        root.setProperty("userName", auth["user"])
        root.setProperty("branding", {"previewMode": True})
    painted = [False]

    def first_frame():
        if not painted[0]:
            painted[0] = True
            mark(work, role + "-painted")

    view.frameSwapped.connect(first_frame)
    view.showFullScreen()

    def finish_if_requested():
        if (work / (role + "-close")).exists():
            view.close()
            app.quit()

    timer = QTimer()
    timer.timeout.connect(finish_if_requested)
    timer.start(25)
    if role == "greeter":
        attempts = []

        def authenticate(user, session):
            attempts.append(user)
            if len(attempts) == 1:
                mark(work, "authentication-failed", user=user)
                context["sddm"].loginFailed.emit()
                QTimer.singleShot(700, submit)
            else:
                mark(work, "authentication-succeeded", user=user)
                context["sddm"].loginSucceeded.emit()

        context["sddm"].loginAttempted.connect(authenticate)

        def submit():
            def find(item):
                if item.objectName() == "userTile-Taylor":
                    return item
                for child in item.childItems():
                    result = find(child)
                    if result is not None:
                        return result
                return None

            tile = find(root)
            QTest.mouseClick(view, Qt.LeftButton, pos=tile.mapToScene(QPointF(30, 30)).toPoint())
            for key in (Qt.Key_T, Qt.Key_E, Qt.Key_S, Qt.Key_T):
                QTest.keyClick(view, key)
            QTest.keyClick(view, Qt.Key_Return)

        QTimer.singleShot(700, submit)
    app.exec()


def controller(work):
    processes = []
    logs = []

    def start(role):
        log = (work / f"{role}.log").open("w")
        logs.append(log)
        process = subprocess.Popen(
            [sys.executable, __file__, "--output", str(work), "--worker", role], stdout=log, stderr=log
        )
        processes.append(process)
        return process

    try:
        boot = start("boot")
        wait_for(work, "boot-painted", boot)
        capture(work, "boot-frame")
        time.sleep(0.37)
        capture(work, "boot-motion-frame")
        greeter = start("greeter")
        wait_for(work, "greeter-painted", greeter)
        (work / "boot-close").touch()
        wait_for(work, "authentication-failed", greeter)
        wait_for(work, "authentication-succeeded", greeter)
        splash_log = (work / "loading.log").open("w")
        logs.append(splash_log)
        splash = subprocess.Popen(
            ["ksplashqml", "--nofork", "chicago95.splashscreen"], stdout=splash_log, stderr=splash_log
        )
        processes.append(splash)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            probe = subprocess.run(
                ["gdbus", "introspect", "--session", "--dest", "org.kde.KSplash", "--object-path", "/KSplash"],
                capture_output=True,
                check=False,
            )
            if probe.returncode == 0:
                break
            if splash.poll() is not None:
                raise RuntimeError("KSplash exited before ready")
            time.sleep(0.05)
        else:
            raise RuntimeError("KSplash did not register")
        capture(work, "loading-painted")
        (work / "greeter-close").touch()
        mark(work, "desktop-start-requested")
        log = (work / "plasmashell.log").open("w")
        logs.append(log)
        plasma = subprocess.Popen(["plasmashell", "--no-respawn"], stdout=log, stderr=log)
        processes.append(plasma)
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            probe = subprocess.run(
                [
                    "gdbus",
                    "call",
                    "--session",
                    "--dest",
                    "org.kde.plasmashell",
                    "--object-path",
                    "/PlasmaShell",
                    "--method",
                    "org.kde.PlasmaShell.evaluateScript",
                    "print(JSON.stringify({panels: panels().length, desktops: desktops().length}));",
                ],
                capture_output=True,
                check=False,
                text=True,
                timeout=3,
            )
            if probe.returncode == 0:
                try:
                    ready = json.loads(ast.literal_eval(probe.stdout)[0])
                    if ready["panels"] > 0 and ready["desktops"] > 0:
                        break
                except (ValueError, SyntaxError, KeyError, TypeError):
                    pass
            if plasma.poll() is not None:
                raise RuntimeError("plasmashell exited before ready")
            time.sleep(0.1)
        else:
            raise RuntimeError("desktop readiness timed out")
        mark(work, "desktop-ready", **ready)
        capture(work, "loading-frame")
        mark(work, "loading-close-requested")
        # Match startplasma's startup stages; Plasma supplies its desktop stage.
        for stage in ("startPlasma", "kcminit", "ksmserver"):
            subprocess.run(
                [
                    "gdbus",
                    "call",
                    "--session",
                    "--dest",
                    "org.kde.KSplash",
                    "--object-path",
                    "/KSplash",
                    "--method",
                    "org.kde.KSplash.setStage",
                    stage,
                ],
                capture_output=True,
                check=False,
                timeout=3,
            )
        splash.wait(timeout=10)
        capture(work, "fade-frame")
        time.sleep(0.8)
        capture(work, "desktop-frame")
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        for log in logs:
            log.close()


def preview_record(work):
    from login_flow import FlowTestDialog
    from PySide6.QtCore import QProcess, QTimer
    from PySide6.QtWidgets import QApplication

    loader = importlib.machinery.SourceFileLoader("flow_panel", str(REPO / "bin/chicago95-control-panel"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    panel = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = panel
    loader.exec_module(panel)
    app = QApplication([])
    preview = panel.LogOnPreview(interactive=True)
    preview.refresh({"LOGIN_STYLE": "luna", "COMPANY": "Microsoft", "BANNER_TEXT": ""})
    dialog = FlowTestDialog(preview, REPO / "luna", desktop_image=work / "desktop-frame.png")
    dialog.show()
    dialog.start_recording(work / "recording")
    dialog.run_scenario()

    def done():
        if (
            not dialog.automating
            and not dialog.recorder.isActive()
            and (dialog.encoder is None or dialog.encoder.state() == QProcess.NotRunning)
        ):
            dialog.close()
            app.quit()

    timer = QTimer()
    timer.timeout.connect(done)
    timer.start(100)
    expired = []
    QTimer.singleShot(45000, lambda: (expired.append(True), app.quit()))
    app.exec()
    dialog.close()
    assert not expired, "flow recording timed out"
    assert any(event["event"] == "scenario-complete" for event in dialog.events), "scenario did not finish"
    assert (work / "recording/flow.mp4").exists(), "recording failed"


def validate_flow(work):
    order = [
        "boot-painted",
        "greeter-painted",
        "authentication-failed",
        "authentication-succeeded",
        "loading-painted",
        "desktop-start-requested",
        "desktop-ready",
        "loading-close-requested",
        "desktop-frame",
    ]
    events = [wait_for(work, name, timeout=0.1) for name in order]
    assert all(b["monotonic"] > a["monotonic"] for a, b in zip(events, events[1:], strict=False)), events
    log = (work / "kwin-flow-session.log").read_text()
    assert "FLOW_LOGIN_FADE_BEGIN" in log, "KWin did not recognize/fade the loading screen"
    from PIL import Image, ImageChops

    for first, second in [("boot-frame", "boot-motion-frame"), ("loading-frame", "desktop-frame")]:
        assert ImageChops.difference(
            Image.open(work / f"{first}.png").convert("RGB"), Image.open(work / f"{second}.png").convert("RGB")
        ).getbbox(), (first, second)
    # Exclude the clock/cursor: the upper-left background must contain a real
    # intermediate blend, not merely a different window at the end.
    fade = Image.open(work / "fade-frame.png").convert("RGB").crop((0, 0, 100, 60))
    for name in ("loading-frame", "desktop-frame"):
        endpoint = Image.open(work / f"{name}.png").convert("RGB").crop((0, 0, 100, 60))
        assert ImageChops.difference(fade, endpoint).getbbox(), "No intermediate desktop fade frame captured"
    report = {
        "passed": True,
        "events": events,
        "fade": "KWin login effect invoked; intermediate blend captured",
        "configured_fade_ms": int(re.search(r"FLOW_LOGIN_FADE_BEGIN\s+(\d+)", log)[1]),
        "elapsed_ms": {
            event["event"]: round((event["monotonic"] - events[0]["monotonic"]) * 1000, 1) for event in events
        },
        "limits": [
            "QML boot, not Plymouth",
            "Mock SDDM authentication",
            "Native KSplash uses the test account; multi-user identity handoff is simulated",
            "Controlled handoff, not real PAM/session startup",
            "No XP timing reference comparison",
            "Screenshot capture adds diagnostic delays; these are not XP target timings",
        ],
    }
    (work / "integration.json").write_text(json.dumps(report, indent=2))
    return report


def run(work, reuse_baseline=None):
    from plasma_session import desktop_session, run_session

    work.mkdir(parents=True, exist_ok=False)
    baseline = reuse_baseline.resolve() if reuse_baseline else work / "baseline"
    if not reuse_baseline:
        baseline.mkdir()
        desktop_session(
            "luna",
            baseline,
            windows=[],
            launchers=0,
            tray_icons=0,
            components=("splash",),
            settings=(("ANIM_SESSION", "fade"), ("ANIM_SPEED", "1")),
        )
    # Use the installed disposable desktop; no user services/autostarts are copied.
    effect = baseline / "home/.local/share/kwin/effects/login"
    shutil.copytree("/usr/share/kwin/effects/login", effect, dirs_exist_ok=True)
    source = effect / "contents/code/main.js"
    source.write_text(
        source.read_text().replace(
            "fadeOut: function (window) {",
            'fadeOut: function (window) { print("FLOW_LOGIN_FADE_BEGIN", loginEffect.duration);',
        )
    )
    source.write_text(
        source.read_text().replace(
            "closed: function (window) {",
            'closed: function (window) { print("FLOW_WINDOW_CLOSED", window.windowClass);',
        )
    )
    session = work / "flow-session.sh"
    session.write_text(
        "#!/bin/sh\nexec " + shlex.join([sys.executable, __file__, "--output", str(work), "--controller"]) + "\n"
    )
    env = {
        **os.environ,
        "SETUP_OS_RELEASE": "/dev/null",
        "HOME": str(baseline / "home"),
        "XDG_RUNTIME_DIR": str(baseline / "run"),
        "XDG_CONFIG_HOME": str(baseline / "home/.config"),
        "XDG_DATA_HOME": str(baseline / "home/.local/share"),
        "QT_QPA_PLATFORM": "wayland",
        "QT_FORCE_STDERR_LOGGING": "1",
        "QT_LOGGING_RULES": "kwin*.debug=true;js.debug=true;org.kde.plasma.ksplashqml.debug=true",
        "KWIN_COMPOSE": "O2",
        "XDG_SESSION_TYPE": "wayland",
        "XDG_CURRENT_DESKTOP": "KDE",
    }
    for name in ("DBUS_SESSION_BUS_ADDRESS", "WAYLAND_DISPLAY", "DISPLAY"):
        env.pop(name, None)
    run_session(work, session, env, (800, 600))
    validate_flow(work)
    subprocess.run(
        [sys.executable, __file__, "--output", str(work), "--preview-record"],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        check=True,
        timeout=60,
    )
    print(work / "integration.json")
    print(work / "recording/flow.mp4")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reuse-baseline", type=Path)
    parser.add_argument("--worker", choices=["boot", "greeter", "loading"])
    parser.add_argument("--controller", action="store_true")
    parser.add_argument("--preview-record", action="store_true")
    args = parser.parse_args()
    work = args.output.resolve()
    if args.worker:
        worker(work, args.worker)
    elif args.controller:
        controller(work)
    elif args.preview_record:
        preview_record(work)
    else:
        run(work, args.reuse_baseline)
