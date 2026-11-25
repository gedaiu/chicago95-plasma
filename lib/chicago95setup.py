"""Setup's bookkeeping, for the parts of Setup written in Python (lib/chicago95appliers.py).

What setup/steps.sh does with run, kconf, record, backup, put_file, put_tree, show_copy and kwin_rule, done the same
way: the same lines in the Setup log (a dry run's "would:" lines), the same entries in the manifest uninstall.sh
reads, the same backups. Standard library only: Setup runs on machines without PySide6.
"""

import filecmp
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if not (REPO / "setup/settings.keys").exists():  # installed in ~/.local/lib/chicago95: the checkout Setup ran from
    REPO = Path(os.environ.get("REPO", REPO))


def settings_keys(repo):
    """Every key of setup.conf: setup/settings.keys and the animation events of setup/animations.conf."""
    listed = [line for line in (repo / "setup/settings.keys").read_text().splitlines() if not line.startswith("#")]
    events = re.findall(r"^EVENT\|([^|]*)\|", (repo / "setup/animations.conf").read_text(), re.MULTILINE)
    return [key for line in listed for key in line.split()] + events


def animation_events(repo):
    return re.findall(r"^EVENT\|([^|]*)\|", (repo / "setup/animations.conf").read_text(), re.MULTILINE)


def read_key_values(path):
    """KEY=value lines, read as data; later lines win."""
    pairs = (line.split("=", 1) for line in Path(path).read_text().splitlines() if "=" in line)
    return {key: value for key, value in pairs if key and not key.startswith("#")}


@dataclass
class Choices:
    """The SETUP_* values of a Setup run, without the prefix. A key that is absent is unset; one set to "" is empty."""

    values: dict = field(default_factory=dict)

    def __getitem__(self, key):
        return self.values.get(key, "")

    def __setitem__(self, key, value):
        self.values[key] = value

    def __contains__(self, key):
        return key in self.values

    def get(self, key, default=""):
        """${SETUP_KEY:-default}: the default when the value is unset or empty."""
        return self.values.get(key) or default

    def unset_or(self, key, default):
        """${SETUP_KEY-default}: the default only when the value is unset."""
        return self.values.get(key, default)


def apply_look(choices, repo, look):
    """setup/steps.sh's apply_look: every KEY=value of looks/<look>.conf; its repository paths made absolute."""
    choices["LOOK"] = look
    for key, value in read_key_values(repo / f"looks/{look}.conf").items():
        if key in ("SPLASH_IMAGE", "BACKGROUND_IMAGE") and "/" in value:
            value = str(repo / value)
        choices[key] = value


def load_settings(choices, repo, path):
    """setup/steps.sh's load_settings: the file's look first, then its own values over it."""
    saved = read_key_values(path)
    if saved.get("LOOK") and (repo / f"looks/{saved['LOOK']}.conf").exists():
        apply_look(choices, repo, saved["LOOK"])
    known = {*settings_keys(repo), "COMPONENTS", "CLASSIC_EFFECTS"}
    for key, value in saved.items():
        if key in known:
            choices[key] = value
    classic_effects_as_animations(choices, repo)


def classic_effects_as_animations(choices, repo):
    """The old single "no animations" choice, as every animation event turned off."""
    events = animation_events(repo)
    if choices["CLASSIC_EFFECTS"] != "yes" or any(choices[event] for event in events):
        return
    for event in events:
        choices[event] = {"ANIM_SPEED": "0", "ANIM_WOBBLY": "no"}.get(event, "none")


def detect_screen(environment):
    """setup/detect.sh's detect_screen: the first enabled output's logical size and scale, from kscreen-doctor."""
    width, height, scale = "2560", "1440", "1"
    if environment.get("WAYLAND_DISPLAY") or environment.get("DISPLAY"):
        dump = run_quietly(["kscreen-doctor", "-o"])
        dump = re.sub(r"\x1b\[[0-9;]*m", "", dump)
        enabled = dump[dump.find("enabled") :] if "enabled" in dump else ""
        geometry = re.search(r"Geometry:\s*\S+\s+(\d+)x(\d+)", enabled)
        found_scale = re.search(r"Scale:\s*([0-9.]+)", enabled)
        if geometry:
            width, height = geometry.groups()
        if found_scale:
            scale = found_scale.group(1)
    return width, height, scale


def run_quietly(command, **options):
    try:
        return subprocess.run(command, capture_output=True, text=True, check=False, **options).stdout
    except OSError:
        return ""


def newest_firefox_profile(home):
    profiles = sorted(
        (path.stat().st_mtime, path.parent) for path in (home / ".mozilla/firefox").glob("*/prefs.js") if path.exists()
    )
    return str(profiles[-1][1]) if profiles else ""


def scale_dpi(scale):
    return str(int(96 * float(scale) + 0.5))


def resolve_choices(settings_path, repo, home, environment):
    """The values install.sh --yes --settings=FILE gives the steps: the 1995 look underneath, the saved choices and
    their look over it, the machine's screen and programs, and the defaults Setup's screens would offer."""
    choices = Choices()
    apply_look(choices, repo, "1995")
    choices["ANIM_MINIMIZE"] = choices["ANIM_MAXIMIZE"] = ""  # unchosen: the animations table decides
    saved = home / ".config/chicago95/setup.conf"
    if saved.exists():
        load_settings(choices, repo, saved)
    choices["IN_PLASMA"] = "1" if "KDE" in environment.get("XDG_CURRENT_DESKTOP", "").split(":") else "0"
    choices["WIDTH"], choices["HEIGHT"], choices["SCALE"] = detect_screen(environment)
    choices["FIREFOX_PROFILE"] = newest_firefox_profile(home)
    choices["HAS_THUNAR"] = "1" if shutil.which("thunar") else "0"
    panel_chosen = choices["PANEL"]
    defaults = {
        "PANEL": "28",
        "EXPLORER": "thunar" if choices["HAS_THUNAR"] == "1" else "dolphin",
        "IDLE_MIN": "5",
        "CURSOR": "48" if float(choices["SCALE"]) > 1 else "32",
        "CLIPPY_AUTOSTART": "yes",
        "QUICK_LAUNCH": "auto",
        "TASK_GROUPING": "auto",
        "FONT": "MS W98 UI",
        "FONT_SCOPE": "everywhere",
        "START_TEXT": "Start",
        "SAVER": "deepstars",
    }
    for key, value in defaults.items():
        choices[key] = choices.get(key, value)
    if not panel_chosen and choices["PANEL"] == "28":
        choices["PANEL"] = default_panel_height(choices)
    load_settings(choices, repo, settings_path)
    choices["DPI"] = scale_dpi(choices["SCALE"])
    return choices


LUNA_PANEL_HEIGHT = "30"
AERO_PANEL_HEIGHT = "40"  # the Windows 7 superbar


def default_panel_height(choices):
    """At 120 DPI the reference Classic and Luna panels are 32–33 and 34 device pixels high, in whole logical pixels."""
    if re.fullmatch(r"1\.250*", choices.get("SCALE", "1")) and choices["TASKBAR_STYLE"] in ("classic", "luna"):
        return {"classic": "26", "luna": "27"}[choices["TASKBAR_STYLE"]]
    return {"luna": LUNA_PANEL_HEIGHT, "aero": AERO_PANEL_HEIGHT}.get(choices["TASKBAR_STYLE"], "28")


def js_string(text):
    """setup/steps.sh's js_string: a JavaScript string literal of the text."""
    return json.dumps(text)


def extension(path):
    return str(path).rsplit(".", 1)[-1]


class Setup:
    """One run's bookkeeping. With a report, what the shell needs back (flags, changed choices, the copy count) is
    written there for setup/steps.sh's python_applier to read."""

    def __init__(self, choices, *, repo, home, environment, report=None):
        self.choices = choices
        self.repo = Path(repo)
        self.home = Path(home)
        self.environment = environment
        self.dry_run = environment.get("SETUP_DRY_RUN", "0") == "1"
        self.log_path = environment.get("SETUP_LOG") or os.devnull
        self.plain = environment.get("UI_PLAIN", "1") == "1"
        self.state_dir = Path(environment.get("STATE_DIR") or self.home / ".local/share/chicago95")
        self.manifest = Path(environment.get("MANIFEST") or self.state_dir / "installed-files.txt")
        self.backup_dir = Path(environment.get("BACKUP_DIR") or self.state_dir / time.strftime("backup-%Y%m%d-%H%M%S"))
        self.copied = int(environment.get("COPIED") or 0)
        self.to_copy = int(environment.get("TO_COPY") or 0)
        flag_names = (
            "SHELL_CHANGED",
            "GLASS_EFFECT_CHANGED",
            "AERO_FRAME_CHANGED",
            "CAPTION_RELOAD",
            "TASKBAR_CHANGED",
            "START_MENU_CHANGED",
            "SHELL_MENU_DONE",
            "LOOK_STEP_DONE",
        )
        self.flags = {name: environment[name] for name in flag_names if environment.get(name)}
        self.changed_choices = {}
        self.statuses = []
        self.report = report

    # --- the log and the screen ---

    def log(self, line):
        with open(self.log_path, "a") as log:
            log.write(line + "\n")

    def short_path(self, path):
        path = str(path).removeprefix(f"{self.repo}/")
        return "~" + path[len(str(self.home)) :] if path.startswith(str(self.home)) else path

    def show_copy(self, source, dest):
        verb = "would-copy" if self.dry_run else "copied"
        self.log(f"{verb}: {source} -> {dest}")
        self.copied += 1
        if self.plain:
            print(f"   ({self.copied}/{self.to_copy}) {self.short_path(source)} → {self.short_path(dest)}", flush=True)

    def status(self, text):
        if self.report:
            self.statuses.append(text)
        elif self.plain:
            print(f"   {text}", flush=True)

    # --- commands ---

    def run(self, *command, to_log=False, quiet=False, input=None, environment=None):
        """setup/steps.sh's run: in a dry run the command is only listed in the log; otherwise it runs. True when it
        succeeded (a dry run always does)."""
        if self.dry_run:
            self.log("  would: " + " ".join(str(part) for part in command))
            return True
        return self.execute(*command, to_log=to_log, quiet=quiet, input=input, environment=environment)

    def execute(self, *command, to_log=False, quiet=False, input=None, environment=None):
        """A command that runs in a dry run too, as the steps' unguarded commands do."""
        output = open(self.log_path, "a") if to_log else subprocess.DEVNULL if quiet else None
        try:
            result = subprocess.run(
                [str(part) for part in command],
                stdout=output,
                stderr=subprocess.STDOUT if to_log else subprocess.DEVNULL if quiet else None,
                input=input,
                text=True,
                env={**os.environ, **(environment or {})},
                check=False,
            )
        except OSError:
            return False
        finally:
            if to_log:
                output.close()
        return result.returncode == 0

    def output_of(self, *command, environment=None):
        try:
            return subprocess.run(
                [str(part) for part in command],
                capture_output=True,
                text=True,
                env={**os.environ, **(environment or {})},
                check=False,
            ).stdout
        except OSError:
            return ""

    def succeeds(self, *command):
        try:
            return subprocess.run([str(part) for part in command], capture_output=True, check=False).returncode == 0
        except OSError:
            return False

    def kconf(self, file, group, key, *values):
        self.run("kwriteconfig6", "--file", file, "--group", group, "--key", key, *values)
        self.record(f"kconf:{file}:{group}:{key}")

    def kwin_reconfigure(self):
        self.run("gdbus", "call", "--session", "--dest", "org.kde.KWin", "--object-path", "/KWin", "--method",
                 "org.kde.KWin.reconfigure", quiet=True)  # fmt: skip

    def plasma_script(self, script):
        """Plasma's scripting interface; what it prints goes to the Setup log."""
        return self.execute(
            "gdbus", "call", "--session", "--dest", "org.kde.plasmashell", "--object-path", "/PlasmaShell",
            "--method", "org.kde.PlasmaShell.evaluateScript", script, to_log=True,
        )  # fmt: skip

    # --- files ---

    def installed_by_setup(self, entry):
        return self.manifest.is_file() and str(entry) in self.manifest.read_text().splitlines()

    def record(self, entry):
        if self.dry_run or self.installed_by_setup(entry):
            return
        self.manifest.parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest, "a") as manifest:
            manifest.write(f"{entry}\n")

    def backup(self, path):
        """The pre-install version; a file Setup put there earlier is not backed up."""
        path = Path(path)
        if not (path.exists() or path.is_symlink()) or self.dry_run or self.installed_by_setup(path):
            return
        dest = self.backup_dir / path.relative_to(self.home) if path.is_relative_to(self.home) else None
        if dest is None or dest.exists():
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        self.execute("cp", "-a", path, dest)

    def put_file(self, source, dest):
        self.backup(dest)
        self.run("mkdir", "-p", Path(dest).parent)
        if not (Path(source).exists() and Path(dest).exists() and os.path.samefile(source, dest)):
            self.run("cp", source, dest)
        self.record(dest)
        self.show_copy(source, dest)

    def put_tree(self, source, dest):
        self.backup(dest)
        self.run("rm", "-rf", dest)
        self.run("mkdir", "-p", Path(dest).parent)
        self.run("cp", "-r", source, dest)
        self.record(dest)
        for file in sorted(str(path) for path in Path(source).rglob("*") if path.is_file()):
            self.show_copy(file, f"{dest}/{Path(file).relative_to(source)}")

    def write_file(self, path, text):
        """A file the step writes itself (settings.js and the like): in a dry run, the tee setup/steps.sh lists."""
        if self.dry_run:
            self.run("tee", path)
            return
        Path(path).write_text(text)

    def substitute_home(self, *paths):
        """@HOME@ in the files installed from the repository, as this home's path."""
        if self.dry_run:
            return
        files = [path for root in map(Path, paths) for path in ([root] if root.is_file() else root.rglob("*"))]
        for file in (path for path in files if path.is_file()):
            try:
                text = file.read_text()
            except (UnicodeDecodeError, OSError):
                continue
            if "@HOME@" in text:
                file.write_text(text.replace("@HOME@", str(self.home)))

    def differs(self, source, dest):
        """setup/steps.sh's installed_differs: a file of the source missing or different at the destination."""
        source, dest = Path(source), Path(dest)
        if not source.is_dir():
            return not (dest.is_file() and filecmp.cmp(source, dest, shallow=False))
        return any(
            not (
                (dest / file.relative_to(source)).is_file()
                and filecmp.cmp(file, dest / file.relative_to(source), shallow=False)
            )
            for file in source.rglob("*")
            if file.is_file()
        )

    def kwin_rule(self, group, *lines):
        """Replaces or appends the group in kwinrulesrc and lists it in Order=; merged as text, because
        kwriteconfig6 drops every other group."""
        if self.dry_run:
            self.log(f"  would: write kwin rule [{group}]")
            return
        path = self.home / ".config/kwinrulesrc"
        self.backup(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        path.write_text(merged_kwin_rule(path.read_text(), group, lines))
        self.record(f"kwinrule:{group}")

    # --- what goes back to the shell ---

    def set_choice(self, key, value):
        self.choices[key] = value
        self.changed_choices[key] = value

    def flag(self, name, value="1"):
        self.flags[name] = value

    def write_report(self):
        if not self.report:
            return
        lines = [*(f"{name}={value}" for name, value in self.flags.items()), f"COPIED={self.copied}"]
        lines += [f"SETUP_{key}={value}" for key, value in self.changed_choices.items()]
        lines += [f"STATUS={text}" for text in self.statuses]
        Path(self.report).write_text("".join(f"{line}\n" for line in lines))


def merged_kwin_rule(text, group, lines):
    block = "[%s]\n%s\n" % (group, "\n".join(lines))
    pattern = re.compile(r"^\[%s\]\n(?:(?!\[).*\n?)*" % re.escape(group), re.M)
    text = pattern.sub("", text).rstrip("\n") + "\n\n" + block
    if "[General]" not in text:
        return "[General]\nOrder=%s\n\n" % group + text
    order = re.search(r"^Order=(.*)$", text, re.M)
    if not order:
        return text.replace("[General]\n", "[General]\nOrder=%s\n" % group, 1)
    names = [name for name in order.group(1).split(",") if name]
    if group not in names:
        names.append(group)
    return text[: order.start()] + "Order=" + ",".join(names) + text[order.end() :]
