#!/usr/bin/env python3
"""Draws the XP Plymouth screen's logo pictures (logo.png, logo@2x.png) with the user's branding: the wordmark the
boot screen shows (luna/qml/XpWordmark.qml) with their logo, name, company and edition, on Plymouth's black, at
the Plymouth layout's 1.85 units and twice that. Setup runs it at install time; without a name the committed
Windows XP pictures stay.

    branded_logo.py --out DIR --name NAME [--company TEXT] [--edition TEXT] [--logo FILE]
"""

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer, QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQuick import QQuickView  # noqa: E402

QML = Path(__file__).resolve().parents[1] / "qml"
WORDMARK_SCALE = 1.85
SCENE = """import QtQuick 2.15
import "%(qml)s"
Rectangle {
    color: "#000000"
    width: mark.width
    height: mark.height
    XpWordmark {
        id: mark
        unit: %(unit)s
        name: %(name)s
        company: %(company)s
        edition: %(edition)s
        logo: %(logo)s
        textColor: "#efefef"
    }
}
"""


def qml_string(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render(app, folder, unit, options):
    scene = folder / ".branded-logo.qml"
    scene.write_text(
        SCENE
        % {
            "qml": QML.as_uri(),
            "unit": unit,
            "name": qml_string(options.name),
            "company": qml_string(options.company),
            "edition": qml_string(options.edition),
            "logo": qml_string(str(options.logo) if options.logo else ""),
        }
    )
    view = QQuickView()
    view.setResizeMode(QQuickView.SizeViewToRootObject)
    view.setSource(QUrl.fromLocalFile(str(scene)))
    errors = [error.toString() for error in view.errors()]
    if errors:
        sys.exit("\n".join(errors))
    view.show()
    QTimer.singleShot(300, app.quit)
    app.exec()
    picture = view.grabWindow()
    view.close()
    scene.unlink()
    return picture


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--company", default="")
    parser.add_argument("--edition", default="")
    parser.add_argument("--logo", type=Path)
    options = parser.parse_args()
    app = QGuiApplication(sys.argv[:1])
    for suffix, multiplier in (("", 1), ("@2x", 2)):
        render(app, options.out, WORDMARK_SCALE * multiplier, options).save(str(options.out / f"logo{suffix}.png"))


if __name__ == "__main__":
    main()
