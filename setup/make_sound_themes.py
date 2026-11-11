#!/usr/bin/env python3
"""Builds the freedesktop sound themes in data/sound-themes/ from the original sound archives.

    python3 -I setup/make_sound_themes.py ~/Downloads/Windows98Sounds.zip ~/Downloads/WIN2000R_v2.7z

Each scheme folder becomes <Id>/index.theme plus stereo/<event>.ogg. Events a scheme lacks fall back
to Chicago95 through Inherits=. The output is committed; this only runs again when the sources change.
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / "data/sound-themes"

WINDOWS_98_EVENTS = {
    "startup": ["desktop-login"],
    "exit windows": ["desktop-logout", "system-shutdown"],
    "asterisk": ["dialog-information"],
    "exclamation": ["dialog-warning"],
    "critical stop": ["dialog-error"],
    "question": ["dialog-question"],
    "default sound": ["bell-window-system", "bell"],
    "beep": ["bell-terminal"],
    "empty recycle bin": ["trash-empty"],
    "maximize": ["window-maximized"],
    "minimize": ["window-minimized"],
    "restore down": ["window-unmaximized"],
    "restore up": ["window-unminimized"],
    "open program": ["window-new"],
    "close program": ["window-close"],
    "menu popup": ["menu-popup"],
    "menu command": ["menu-click"],
}

WINDOWS_2000_EVENTS = {
    "windows logon": ["desktop-login"],
    "windows logoff": ["desktop-logout", "system-shutdown"],
    "ding": ["bell-window-system", "bell"],
    "chord": ["dialog-error", "dialog-warning", "dialog-information"],
    "recycle": ["trash-empty"],
    "start": ["menu-click"],
    "notify": ["message-new-instant"],
    "ta da": ["complete-copy"],
}

# The Plus! packs spell some events differently; the long Jungle takes win over its short ones.
EVENT_ALIASES = {
    "windows start": "startup",
    "windows exit": "exit windows",
    "default": "default sound",
    "error": "program error",
    "recycle": "empty recycle bin",
    "open": "open program",
    "close": "close program",
}


def event_name(wav_name: str, scheme: str) -> str:
    stem = Path(wav_name).stem.lower()
    stem = re.sub(r"\s*remastered$", "", stem)
    stem = stem.removeprefix(scheme.lower()).strip()
    return EVENT_ALIASES.get(stem, stem) if scheme != "Windows 2000" else stem


def theme_id(scheme: str) -> str:
    compact = re.sub(r"[^A-Za-z0-9]", "", scheme.replace("60's", "60s"))
    return compact if scheme.startswith("Windows") else f"Plus98-{compact}"


def transcode(source: Path, destination: Path):
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-i", str(source), "-c:a", "libvorbis", "-q:a", "4", str(destination)],
        check=True,
    )


def build_theme(scheme: str, wavs: list[Path], events: dict[str, list[str]]):
    target = OUTPUT / theme_id(scheme)
    shutil.rmtree(target, ignore_errors=True)
    (target / "stereo").mkdir(parents=True)
    (target / "index.theme").write_text(
        f"[Sound Theme]\nName={scheme}\nInherits=Chicago95\nDirectories=stereo\n\n[stereo]\nOutputProfile=stereo\n"
    )
    by_event = {event_name(wav.name, scheme): wav for wav in sorted(wavs, key=lambda wav: len(wav.name))}
    for windows_event, wav in by_event.items():
        for freedesktop_event in events.get(windows_event, []):
            transcode(wav, target / "stereo" / f"{freedesktop_event}.ogg")


def extract(archive: Path, into: Path):
    subprocess.run(["7z", "x", "-y", f"-o{into}", str(archive)], check=True, stdout=subprocess.DEVNULL)


def main(windows_98_zip: str, windows_2000_7z: str):
    with tempfile.TemporaryDirectory() as unpacked_98, tempfile.TemporaryDirectory() as unpacked_2000:
        extract(Path(windows_98_zip), Path(unpacked_98))
        extract(Path(windows_2000_7z), Path(unpacked_2000))
        for folder in sorted(path for path in Path(unpacked_98).iterdir() if path.is_dir()):
            scheme = "Leonardo da Vinci" if folder.name == "Leonardo Da Vinci" else folder.name
            build_theme(scheme, list(folder.glob("*.wav")), WINDOWS_98_EVENTS)
        build_theme("Windows 2000", list(Path(unpacked_2000).rglob("*.wav")), WINDOWS_2000_EVENTS)


if __name__ == "__main__":
    main(*sys.argv[1:3])
