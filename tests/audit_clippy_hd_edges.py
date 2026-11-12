#!/usr/bin/env python3
"""Inspect sprite matte residue on white, dark and magenta; never modify artwork."""

import argparse
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter


def edge_metrics(path):
    image = Image.open(path).convert("RGBA")
    alpha = image.getchannel("A")
    values = np.asarray(alpha)
    # Allow two physical pixels around the solid silhouette for antialiasing.
    silhouette = alpha.point(lambda value: 255 if value >= 128 else 0)
    allowed = np.asarray(silhouette.filter(ImageFilter.MaxFilter(5))) > 0
    outside = values[~allowed]
    return {
        "stray_pixels_above_alpha_8": int(np.count_nonzero(outside > 8)),
        "max_outside_alpha": int(outside.max(initial=0)),
        "outside_alpha_sum": int(outside.sum()),
        "transparent_pixels_with_rgb_residue": int(
            np.count_nonzero((values == 0) & np.any(np.asarray(image)[:, :, :3] != 0, axis=2))
        ),
    }


def audit(folder, output):
    output.mkdir(parents=True, exist_ok=False)
    report = {}
    for path in sorted(folder.glob("*.png")):
        report[path.name] = edge_metrics(path)
        image = QImage(str(path))
        width, height = image.width(), image.height()
        canvas = QImage(width * 3, height + 30, QImage.Format_RGB32)
        painter = QPainter(canvas)
        painter.setFont(QFont("Sans", 10))
        for column, background in enumerate(("#ffffff", "#101010", "#ff00ff")):
            painter.fillRect(QRect(column * width, 0, width, height + 30), QColor(background))
            painter.setPen(QColor("#ffffff" if column == 1 else "#000000"))
            painter.drawText(column * width + 8, 20, path.name)
            painter.drawImage(column * width, 30, image)
        painter.end()
        canvas.save(str(output / path.name))
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    failures = [
        name
        for name, metrics in report.items()
        if metrics["stray_pixels_above_alpha_8"] or metrics["transparent_pixels_with_rgb_residue"]
    ]
    print(json.dumps({"frames": len(report), "frames_with_residue": failures}, indent=2))
    return failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, default=Path(__file__).resolve().parents[1] / "data/clippy/hd-animations")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication([])
    raise SystemExit(bool(audit(args.pack, args.output)))
