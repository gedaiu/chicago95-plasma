"""Runs prettier over QML JavaScript libraries, whose first line `.pragma library` prettier cannot parse.

    python3 tests/tools_prettier_pragma.py check|write PRETTIER_COMMAND FILE...
"""

import shlex
import subprocess
import sys

PRAGMA = ".pragma library"


def formatted(prettier_command, path):
    lines = open(path, encoding="utf-8").read().split("\n", 1)
    enforce(lines[0] == PRAGMA, f"{path} does not start with {PRAGMA}")
    body = subprocess.run(
        [*shlex.split(prettier_command), "--stdin-filepath", "pragma.js"],
        input=lines[1],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return f"{PRAGMA}\n\n{body}"


def enforce(condition, message):
    if not condition:
        sys.exit(message)


def main(mode, prettier_command, paths):
    wanted = {path: formatted(prettier_command, path) for path in paths}
    stale = [path for path, text in wanted.items() if text != open(path, encoding="utf-8").read()]
    if mode == "write":
        for path in stale:
            open(path, "w", encoding="utf-8").write(wanted[path])
        return
    enforce(not stale, "needs prettier: " + " ".join(stale))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
