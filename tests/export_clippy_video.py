"""Export a rendered manifest as transparent WebM and opaque MP4; verify decoded alpha."""

import argparse
import json
import math
import subprocess
from functools import reduce
from pathlib import Path

import numpy as np
from PIL import Image


def frame_schedule(durations, fps):
    """Round cumulative boundaries, so rounding error cannot accumulate per pose."""
    if not isinstance(fps, int) or fps <= 0:
        raise ValueError("fps must be a positive integer")
    elapsed, previous, repeats, errors = 0, 0, [], []
    for duration in durations:
        if not isinstance(duration, int) or duration < 0:
            raise ValueError("Durations must be nonnegative integer milliseconds")
        elapsed += duration
        boundary = (elapsed * fps + 500) // 1000
        repeats.append(boundary - previous)
        errors.append(boundary * 1000 / fps - elapsed)
        previous = boundary
    return repeats, errors


def export(folder, output, actions=None, fps=None):
    manifest = json.loads((folder / "manifest.json").read_text())
    names = list(manifest["sequences"]) if actions is None else actions
    frames = [item for name in names for item in manifest["sequences"][name]]
    if fps is None:
        tick = reduce(math.gcd, (item["duration_ms"] for item in frames))
        if tick <= 0 or 1000 % tick:
            raise ValueError("Frame durations must support an integral lossless timing grid")
        fps = 1000 // tick
    repeats, timing_errors = frame_schedule([item["duration_ms"] for item in frames], fps)
    if not sum(repeats):
        raise ValueError("Selected sequence is shorter than half an output frame")
    width, height = manifest["pixel_size"]
    output.mkdir(parents=True, exist_ok=False)
    common = [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgba",
        "-s",
        f"{width}x{height}",
        "-r",
        str(fps),
        "-i",
        "-",
        "-an",
    ]
    webm = subprocess.Popen(
        common
        + [
            "-filter_complex",
            "[0:v]split[c][a];[c]format=yuv420p[color];[a]alphaextract[alpha];[color][alpha]alphamerge[out]",
            "-map",
            "[out]",
            "-c:v",
            "libvpx-vp9",
            "-pix_fmt",
            "yuva420p",
            "-lossless",
            "1",
            "-deadline",
            "good",
            "-cpu-used",
            "4",
            "-row-mt",
            "1",
            "-threads",
            "2",
            str(output / "clippy-transparent.webm"),
        ],
        stdin=subprocess.PIPE,
    )
    mp4 = subprocess.Popen(
        common
        + [
            "-c:v",
            "libx264",
            "-crf",
            "16",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-threads",
            "2",
            str(output / "clippy-preview.mp4"),
        ],
        stdin=subprocess.PIPE,
    )
    expected_alpha = []
    count = 0
    try:
        for item, repeat in zip(frames, repeats, strict=True):
            image = Image.open(folder / item["file"]).convert("RGBA")
            if image.size != (width, height):
                raise ValueError(f"Unexpected dimensions: {item['file']}")
            opaque = Image.alpha_composite(Image.new("RGBA", image.size, "#008080"), image)
            raw, preview = image.tobytes(), opaque.tobytes()
            expected_alpha.append((np.asarray(image.getchannel("A")), repeat))
            for _ in range(repeat):
                webm.stdin.write(raw)
                mp4.stdin.write(preview)
                count += 1
    finally:
        webm.stdin.close()
        mp4.stdin.close()
        codes = [webm.wait(), mp4.wait()]
    if any(codes):
        raise RuntimeError(f"Encoding failed: {codes}")
    # Force libvpx: FFmpeg's native VP9 decoder can silently discard WebM alpha.
    decoder = subprocess.Popen(
        [
            "ffmpeg",
            "-v",
            "error",
            "-c:v",
            "libvpx-vp9",
            "-i",
            str(output / "clippy-transparent.webm"),
            "-vf",
            "alphaextract",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "gray",
            "-",
        ],
        stdout=subprocess.PIPE,
    )
    size = width * height
    decoded = 0
    max_alpha_error = 0
    try:
        for expected, repeat in expected_alpha:
            for _ in range(repeat):
                raw = decoder.stdout.read(size)
                if len(raw) != size:
                    raise RuntimeError(f"Truncated WebM at frame {decoded}")
                alpha = np.frombuffer(raw, dtype=np.uint8).reshape(height, width)
                error = int(np.abs(alpha.astype(np.int16) - expected).max())
                max_alpha_error = max(max_alpha_error, error)
                if error:
                    raise RuntimeError(f"Alpha changed at frame {decoded}: {error}")
                decoded += 1
        if decoder.stdout.read(1):
            raise RuntimeError("Unexpected extra WebM frames")
    finally:
        decoder.stdout.close()
        code = decoder.wait()
    if code:
        raise RuntimeError("WebM decoding failed")
    probe = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-count_frames",
                "-show_entries",
                "stream=width,height,nb_read_frames,r_frame_rate",
                "-of",
                "json",
                str(output / "clippy-preview.mp4"),
            ]
        )
    )["streams"][0]
    assert int(probe["nb_read_frames"]) == count
    assert (probe["width"], probe["height"]) == (width, height)
    rate_n, rate_d = map(int, probe["r_frame_rate"].split("/"))
    assert rate_n == fps * rate_d
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(output / "clippy-preview.mp4"), "-f", "null", "-"], check=True)
    report = {
        "source": str(folder),
        "actions": names,
        "frames": count,
        "fps": fps,
        "duration_seconds": count / fps,
        "source_duration_ms": sum(item["duration_ms"] for item in frames),
        "max_boundary_error_ms": max(map(abs, timing_errors), default=0),
        "source_frame_repeats": repeats,
        "sampling": "Source poses held; no invented or untested interpolated geometry.",
        "dimensions": [width, height],
        "webm_decoded_frames": decoded,
        "max_alpha_error": max_alpha_error,
        "mp4_fully_decoded": True,
        "background": "MP4: teal; WebM: transparent",
        "artwork_status": manifest["status"],
        "note": "Export validation does not certify the 98% visual-match requirement.",
    }
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--actions", nargs="+")
    parser.add_argument("--fps", type=int, help="Fixed output frame rate, e.g. 60; default retains exact source holds")
    args = parser.parse_args()
    export(args.folder, args.output, args.actions, args.fps)
