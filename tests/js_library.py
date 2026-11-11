"""Runs a QML JavaScript library (.pragma library) in a bare JS engine, so its pure functions get unit tests.

A library's `.import "other.js" as Name` lines load that library under Name, as QML does, so libraries can
share their constants. The engine needs a Qt application to exist; tests get it from the qt_app fixture."""

import re

from PySide6.QtQml import QJSEngine

IMPORT = re.compile(r'^\.import\s+"([^"]+\.js)"\s+as\s+(\w+)\s*$')
TOP_LEVEL_NAME = re.compile(r"^(?:function|const|let|var)\s+(\w+)", re.MULTILINE)


def library_source(path):
    """The library's code with its directives turned into plain JavaScript: each import becomes an object."""
    lines = []
    for line in path.read_text().splitlines():
        imported = IMPORT.match(line)
        if imported:
            file_name, alias = imported.groups()
            source = library_source(path.parent / file_name)
            names = ", ".join(TOP_LEVEL_NAME.findall(source))
            lines.append(f"var {alias} = (function () {{\n{source}\nreturn {{ {names} }};\n}})();")
        elif not line.startswith(".pragma"):
            lines.append(line)
    return "\n".join(lines)


def load_js_library(path):
    engine = QJSEngine()
    result = engine.evaluate(library_source(path), str(path))
    assert not result.isError(), result.toString()
    return engine


def call(engine, function_name, *arguments):
    return engine.globalObject().property(function_name).call(list(arguments)).toVariant()
