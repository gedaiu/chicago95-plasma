"""Runs a QML JavaScript library (.pragma library) in a bare JS engine, so its pure functions get unit tests.

The engine needs a Qt application to exist; tests get it from the qt_app fixture."""

from PySide6.QtQml import QJSEngine


def load_js_library(path):
    source = "\n".join(line for line in path.read_text().splitlines() if not line.startswith(".pragma"))
    engine = QJSEngine()
    result = engine.evaluate(source, str(path))
    assert not result.isError(), result.toString()
    return engine


def call(engine, function_name, *arguments):
    return engine.globalObject().property(function_name).call(list(arguments)).toVariant()
