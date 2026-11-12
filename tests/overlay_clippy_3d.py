"""Compare original atlas frames with HD renders on a fixed 124x93 canvas.

Writes lossless native-resolution images, contact sheets, and two review videos:
manual pose correspondence (original timing) and unchanged source/candidate timing.
No frame is translated, cropped, registered, or individually scaled to fit.
"""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
from clippy_acceptance import MATCH_THRESHOLD
from PIL import Image, ImageDraw
from review_clippy_3d import SIZE, original_frames

# Explicit nearest-pose correspondence; NOT a claim that these poses match.
# Gesture blink/expression variants do not yet exist in the new renderer.
POSE_FILES = {
    "RestPose": ["rest"],
    "Blink": ["rest", "blink-1", "blink-3", "blink-2", "rest"],
    "GestureLeft": ["rest", "point-right-1", "point-right-2", "point-right-4", "point-right-5"]
    + ["point-right-6"] * 7
    + ["point-right-4", "point-right-2", "point-right-1", "rest"],
    "GestureRight": ["rest", "point-left-2", "point-left-2", "point-left-3", "point-left-4", "point-left-5"]
    + ["point-left-6"] * 6
    + ["point-left-4", "point-left-3", "point-left-2", "point-left-1", "rest"],
}
BACKGROUND = (0, 128, 128, 255)


def downsample(image):
    # RGBa is premultiplied alpha: hidden RGB cannot bleed into the filtered edge.
    return image.convert("RGBA").convert("RGBa").resize(SIZE, Image.Resampling.LANCZOS).convert("RGBA")


def flatten(image):
    return Image.alpha_composite(Image.new("RGBA", SIZE, BACKGROUND), image).convert("RGB")


def panels(original, candidate):
    a, b = flatten(original), flatten(candidate)
    delta = np.abs(np.asarray(a).astype(np.int16) - np.asarray(b).astype(np.int16))
    return [a, b, Image.blend(a, b, 0.5), Image.fromarray(np.minimum(delta * 4, 255).astype(np.uint8))]


def metrics(original, candidate):
    a, b = (np.asarray(image).astype(float) for image in (original, candidate))
    alpha_a, alpha_b = a[:, :, 3] >= 128, b[:, :, 3] >= 128
    union = alpha_a | alpha_b
    foreground = (a[:, :, 3] > 0) | (b[:, :, 3] > 0)
    premul_a = a[:, :, :3] * a[:, :, 3:] / 255
    premul_b = b[:, :, :3] * b[:, :, 3:] / 255
    color_similarity = 1 - float(np.abs(premul_a - premul_b)[foreground].mean()) / 255 if foreground.any() else 1.0
    return {
        "foreground_color_similarity": color_similarity,
        "silhouette_iou": float((alpha_a & alpha_b).sum() / union.sum()) if union.any() else 1.0,
        "premultiplied_rgb_mae": float(np.abs(premul_a - premul_b).mean()),
        "alpha_mae": float(np.abs(a[:, :, 3] - b[:, :, 3]).mean()),
        "exact_match": bool(np.array_equal(a, b)),
    }


def timeline_index(durations, time):
    elapsed = 0
    for index, duration in enumerate(durations):
        elapsed += duration
        if time < elapsed:
            return index
    return len(durations) - 1


def presentation(images, title, alternating=None):
    columns = images + ([alternating] if alternating is not None else [])
    canvas = Image.new("RGB", (len(columns) * 256, 300), "#202020")
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 4), title, fill="white")
    labels = ["Original", "New (downsampled)", "50/50 overlay", "Difference x4", "Alternating old/new"]
    for column, (label, image) in enumerate(zip(labels, columns, strict=False)):
        x = column * 256
        draw.text((x + 4, 25), label, fill="white")
        canvas.paste(image.resize((248, 186), Image.Resampling.NEAREST), (x + 4, 44))
        # The enlargement above is nearest-neighbor AFTER the 124x93 comparison.
        # Native PNGs are the source of truth; no high-resolution pixels enter here.
    return canvas


def video(path, sequences, candidate_sequences, native, mode, pose_files, source_indexed=False):
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgb24",
        "-video_size",
        "1280x300",
        "-framerate",
        "100",
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-crf",
        "16",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(path),
    ]
    count = 0
    with subprocess.Popen(command, stdin=subprocess.PIPE) as process:
        for action, refs in sequences.items():
            durations = [duration for _, duration in refs]
            candidates = candidate_sequences[action]
            candidate_durations = [item["duration_ms"] for item in candidates]
            total = sum(durations) if mode == "pose" else max(sum(durations), sum(candidate_durations))
            for time in range(0, total, 10):
                index = timeline_index(durations, time)
                if mode == "pose":
                    filename = pose_files[action][index] + ".png"
                else:
                    filename = candidates[timeline_index(candidate_durations, time)]["file"]
                images = panels(refs[index][0], native[filename])
                title = f"{mode} | {action} | original #{index} | new {filename} | {time} ms"
                canvas = presentation(images, title, images[(time // 250) % 2])
                draw = ImageDraw.Draw(canvas)
                note = (
                    (
                        "Source-indexed poses; original durations; visual fidelity still under review."
                        if source_indexed
                        else "Nearest pose mapping; expressions may be missing. Original frame durations."
                    )
                    if mode == "pose"
                    else "Actual elapsed time; no retiming. Ended sequences hold their final frame."
                )
                draw.text((8, 250), note, fill="white")
                draw.text(
                    (8, 274),
                    "All comparisons at 124x93. Display enlarged 2x with nearest-neighbor. Fixed anchor.",
                    fill="white",
                )
                process.stdin.write(canvas.tobytes())
                count += 1
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError(f"Video encoding failed: {path}")
    return count


def generate(folder, output):
    manifest = json.loads((folder / "manifest.json").read_text())
    output.mkdir(parents=True, exist_ok=False)
    native = {}
    hashes = {}
    for filename in sorted({item["file"] for items in manifest["sequences"].values() for item in items}):
        path = folder / filename
        image = Image.open(path).convert("RGBA")
        if image.size != tuple(manifest["pixel_size"]):
            raise ValueError(f"Unexpected source dimensions: {path}")
        native[filename] = downsample(image)
        hashes[filename] = hashlib.sha256(path.read_bytes()).hexdigest()
    report = {
        "comparison_size": list(SIZE),
        "registration": "none; full canvas, fixed anchor",
        "input_sha256": hashes,
        "frames": [],
        "videos": {},
        "limitations": [
            "Manual nearest-pose correspondence is explicit, not an exact pose match.",
            "Gesture blink/expression variants are missing from the new render.",
            "Scores describe differences; there is no automatic visual-fidelity pass threshold.",
            "Original ACS branching is not simulated; Blink uses Idle1_1 frames 0 through 4.",
        ],
    }
    sequences = {}
    reference_frames = manifest.get("reference_frames", {})
    pose_files = (
        {action: [Path(item["file"]).stem for item in frames] for action, frames in reference_frames.items()}
        if reference_frames
        else POSE_FILES
    )
    for action, names in pose_files.items():
        refs = original_frames("Idle1_1" if action == "Blink" else action)
        if action == "Blink":
            refs = refs[:5]
        if len(refs) != len(names):
            raise ValueError(f"Pose mapping length differs for {action}")
        if reference_frames:
            assert [item["original_index"] for item in reference_frames[action]] == list(range(len(refs)))
            assert [item["duration_ms"] for item in manifest["sequences"][action]] == [duration for _, duration in refs]
        sequences[action] = refs
        rows = []
        elapsed = 0
        for index, ((original, duration), name) in enumerate(zip(refs, names, strict=True)):
            candidate = native[name + ".png"]
            images = panels(original, candidate)
            destination = output / action / f"{index:03d}"
            destination.mkdir(parents=True)
            original.save(destination / "original.png")
            candidate.save(destination / "new.png")
            images[2].save(destination / "overlay.png")
            images[3].save(destination / "difference.png")
            Image.fromarray(
                np.abs(
                    np.asarray(original.getchannel("A")).astype(np.int16)
                    - np.asarray(candidate.getchannel("A")).astype(np.int16)
                ).astype(np.uint8)
            ).save(destination / "alpha-difference.png")
            images[0].save(
                destination / "alternating.gif",
                save_all=True,
                append_images=[images[1]],
                duration=250,
                loop=0,
                optimize=False,
            )
            note = "source-indexed pose" if reference_frames else "nearest pose; expressions may be missing"
            report["frames"].append(
                {
                    "action": action,
                    "original_index": index,
                    "original_time_ms": elapsed,
                    "duration_ms": duration,
                    "candidate": name + ".png",
                    "mapping": note,
                    **metrics(original, candidate),
                }
            )
            rows.append(presentation(images, f"{action} #{index} | {elapsed} ms | new {name} | {note}"))
            elapsed += duration
        sheet = Image.new("RGB", (1024, 300 * len(rows)))
        for index, row in enumerate(rows):
            sheet.paste(row, (0, 300 * index))
        sheet.save(output / f"{action}-contact.png")
    for mode in ("pose", "timeline"):
        count = video(
            output / f"{mode}-overlay.mp4",
            sequences,
            manifest["sequences"],
            native,
            mode,
            pose_files,
            bool(reference_frames),
        )
        report["videos"][mode] = {"frames": count, "fps": 100, "duration_seconds": count / 100}
    failures = [
        dict(
            action=f["action"],
            frame=f["original_index"],
            silhouette=f["silhouette_iou"],
            color=f["foreground_color_similarity"],
        )
        for f in report["frames"]
        if f["silhouette_iou"] < MATCH_THRESHOLD or f["foreground_color_similarity"] < MATCH_THRESHOLD
    ]
    report["acceptance"] = {
        "threshold": MATCH_THRESHOLD,
        "metric_scope": "silhouette IoU AND foreground premultiplied RGB similarity, each frame",
        "visual_pass": not failures,
        "failing_frames": failures,
        "pose_review": "manual review required; numeric scores do not certify pose",
        "source_timing_used": bool(reference_frames),
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-acceptance", action="store_true")
    args = parser.parse_args()
    result = generate(args.folder, args.output)
    print(json.dumps({"compared_frames": len(result["frames"]), "videos": result["videos"]}, indent=2))

    if args.require_acceptance and not result["acceptance"]["visual_pass"]:
        raise SystemExit("FAILED: one or more frames miss the 98% silhouette/color thresholds; see report.json")
