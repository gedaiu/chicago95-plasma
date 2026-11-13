"""Independent, fail-closed validation of rendered Clippy frames at 124x93.

Regions are inspection windows, not perfect semantic segmentation. Every region
must pass; the large paper cannot compensate for an incorrect eye or wire tip.
"""

import argparse
import bisect
import hashlib
import html
import json
import subprocess
from pathlib import Path

import numpy as np
from clippy_acceptance import CHANNEL_TOLERANCE, MATCH_THRESHOLD
from clippy_geometry_audit import measure_reference
from clippy_reference_color import COLOR_REFERENCE_POLICY, smooth_reference_color
from overlay_clippy_3d import downsample
from PIL import Image, ImageDraw
from review_clippy_3d import original_frames

REGIONS = {
    "upper_wire": (38, 0, 82, 24),
    "left_eye": (33, 18, 57, 43),
    "right_eye": (55, 18, 83, 44),
    "lower_wire": (39, 38, 86, 86),
    "left_tip": (12, 34, 54, 67),
    "right_tip": (69, 32, 112, 68),
    "paper_right_edge": (90, 20, 116, 86),
    "paper_lower_edge": (12, 76, 96, 93),
    "paper_left_edge": (12, 43, 45, 80),
}
THRESHOLD = MATCH_THRESHOLD


def pixels(image):
    a = np.asarray(image.convert("RGBA")).astype(np.float64)
    a[:, :, :3] *= a[:, :, 3:] / 255
    return a


def boundary(mask):
    padded = np.pad(mask, 1)
    interior = mask.copy()
    for dy, dx in ((0, 1), (2, 1), (1, 0), (1, 2)):
        interior &= padded[dy : dy + mask.shape[0], dx : dx + mask.shape[1]]
    return np.argwhere(mask & ~interior)


def distances(a, b):
    if not len(a) or not len(b):
        return None
    result = []
    for start in range(0, len(a), 128):
        delta = a[start : start + 128, None, :] - b[None, :, :]
        result.extend(np.sqrt((delta * delta).sum(axis=2).min(axis=1)).tolist())
    return result


def spatial(original, candidate, smooth_color=False):
    raw = pixels(original)
    a, b = pixels(smooth_reference_color(original)) if smooth_color else raw, pixels(candidate)
    active = (a[:, :, 3] > 0) | (b[:, :, 3] > 0)
    good = np.max(abs(a - b), axis=2) <= CHANNEL_TOLERANCE
    raw_good = np.max(abs(raw - b), axis=2) <= CHANNEL_TOLERANCE
    regions = {}
    for name, (x0, y0, x1, y1) in {"whole_foreground": (0, 0, 124, 93), **REGIONS}.items():
        mask = active[y0:y1, x0:x1]
        fraction = float(good[y0:y1, x0:x1][mask].mean()) if mask.any() else 1.0
        regions[name] = {
            "matching_pixel_fraction": fraction,
            "raw_matching_pixel_fraction": float(raw_good[y0:y1, x0:x1][mask].mean()) if mask.any() else 1.0,
            "foreground_pixels": int(mask.sum()),
            "pass": fraction >= THRESHOLD,
        }
    aa, bb = a[:, :, 3] >= 128, b[:, :, 3] >= 128
    union = (aa | bb).sum()
    iou = float((aa & bb).sum() / union) if union else 1.0
    edge_a, edge_b = boundary(aa), boundary(bb)
    da, db = distances(edge_a, edge_b), distances(edge_b, edge_a)
    if da is None or db is None:
        edge95 = 0.0 if not len(edge_a) and not len(edge_b) else None
        edge_max = edge95
    else:
        edge95 = float(np.percentile(da + db, 95))
        edge_max = float(max(da + db))
    edge_pass = edge95 is not None and edge95 <= 1.0 and edge_max <= 2.0
    return {
        "regions": regions,
        "color_reference_policy": COLOR_REFERENCE_POLICY if smooth_color else "raw-source",
        "silhouette_iou": iou,
        "boundary_p95_pixels": edge95,
        "boundary_max_pixels": edge_max,
        "boundary_pass": edge_pass,
        "pass": all(r["pass"] for r in regions.values()) and iou >= THRESHOLD and edge_pass,
    }


def motion(previous_reference, reference, previous_candidate, candidate, smooth_color=False):
    # Signed per-pixel changes catch frozen frames, reverse motion and extra gestures.
    if smooth_color:
        reference = smooth_reference_color(reference)
        previous_reference = smooth_reference_color(previous_reference)
    da = pixels(reference) - pixels(previous_reference)
    db = pixels(candidate) - pixels(previous_candidate)
    moving = (np.max(abs(da), axis=2) > 8) | (np.max(abs(db), axis=2) > 8)
    good = np.max(abs(da - db), axis=2) <= CHANNEL_TOLERANCE
    regions = {}
    for name, (x0, y0, x1, y1) in {"whole_motion": (0, 0, 124, 93), **REGIONS}.items():
        mask = moving[y0:y1, x0:x1]
        fraction = float(good[y0:y1, x0:x1][mask].mean()) if mask.any() else 1.0
        regions[name] = {
            "matching_motion_fraction": fraction,
            "moving_pixels": int(mask.sum()),
            "pass": fraction >= THRESHOLD,
        }
    return {"regions": regions, "pass": all(r["pass"] for r in regions.values())}


def validate_sequence(refs, images, durations, smooth_color=False):
    expected = [duration for _, duration in refs]
    timing = durations == expected and len(images) == len(refs)
    rows = []
    for index in range(min(len(images), len(refs))):
        result = spatial(refs[index][0], images[index], smooth_color=smooth_color)
        temporal = (
            motion(refs[index - 1][0], refs[index][0], images[index - 1], images[index], smooth_color=smooth_color)
            if index
            else None
        )
        rows.append(
            {
                "frame": index,
                "spatial": result,
                "motion": temporal,
                "pass": result["pass"] and (temporal is None or temporal["pass"]),
            }
        )
    return {
        "timing_pass": timing,
        "expected_frames": len(refs),
        "actual_frames": len(images),
        "expected_durations_ms": expected,
        "actual_durations_ms": durations,
        "frames": rows,
        "pass": timing and all(r["pass"] for r in rows),
    }


def validate_video(path):
    probe = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_frames",
                "-show_format",
                "-show_entries",
                "frame=best_effort_timestamp_time:stream=width,height:format=duration",
                "-show_streams",
                "-of",
                "json",
                str(path),
            ]
        )
    )
    width, height = probe["streams"][0]["width"], probe["streams"][0]["height"]
    times = [float(frame["best_effort_timestamp_time"]) * 1000 for frame in probe["frames"]]
    refs, starts, elapsed = [], [], 0
    for action in ("RestPose", "Blink", "GestureLeft", "GestureRight"):
        sequence = original_frames("Idle1_1" if action == "Blink" else action)
        if action == "Blink":
            sequence = sequence[:5]
        for index, (image, duration) in enumerate(sequence):
            starts.append(elapsed)
            refs.append((action, index, image))
            elapsed += duration
    duration = float(probe["format"]["duration"]) * 1000
    timing = (
        abs(duration - elapsed) < 1
        and bool(times)
        and abs(times[0]) < 1
        and all(any(abs(time - start) < 1 for time in times) for start in starts)
        and all(a < b for a, b in zip(times[:-1], times[1:], strict=True))
    )
    decoder = subprocess.Popen(
        [
            "ffmpeg",
            "-v",
            "error",
            "-c:v",
            "libvpx-vp9",
            "-i",
            str(path),
            "-fps_mode",
            "passthrough",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-",
        ],
        stdout=subprocess.PIPE,
    )
    results = []
    previous_reference = previous_image = None
    size = width * height * 4
    try:
        for time in times:
            raw = decoder.stdout.read(size)
            if len(raw) != size:
                raise RuntimeError("Truncated transparent video")
            image = downsample(Image.frombytes("RGBA", (width, height), raw))
            action, index, reference = refs[max(0, bisect.bisect_right(starts, time + 1e-4) - 1)]
            result = spatial(reference, image)
            geometry = measure_reference(action, index, reference, image)
            temporal = (
                motion(previous_reference, reference, previous_image, image) if previous_image is not None else None
            )
            results.append(
                {
                    "time_ms": time,
                    "geometry": geometry,
                    "action": action,
                    "source_frame": index,
                    "spatial": result,
                    "motion": temporal,
                    "pass": result["pass"] and geometry["pass"] and (temporal is None or temporal["pass"]),
                }
            )
            previous_reference, previous_image = reference, image
        if decoder.stdout.read(1):
            raise RuntimeError("Decoded frame count differs from video timestamps")
    finally:
        decoder.stdout.close()
        code = decoder.wait()
    if code:
        raise RuntimeError("Video decoder failed")
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "decoded_frames": len(results),
        "duration_ms": duration,
        "expected_duration_ms": elapsed,
        "timing_pass": timing,
        "frames": results,
        "pass": timing and all(r["pass"] for r in results),
    }


def validate(folder, output, video=None):
    manifest = json.loads((folder / "manifest.json").read_text())
    output.mkdir(parents=True, exist_ok=False)
    actions = {}
    for action in ("RestPose", "Blink", "GestureLeft", "GestureRight"):
        refs = original_frames("Idle1_1" if action == "Blink" else action)
        if action == "Blink":
            refs = refs[:5]
        entries = manifest.get("sequences", {}).get(action, [])
        images = [downsample(Image.open(folder / item["file"])) for item in entries]
        actions[action] = validate_sequence(refs, images, [item["duration_ms"] for item in entries])
        for row, reference, candidate in zip(actions[action]["frames"], refs, images, strict=False):
            index = row["frame"]
            row["geometry"] = measure_reference(action, index, reference[0], candidate)
            row["pass"] = row["pass"] and row["geometry"]["pass"]
            actions[action]["pass"] = actions[action]["pass"] and row["pass"]
            canvas = Image.new("RGB", (744, 330), "#202020")
            draw = ImageDraw.Draw(canvas)
            for column, image in enumerate((reference[0], candidate)):
                background = Image.new("RGBA", (124, 93), "#008080")
                background.alpha_composite(image)
                large = background.convert("RGB").resize((372, 279), Image.Resampling.NEAREST)
                canvas.paste(large, (column * 372, 30))
                draw.text(
                    (column * 372 + 6, 6),
                    f"{action} #{index}: " + ("ORIGINAL" if column == 0 else "CANDIDATE"),
                    fill="white",
                )
                for name, (x0, y0, x1, y1) in REGIONS.items():
                    passed = row["spatial"]["regions"][name]["pass"]
                    draw.rectangle(
                        (column * 372 + x0 * 3, y0 * 3 + 30, column * 372 + x1 * 3 - 1, y1 * 3 + 29),
                        outline="#50ff50" if passed else "#ff4040",
                    )
            draw.text(
                (6, 312), "Red: failing region. Green: pixel check passed (not an artwork approval).", fill="white"
            )
            canvas.save(output / f"{action}-{index:03d}.png")
    report = {
        "threshold": THRESHOLD,
        "max_channel_error": CHANNEL_TOLERANCE,
        "comparison_size": [124, 93],
        "registration": "none; fixed full canvas",
        "regions": REGIONS,
        "actions": actions,
        "pass": all(action["pass"] for action in actions.values()),
        "limitations": [
            "Regions are inspection windows, not object masks.",
            "Pixel/edge/motion checks do not prove 3D collision freedom; run the Blender clearance check.",
            "Manual review of shape, depth, eye direction and expression remains required.",
            "Original ACS branching is not simulated.",
        ],
    }
    report["input_manifest_sha256"] = hashlib.sha256((folder / "manifest.json").read_bytes()).hexdigest()
    report["source_atlas_sha256"] = hashlib.sha256(
        (Path(__file__).resolve().parents[1] / "data/clippy/map.png").read_bytes()
    ).hexdigest()
    if video:
        report["video"] = validate_video(video)
        report["pass"] = report["pass"] and report["video"]["pass"]
    (output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    failures = []
    for action, result in actions.items():
        if not result["timing_pass"]:
            failures.append({"action": action, "failure": "frame count or timing"})
        for row in result["frames"]:
            if not row["pass"]:
                failures.append(
                    {
                        "action": action,
                        "frame": row["frame"],
                        "geometry": row["geometry"],
                        "spatial_regions": [n for n, r in row["spatial"]["regions"].items() if not r["pass"]],
                        "motion_regions": [
                            n for n, r in (row["motion"] or {}).get("regions", {}).items() if not r["pass"]
                        ],
                        "boundary_pass": row["spatial"]["boundary_pass"],
                        "boundary_p95_pixels": row["spatial"]["boundary_p95_pixels"],
                        "region_match_percent": {
                            n: round(r["matching_pixel_fraction"] * 100, 2)
                            for n, r in row["spatial"]["regions"].items()
                        },
                        "motion_match_percent": {
                            n: round(r["matching_motion_fraction"] * 100, 2)
                            for n, r in (row["motion"] or {}).get("regions", {}).items()
                        },
                    }
                )
    (output / "failures.json").write_text(json.dumps(failures, indent=2) + "\n")
    cards = []
    for failure in failures:
        label = html.escape(f"{failure['action']} / {failure.get('frame', 'timing')}")
        image = (
            f"<a href='{failure['action']}-{failure['frame']:03d}.png'>"
            f"<img loading='lazy' src='{failure['action']}-{failure['frame']:03d}.png'></a>"
            if "frame" in failure
            else ""
        )
        cards.append(
            f"<section><h2>{label}</h2><pre>{html.escape(json.dumps(failure, indent=2))}</pre>{image}</section>"
        )
    (output / "index.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>Clippy fidelity failures</title>"
        "<style>body{background:#202020;color:#eee;font:16px sans-serif;margin:24px}"
        "section{border-top:1px solid #666;padding:16px 0}img{max-width:100%;image-rendering:pixelated}"
        "pre{white-space:pre-wrap}a{color:#9cf}</style>"
        "<h1>Clippy fidelity validation: " + ("numeric checks passed" if report["pass"] else "FAILED") + "</h1>"
        "<p>Each inspection region must have at least 98% matching pixels within 5/255 per channel. "
        "Silhouette overlap must reach 98%; boundary distances and actual pixel motion are also checked. "
        "Regions are inspection windows, not segmented object masks. Manual review remains required.</p>"
        "<p><a href='validation.json'>Full report, including decoded video checks</a></p>" + "".join(cards)
    )
    print(json.dumps({"pass": report["pass"], "failures": len(failures), "output": str(output)}, indent=2))
    return report["pass"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--video", type=Path, help="Transparent VP9 WebM to independently decode and validate")
    args = parser.parse_args()
    raise SystemExit(0 if validate(args.folder, args.output, args.video) else 1)
