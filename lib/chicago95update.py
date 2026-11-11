"""Is a newer Chicago95 for Plasma published? Setup writes the commit it installed (COMMIT=) into
~/.config/chicago95/setup.conf; one `git ls-remote` asks the repository's origin for the tip of its branch.
The answer is cached for a day in ~/.cache/chicago95/update-check.json, so Clippy's daily check and the
Control Panel's Updates page share it."""
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal

PROJECT_ORIGIN = "https://github.com/gedaiu/chicago95-plasma.git"
BRANCH = "main"
GIT = "git"
CACHE_FILE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "chicago95/update-check.json"
CHECK_EVERY = timedelta(days=1)
GIT_TIMEOUT_MS = 20_000


def latest_commit(ls_remote_output):
    """The sha of the first ref line, or nothing."""
    first_line = ls_remote_output.strip().splitlines()[:1]
    return first_line[0].split()[0] if first_line else ""


def check_result(installed, latest, checked_at, error=""):
    return {
        "installed": installed,
        "latest": latest,
        "checked": checked_at.isoformat(),
        "available": bool(installed and latest and installed != latest),
        "error": error,
    }


def short_version(commit):
    return commit[:7] if commit else "unknown"


def read_cache(path):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else {}


def write_cache(path, result):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result))


def is_due(cache, now):
    if not cache.get("checked"):
        return True
    return now - datetime.fromisoformat(cache["checked"]) >= CHECK_EVERY


def origin_of(repo, git=GIT):
    """The repository's origin URL; the project's own when the folder has none (a download, not a clone)."""
    try:
        found = subprocess.run([git, "-C", repo, "remote", "get-url", "origin"], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return PROJECT_ORIGIN
    return found.stdout.strip() if found.returncode == 0 and found.stdout.strip() else PROJECT_ORIGIN


def utc_now():
    return datetime.now(timezone.utc)


class UpdateCheck(QObject):
    """One check: asks the origin, writes the cache, and reports the result (check_result) through `finished`."""

    finished = Signal(dict)

    def __init__(self, settings, cache_path=CACHE_FILE, git=None, now=utc_now, parent=None):
        super().__init__(parent)
        self.settings, self.cache_path, self.git, self.now = settings, Path(cache_path), git or GIT, now
        self.process = QProcess(self)
        self.process.finished.connect(self.report)
        self.process.errorOccurred.connect(lambda _error: self.report(-1, QProcess.ExitStatus.CrashExit))
        self.reported = False

    def start(self):
        origin = origin_of(self.settings.get("REPO", ""), self.git)
        self.process.start(self.git, ["ls-remote", origin, f"refs/heads/{BRANCH}"])

    def report(self, exit_code, _status):
        if self.reported:
            return
        self.reported = True
        output = bytes(self.process.readAllStandardOutput()).decode(errors="replace")
        error = "" if exit_code == 0 else (bytes(self.process.readAllStandardError()).decode(errors="replace").strip() or f"git exited with {exit_code}")
        result = check_result(self.settings.get("COMMIT", ""), latest_commit(output) if exit_code == 0 else "", self.now(), error)
        write_cache(self.cache_path, result)
        self.finished.emit(result)


def read_settings(path):
    """setup.conf's KEY=value lines (data, never executed)."""
    path = Path(path)
    if not path.exists():
        return {}
    lines = [line for line in path.read_text().splitlines() if "=" in line and not line.startswith("#")]
    return dict(line.split("=", 1) for line in lines)


def update_message(result):
    return (
        f"A newer Chicago95 for Plasma is available ({short_version(result['latest'])}; "
        f"you have {short_version(result['installed'])}).\n\nOpen Control Panel, Updates to install it."
    )


class DailySchedule(QObject):
    """Checks once a day from a resident tool: tick() runs a check when the cache is a day old, and
    on_update(result) is called when a newer version is published."""

    def __init__(self, settings_path, on_update, cache_path=CACHE_FILE, git=None, now=utc_now, parent=None):
        super().__init__(parent)
        self.settings_path, self.on_update, self.cache_path, self.git, self.now = settings_path, on_update, cache_path, git, now
        self.check = None

    def tick(self):
        if self.check is not None or not is_due(read_cache(self.cache_path), self.now()):
            return
        self.check = UpdateCheck(read_settings(self.settings_path), self.cache_path, git=self.git, now=self.now, parent=self)
        self.check.finished.connect(self.handle)
        self.check.start()

    def handle(self, result):
        if self.check is not None:
            self.check.deleteLater()
            self.check = None
        if result["available"]:
            self.on_update(result)
