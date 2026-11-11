"""Runs eslint's fixes and prettier over QML JavaScript libraries.

Their leading directives, `.pragma library` and any `.import "other.js" as Name`, are not valid JavaScript, so
they are set aside while the rest is formatted.

python3 tests/tools_prettier_pragma.py check|write PRETTIER_COMMAND FILE...
"""

import json
import shlex
import subprocess
import sys

PRAGMA = ".pragma library"
ESLINT_STDIN = ["npx", "eslint", "--stdin", "--stdin-filename", "pragma.js", "--fix-dry-run", "--format", "json"]


def enforce(condition, message):
    if not condition:
        sys.exit(message)


def eslint_fixed(path, body, lines_before):
    report = json.loads(subprocess.run(ESLINT_STDIN, input=body, capture_output=True, text=True, check=False).stdout)
    problems = [f"{path}:{message['line'] + lines_before}: {message['message']}" for message in report[0]["messages"]]
    enforce(not problems, "\n".join(problems))
    return report[0].get("output", body)


def prettier_formatted(prettier_command, body):
    return subprocess.run(
        [*shlex.split(prettier_command), "--stdin-filepath", "pragma.js"],
        input=body,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def formatted(prettier_command, path):
    lines = open(path, encoding="utf-8").read().split("\n")
    enforce(lines[0] == PRAGMA, f"{path} does not start with {PRAGMA}")
    directives = next(index for index, line in enumerate(lines) if not line.startswith("."))
    body = "\n".join(lines[directives:])
    header = "\n".join(lines[:directives])
    return f"{header}\n\n{prettier_formatted(prettier_command, eslint_fixed(path, body, directives))}"


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
