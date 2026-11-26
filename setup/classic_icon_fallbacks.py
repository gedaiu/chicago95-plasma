"""Resolve optional ClassicOS-2000 icon theme parents against installed themes."""

import os
import re
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def repair(index):
    if index.parent.is_symlink() or index.is_symlink():
        return
    roots = [
        Path.home() / ".icons",
        Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "icons",
        *(
            Path(p) / "icons"
            for p in (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")
            if p
        ),
    ]
    optional = {
        "tango": ("tango",),
        "retrosmart-icon-theme": ("retrosmart-icon-theme",),
        "adwaita": ("adwaita", "Adwaita"),
    }
    original = index.read_bytes().decode()
    lines = original.splitlines(keepends=True)
    in_theme = False
    for i, line in enumerate(lines):
        if line.startswith("["):
            in_theme = line.strip() == "[Icon Theme]"
        match = re.fullmatch(r"(Inherits\s*=)([^\r\n]*)(\r?\n)?", line)
        if not (in_theme and match):
            continue
        parents = []
        for parent in match[2].split(","):
            candidates = optional.get(parent.strip())
            if candidates is None:
                parents.append(parent)
                continue
            for candidate in candidates:
                if any((root / candidate / "index.theme").is_file() for root in roots):
                    parents.append(candidate)
                    break
        lines[i] = match[1] + ",".join(parents) + (match[3] or "")
        break
    updated = "".join(lines)
    if updated != original:
        with TemporaryDirectory(dir=index.parent) as directory:
            replacement = Path(directory) / index.name
            replacement.write_bytes(updated.encode())
            replacement.chmod(index.stat().st_mode)
            replacement.replace(index)


if __name__ == "__main__":
    repair(Path(sys.argv[1]))
