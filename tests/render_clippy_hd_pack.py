#!/usr/bin/env python3
"""Assemble HD keyframe clips and record every sequence at large and logical sizes."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from clippy_hd import EYES, read_master  # noqa: E402
from clippy_hd import frames as blink_frames  # noqa: E402
from clippy_hd_matte import clean_matte  # noqa: E402
from clippy_hd_pack import HDPack  # noqa: E402
from PySide6.QtCore import QRect, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter, QPainterPath  # noqa: E402

SOURCES = ROOT / "data/clippy/hd-sources"
PACK = ROOT / "data/clippy/hd-animations"
GROUPS = ("gaze", "eyebrow", "pointing", "wave", "thinking", "scratch", "celebrate", "writing", "reading", "sleep")


def inset_master(image):
    """Preserve the complete master, including faint edge alpha, inside a safe margin."""
    canvas = QImage(496, 372, QImage.Format_ARGB32)
    canvas.fill(Qt.transparent)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.drawImage(QRect(8, 6, 480, 360), image)
    painter.end()
    return canvas


def sheet_frames(path):
    sheet = QImage(str(path))
    if sheet.isNull() or not sheet.hasAlphaChannel():
        raise ValueError(f"Missing transparent source: {path}")
    images = []
    for index in range(4):
        # Integer boundaries also support odd-sized generated canvases without losing pixels.
        column, row = index % 2, index // 2
        left, top = column * sheet.width() // 2, row * sheet.height() // 2
        right, bottom = (column + 1) * sheet.width() // 2, (row + 1) * sheet.height() // 2
        cell = sheet.copy(left, top, right - left, bottom - top)
        cell = cell.scaled(464, 348, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        frame = QImage(496, 372, QImage.Format_ARGB32)
        frame.fill(Qt.transparent)
        painter = QPainter(frame)
        painter.drawImage((496 - cell.width()) // 2, (372 - cell.height()) // 2, cell)
        painter.end()
        images.append(frame)
    return images


def build():
    PACK.mkdir(parents=True, exist_ok=True)
    for group in GROUPS:
        path = SOURCES / "corrected-poses" / f"{group}.png"
        if not path.exists():
            path = SOURCES / f"{group}-clean.png"
        if not path.exists():
            path = SOURCES / f"{group}.png"
        for index, frame in enumerate(sheet_frames(path)):
            if not frame.save(str(PACK / f"{group}-{index}.png")):
                raise RuntimeError("Could not save HD frame")
    for index, frame in enumerate(blink_frames(ROOT / "data/clippy/hd-reference")):
        inset_master(frame).save(str(PACK / f"blink-{index}.png"))

    # Gaze is an eye-only action. Register the generated eye surfaces to the master
    # instead of allowing its independently generated body/paper to shift on each look.
    gaze = QImage(str(SOURCES / "gaze.png"))
    base = read_master(ROOT / "data/clippy/hd-reference/rest-pose-v1.png")
    for index in range(4):
        result = base.copy()
        painter = QPainter(result)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)
        cell_x = (index % 2) * gaze.width() // 2
        cell_y = (index // 2) * gaze.height() // 2
        for target, source in zip(EYES, (QRectF(256, 122, 88, 88), QRectF(366, 142, 88, 88)), strict=True):
            painter.save()
            clip = QPainterPath()
            clip.addEllipse(target)
            painter.setClipPath(clip)
            source.translate(cell_x, cell_y)
            painter.drawImage(target, gaze, source)
            painter.restore()
        painter.end()
        inset_master(result.scaled(496, 372, Qt.KeepAspectRatio, Qt.SmoothTransformation)).save(
            str(PACK / f"gaze-{index}.png")
        )

    animations = {}

    def add(name, group, indices, durations=None):
        durations = durations or [250] * len(indices)
        animations[name] = [
            {"file": f"{group}-{index}.png", "duration_ms": duration}
            for index, duration in zip(indices, durations, strict=True)
        ]

    add("RestPose", "blink", [0], [1000])
    add("IdleBlink", "blink", [0, 1, 2, 1, 0], [1400, 60, 100, 60, 600])
    for index, direction in enumerate(("Left", "Right", "Up", "Down")):
        # A held directional pose is bracketed by the neutral pose, as in the original gaze actions.
        animations[f"Look{direction}"] = [
            {"file": "blink-0.png", "duration_ms": 400},
            {"file": f"gaze-{index}.png", "duration_ms": 1200},
            {"file": "blink-0.png", "duration_ms": 400},
        ]
        animations[f"Gesture{direction}"] = [
            {"file": "blink-0.png", "duration_ms": 400},
            {"file": f"pointing-{index}.png", "duration_ms": 1200},
            {"file": "blink-0.png", "duration_ms": 400},
        ]
    add("IdleEyeBrowRaise", "eyebrow", [0, 1, 2, 3, 0], [500, 150, 650, 150, 500])
    add("Wave", "wave", [0, 1, 2, 3, 2, 3, 1, 0])
    add("Greeting", "wave", [0, 1, 2, 3, 2, 1, 0])
    add("GoodBye", "wave", [0, 1, 3, 2, 3, 2, 1, 0])
    add("Thinking", "thinking", [0, 1, 2, 3, 2, 1, 0], [400] * 7)
    add("IdleHeadScratch", "scratch", [0, 1, 2, 1, 2, 3, 0])
    add("Congratulate", "celebrate", [0, 1, 2, 3, 2, 3, 1, 0])
    add("Writing", "writing", [0, 1, 2, 3, 1, 2, 3, 0], [300] * 8)
    add("Reading", "reading", [0, 1, 2, 3, 0], [500] * 5)
    add("Sleep", "sleep", [0, 1, 2, 3], [500, 400, 400, 1200])
    add("Wake", "sleep", [3, 2, 1, 0], [400, 300, 300, 500])
    add("IdleSnooze", "sleep", [0, 1, 2, 3, 2, 1, 0], [400, 300, 300, 1200, 300, 300, 400])
    manifest = {
        "version": 1,
        "status": "HD keyframe artwork for the requested action set; not a redraw of all 43 original clips",
        "logical_size": [124, 93],
        "pixel_size": [496, 372],
        "scale": 4,
        "animations": animations,
        "aliases": {
            "GetAttention": "Wave",
            "Explain": "GestureRight",
            "Searching": "Reading",
            "Alert": "IdleEyeBrowRaise",
            "Show": "Greeting",
            "Hide": "GoodBye",
        },
        "notes": [
            "Greeting and goodbye share wave artwork with different timing/order.",
            "Wake reverses the sleep poses; IdleSnooze completes the sleep/wake cycle.",
            "Runtime aliases reuse named clips; they are not additional newly drawn actions.",
            "Four generated key poses per group, no synthetic crossfades or interpolated frames.",
        ],
    }
    (PACK / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for path in PACK.glob("*.png"):
        if not clean_matte(QImage(str(path))).save(str(path)):
            raise RuntimeError(f"Could not save cleaned matte: {path}")


def render(output):
    output.mkdir(parents=True, exist_ok=False)
    pack = HDPack(PACK)
    names = list(pack.manifest["animations"])
    contact = QImage(4 * 300, ((len(names) + 3) // 4) * 260, QImage.Format_RGB32)
    contact.fill(QColor("#008080"))
    cp = QPainter(contact)
    cp.setRenderHint(QPainter.SmoothPixmapTransform)
    cp.setPen(Qt.white)
    cp.setFont(QFont("Sans", 12))
    clips = []
    for position, name in enumerate(names):
        sequence = pack.sequences[name]
        x, y = position % 4 * 300, position // 4 * 260
        cp.drawText(x + 12, y + 22, name)
        cp.drawImage(QRect(x + 10, y + 35, 280, 210), pack.images[sequence[len(sequence) // 2][0]])
        path = output / f"{name}.mp4"
        clips.append(path)
        command = [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "rawvideo",
            "-pixel_format",
            "rgba",
            "-video_size",
            "640x540",
            "-framerate",
            "50",
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(path),
        ]
        with subprocess.Popen(command, stdin=subprocess.PIPE) as process:
            for index, duration in sequence:
                canvas = QImage(640, 540, QImage.Format_RGBA8888)
                canvas.fill(QColor("#008080"))
                painter = QPainter(canvas)
                painter.setRenderHint(QPainter.SmoothPixmapTransform)
                painter.setPen(Qt.white)
                painter.setFont(QFont("Sans", 14))
                painter.drawText(20, 30, name)
                painter.drawImage(72, 40, pack.images[index])
                painter.drawImage(QRect(258, 430, 124, 93), pack.images[index])
                painter.end()
                data = bytes(canvas.constBits())
                for _ in range(max(1, round(duration / 20))):
                    process.stdin.write(data)
            process.stdin.close()
            if process.wait() != 0:
                raise RuntimeError(f"Recording failed: {name}")
    cp.end()
    contact.save(str(output / "contact-sheet.png"))
    strip = QImage(4 * 248, len(GROUPS) * 216, QImage.Format_RGB32)
    strip.fill(QColor("#008080"))
    painter = QPainter(strip)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.setPen(Qt.white)
    painter.setFont(QFont("Sans", 12))
    for row, group in enumerate(GROUPS):
        for index in range(4):
            painter.drawText(index * 248 + 8, row * 216 + 20, f"{group} {index}")
            painter.drawImage(QRect(index * 248, row * 216 + 26, 248, 186), QImage(str(PACK / f"{group}-{index}.png")))
    painter.end()
    strip.save(str(output / "all-keyframes.png"))
    (output / "clips.txt").write_text("".join(f"file '{path.name}'\n" for path in clips))
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(output / "clips.txt"),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(output / "all-animations.mp4"),
        ],
        check=True,
    )
    (output / "manifest.json").write_text(json.dumps(pack.manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--build", action="store_true", help="rebuild the checked-in pack from source sheets")
    args = parser.parse_args()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication([])
    if args.build:
        build()
    render(args.output)
    print(args.output / "all-animations.mp4")
