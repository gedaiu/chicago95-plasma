#!/usr/bin/env python3
"""The Screen Saver tab's monitor pictures: every screensaver photographed once, at the monitor screen's size.

    python3 tests/render_screensaver_previews.py

runs each saver of bin/chicago95-screensaver, as Plasma would start it, in a headless KWin whose whole screen is
the size of the monitor's screen in the Control Panel, and saves data/screensaver-previews/<saver>.png.
Run it again after adding a saver or changing one's options.
"""

import importlib.machinery
import importlib.util
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent
sys.path[:0] = [str(TESTS), str(REPO / "lib")]

from PIL import Image, ImageStat  # noqa: E402
from plasma_session import link_user_assets, run_session  # noqa: E402

PICTURES = REPO / "data/screensaver-previews"
RUN_SECONDS = 4
SHOTS, SHOT_GAP_SECONDS = 3, 2  # savers that fade in and out are kept at their liveliest shot
SLOW_STARTERS = {"glmatrix": 12, "fliptext": 6, "deepstars": 6}  # seconds until their screen fills
# The Blue Screen saver cycles through many systems' crash screens; its picture shows the Windows one.
PICTURE_OPTIONS = {"bsod": ["--only", "windows"]}
SAVER = """import sys
from importlib.machinery import SourceFileLoader
saver = SourceFileLoader("saver", sys.argv[1]).load_module()
name, extra = sys.argv[2], sys.argv[3:]
saver.CATALOG[name] = saver.CATALOG[name]._replace(options=saver.CATALOG[name].options + extra)
sys.argv = [sys.argv[1], "--hack", name]
sys.exit(saver.main())
"""
SCRIPT = """#!/bin/bash
cd "$REPO"
shoot() {{
    python3 "$WORK/saver.py" bin/chicago95-screensaver "$@" >"$WORK/$1.log" 2>&1 &
    sleep "$SECONDS_FOR"
    for shot in $(seq {shots_per_saver}); do
        spectacle --background --nonotify --fullscreen --output "$WORK/$1-$shot.png" >>"$WORK/$1.log" 2>&1
        sleep {shot_gap}
    done
    kill %1
    wait
}}
{shots}
"""


def shot_line(name):
    seconds = SLOW_STARTERS.get(name, RUN_SECONDS)
    return f"SECONDS_FOR={seconds} shoot {name} {' '.join(PICTURE_OPTIONS.get(name, []))}"


def load(name):
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), str(REPO / "bin" / name))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(module)
    return module


def main():
    savers = list(load("chicago95-screensaver").CATALOG)
    screen = load("chicago95-control-panel").MONITOR_SCREEN
    work = Path(tempfile.mkdtemp(prefix="c95-savers-", dir="/tmp"))  # short: Wayland's socket path is limited
    home, runtime = work / "home", work / "run"
    for folder in (home / ".config", runtime):
        folder.mkdir(parents=True, exist_ok=True)
    runtime.chmod(0o700)
    link_user_assets(home)
    (work / "saver.py").write_text(SAVER)
    (work / "savers.sh").write_text(
        SCRIPT.format(
            shots="\n".join(shot_line(name) for name in savers), shots_per_saver=SHOTS, shot_gap=SHOT_GAP_SECONDS
        )
    )
    environment = {
        "SETUP_OS_RELEASE": "/dev/null",
        "HOME": str(home),
        "PATH": os.environ["PATH"],
        "LANG": "en_US.UTF-8",
        "XDG_RUNTIME_DIR": str(runtime),
        "WORK": str(work),
        "REPO": str(REPO),
    }
    run_session(work, work / "savers.sh", environment, xwayland=True, screen=screen)
    PICTURES.mkdir(parents=True, exist_ok=True)
    missing = []
    for name in savers:
        shots = [Image.open(shot).convert("RGB") for shot in sorted(work.glob(f"{name}-*.png"))]
        if not shots:
            missing.append(name)
            continue
        liveliest = max(shots, key=lambda shot: sum(ImageStat.Stat(shot).mean))
        liveliest.resize(screen).save(PICTURES / f"{name}.png", optimize=True)
    if missing:
        sys.exit(f"no picture of {', '.join(missing)}; see the logs in {work}")
    shutil.rmtree(work, ignore_errors=True)
    print(f"{len(savers)} pictures in {PICTURES}")


if __name__ == "__main__":
    main()
