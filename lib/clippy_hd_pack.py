"""Load the optional HD assistant pack; retain physical pixels until painting."""

import json
from pathlib import Path

from PySide6.QtCore import QRect, QSize
from PySide6.QtGui import QImage, QPainter


class HDPack:
    def __init__(self, folder: Path):
        self.folder = folder
        self.manifest = json.loads((folder / "manifest.json").read_text())
        self.frame_size = QSize(*self.manifest["logical_size"])
        self.pixel_size = QSize(*self.manifest["pixel_size"])
        self.images = []
        self.sequences = {}
        indices = {}
        for name, sequence in self.manifest["animations"].items():
            frames = []
            for item in sequence:
                filename = item["file"]
                path = (folder / filename).resolve()
                if not path.is_relative_to(folder.resolve()):
                    raise ValueError("HD frame escapes pack directory")
                if filename not in indices:
                    image = QImage(str(path))
                    if image.isNull() or image.size() != self.pixel_size or not image.hasAlphaChannel():
                        raise ValueError(f"Invalid HD frame: {filename}")
                    indices[filename] = len(self.images)
                    self.images.append(image)
                duration = item["duration_ms"]
                if not isinstance(duration, int) or duration <= 0:
                    raise ValueError(f"Invalid frame duration in {name}")
                frames.append((indices[filename], duration))
            if not frames:
                raise ValueError(f"Empty HD animation: {name}")
            self.sequences[name] = frames
        for alias, source in self.manifest.get("aliases", {}).items():
            self.sequences[alias] = self.sequences[source]

    def paint_frame(self, painter: QPainter, frame):
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        target = QRect(0, 0, self.frame_size.width(), self.frame_size.height())
        for index, _ in frame.images:
            painter.drawImage(target, self.images[index])

    def animations(self, animation_type, frame_type):
        return {
            name: animation_type(
                name, tuple(frame_type(duration, ((index, 0),), None, None) for index, duration in sequence)
            )
            for name, sequence in self.sequences.items()
        }
