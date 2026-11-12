"""Diagnostic native-pixel landmarks and exposed contours, without registration.

Pupils are dark connected components in bounded search windows. Ambiguous or
missing detections are reported, never silently counted as matches. These are
not semantic masks or proof of expression/3D correctness.
"""

import argparse
import hashlib
import html
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from clippy_acceptance import MATCH_THRESHOLD
from overlay_clippy_3d import downsample
from PIL import Image, ImageDraw, ImageFilter
from review_clippy_3d import original_frames

PUPIL_WINDOWS = {"left_pupil": (35, 24, 57, 42), "right_pupil": (55, 22, 81, 43)}


def components(mask):
    remaining = {tuple(p) for p in np.argwhere(mask)}
    groups = []
    while remaining:
        seed = remaining.pop()
        stack, group = [seed], [seed]
        while stack:
            y, x = stack.pop()
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                neighbor = (y + dy, x + dx)
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
                    group.append(neighbor)
        groups.append(np.array(group))
    return groups


def detect_pupil(image, window, expected=None):
    a = np.asarray(image.convert("RGBA"))
    x0, y0, x1, y1 = window
    pixels = a[y0:y1, x0:x1]
    mask = (pixels[:, :, :3].max(axis=2) < 75) & (pixels[:, :, 3] >= 200)
    groups = []
    for group in components(mask):
        if len(group) < 4:
            continue
        component = np.zeros(mask.shape, dtype=np.uint8)
        component[group[:, 0], group[:, 1]] = 255
        ring = (np.asarray(Image.fromarray(component).filter(ImageFilter.MaxFilter(5))) > 0) & (component == 0)
        opaque = pixels[:, :, 3] >= 200
        bright = (pixels[:, :, :3].min(axis=2) > 150) & opaque
        # A pupil needs an opaque, bright iris surround. This excludes eyebrows,
        # which can be larger/darker than the pupil inside the same search window.
        center = group.mean(axis=0) + [y0, x0]
        anchored = expected is not None
        near_reference = not anchored or np.linalg.norm(center[::-1] - expected) <= 8
        min_opaque, min_bright = (0.5, 0.2) if anchored else (0.6, 0.34)
        if near_reference and ring.any() and opaque[ring].mean() >= min_opaque and bright[ring].mean() >= min_bright:
            groups.append(group)
    groups.sort(key=len, reverse=True)
    if not groups:
        return {"status": "missing", "point": None}
    if len(groups) > 1 and len(groups[1]) >= len(groups[0]) * 0.7:
        return {"status": "ambiguous", "point": None, "component_sizes": [len(g) for g in groups]}
    group = groups[0]
    center = group.mean(axis=0)
    return {"status": "detected", "point": [float(center[1] + x0), float(center[0] + y0)], "pixels": len(group)}


def contours(image):
    alpha = np.asarray(image.convert("RGBA"))[:, :, 3] >= 128
    result = {}
    # Reference inspection shows these exposed lower edges belong to the paper.
    # An unexpected character occlusion can contaminate the measurement; review overlays.
    for side, rows in [("paper_left", range(60, 79)), ("paper_right", range(58, 87))]:
        points = []
        for y in rows:
            xs = np.flatnonzero(alpha[y])
            points.append([int(xs.min() if side == "paper_left" else xs.max()), y] if len(xs) else None)
        result[side] = points
    result["paper_bottom"] = []
    for x in range(25, 89):
        ys = np.flatnonzero(alpha[70:, x])
        result["paper_bottom"].append([x, int(ys.max() + 70)] if len(ys) else None)
    return result


def contour_error(reference, candidate):
    offsets = []
    missing = 0
    for a, b in zip(reference, candidate, strict=True):
        if a is None and b is None:
            continue
        if a is None or b is None:
            missing += 1
        else:
            offsets.append([b[0] - a[0], b[1] - a[1]])
    distances = [float(np.linalg.norm(d)) for d in offsets]
    total = len(distances) + missing
    fraction = sum(d <= 1 for d in distances) / total if total else 1.0
    return {
        "samples": total,
        "missing_samples": missing,
        "matching_within_1px": fraction,
        "mean_offset_xy": np.mean(offsets, axis=0).tolist() if offsets else None,
        "max_error_px": max(distances) if distances else None,
        "p95_error_px": float(np.percentile(distances, 95)) if distances else None,
        "pass": fraction >= MATCH_THRESHOLD and not missing,
    }


def audit_frame(reference, candidate, closed=False, annotation=None):
    refs, news = contours(reference), contours(candidate)
    edges = {name: contour_error(points, news[name]) for name, points in refs.items()}
    landmarks = {}
    for name, window in PUPIL_WINDOWS.items():
        if annotation is not None:
            expected = annotation["landmarks"][name]["point"]
            a = (
                {"status": "detected", "point": expected}
                if expected is not None
                else {"status": "closed", "point": None}
            )
        else:
            a = detect_pupil(reference, window)
        b = detect_pupil(candidate, window, a.get("point") if annotation is not None else None)
        if closed:
            landmarks[name] = {
                "status": "not_applicable_closed_eyes",
                "pass": None,
                "note": "Closed-eye shape is checked by the pixel validator, not by pupil detection.",
            }
            continue
        if a["status"] != "detected" or b["status"] != "detected":
            landmarks[name] = {"status": "unresolved", "reference": a, "candidate": b, "pass": False}
            continue
        delta = np.array(b["point"]) - a["point"]
        error = float(np.linalg.norm(delta))
        landmarks[name] = {
            "status": "measured",
            "reference": a["point"],
            "candidate": b["point"],
            "offset_xy": delta.tolist(),
            "error_px": error,
            "pass": error <= 1,
        }
    # Upper wire silhouette is isolated from paper above row 20.
    aa = np.asarray(reference.convert("RGBA"))[:20, :, 3] >= 128
    bb = np.asarray(candidate.convert("RGBA"))[:20, :, 3] >= 128
    union = (aa | bb).sum()
    wire_iou = float((aa & bb).sum() / union) if union else 1.0
    return (
        {
            "paper_contours": edges,
            "landmarks": landmarks,
            "upper_wire_iou": wire_iou,
            "upper_wire_pass": wire_iou >= MATCH_THRESHOLD,
            "pass": all(e["pass"] for e in edges.values())
            and wire_iou >= MATCH_THRESHOLD
            and all(item["pass"] for item in landmarks.values() if item["pass"] is not None),
        },
        refs,
        news,
    )


@lru_cache(maxsize=1)
def reference_annotations():
    fixture_path = Path(__file__).resolve().parent / "fixtures/clippy/reference-landmarks.json"
    fixture = json.loads(fixture_path.read_text())
    atlas = Path(__file__).resolve().parents[1] / "data/clippy/map.png"
    if hashlib.sha256(atlas.read_bytes()).hexdigest() != fixture["source_atlas_sha256"]:
        raise ValueError("Original atlas changed: reference annotations must be reviewed")
    agent = atlas.with_name("agent.js")
    if hashlib.sha256(agent.read_bytes()).hexdigest() != fixture["source_agent_sha256"]:
        raise ValueError("Original animation definitions changed: reference annotations must be reviewed")
    return fixture


def measure_reference(action, index, reference, candidate):
    annotation = reference_annotations()["frames"][f"{action}/{index}"]
    if hashlib.sha256(reference.tobytes()).hexdigest() != annotation["rgba_sha256"]:
        raise ValueError(f"Reference frame changed: {action}/{index}")
    closed = all(item["point"] is None for item in annotation["landmarks"].values())
    return audit_frame(reference, candidate, closed, annotation)[0]


def run(folder, output):
    manifest = json.loads((folder / "manifest.json").read_text())
    output.mkdir(parents=True, exist_ok=False)
    fixture_path = Path(__file__).resolve().parent / "fixtures/clippy/reference-landmarks.json"
    fixture = reference_annotations()
    source_path = Path(__file__).resolve().parents[1] / "data/clippy/map.png"
    if hashlib.sha256(source_path.read_bytes()).hexdigest() != fixture["source_atlas_sha256"]:
        raise ValueError("Original atlas changed: review the reference annotations before proceeding")
    rows = []
    closed_indices = {"Blink": {2}, "GestureLeft": {7}, "GestureRight": {8}}
    for action in ("RestPose", "Blink", "GestureLeft", "GestureRight"):
        refs = original_frames("Idle1_1" if action == "Blink" else action)
        if action == "Blink":
            refs = refs[:5]
        entries = manifest["sequences"][action]
        if len(entries) != len(refs):
            raise ValueError("Geometry audit requires source-indexed frames")
        for index, ((reference, _), entry) in enumerate(zip(refs, entries, strict=True)):
            candidate = downsample(Image.open(folder / entry["file"]))
            annotation = fixture["frames"][f"{action}/{index}"]
            if hashlib.sha256(reference.tobytes()).hexdigest() != annotation["rgba_sha256"]:
                raise ValueError(f"Reference frame changed: {action}/{index}")
            result, ref_contours, new_contours = audit_frame(
                reference, candidate, index in closed_indices.get(action, set()), annotation
            )
            rows.append(
                {
                    "action": action,
                    "frame": index,
                    "candidate_sha256": hashlib.sha256((folder / entry["file"]).read_bytes()).hexdigest(),
                    **result,
                }
            )
            canvas = Image.new("RGB", (1116, 340), "#202020")
            draw = ImageDraw.Draw(canvas)
            for column, image in enumerate((reference, candidate, candidate)):
                background = Image.new("RGBA", (124, 93), "#008080")
                background.alpha_composite(image)
                canvas.paste(background.convert("RGB").resize((372, 279), Image.Resampling.NEAREST), (column * 372, 30))
            draw.text((8, 8), f"{action} #{index} original", fill="white")
            draw.text((380, 8), "Candidate", fill="white")
            draw.text((752, 8), "Cyan=reference; orange=candidate", fill="white")
            for contour, color in ((ref_contours, "#00ffff"), (new_contours, "#ff8000")):
                for points in contour.values():
                    for point in points:
                        if point:
                            x, y = point
                            draw.rectangle((744 + x * 3, 30 + y * 3, 746 + x * 3, 32 + y * 3), fill=color)
            for landmark in result["landmarks"].values():
                if landmark["status"] == "measured":
                    a, b = landmark["reference"], landmark["candidate"]
                    for column, point, color in ((0, a, "#00ffff"), (1, b, "#ff8000")):
                        x, y = column * 372 + point[0] * 3, 30 + point[1] * 3
                        draw.ellipse((x - 4, y - 4, x + 4, y + 4), outline=color, width=1)
                    draw.line((744 + a[0] * 3, 30 + a[1] * 3, 744 + b[0] * 3, 30 + b[1] * 3), fill="#ff4040", width=2)
            measurements = " | ".join(
                f"{name}: {item.get('error_px', 0):.1f}px"
                if item["status"] == "measured"
                else f"{name}: {item['status']}"
                for name, item in result["landmarks"].items()
            )
            draw.text((8, 316), measurements, fill="white")
            canvas.save(output / f"{action}-{index:03d}.png")
    report = {
        "reference_annotations_sha256": hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
        "input_manifest_sha256": hashlib.sha256((folder / "manifest.json").read_bytes()).hexdigest(),
        "frames": rows,
        "pass": all(r["pass"] for r in rows),
        "fixed_canvas": [124, 93],
        "limitations": [
            "Pupil detector is bounded dark-component detection, not semantic eye segmentation.",
            "Closed-eye frames have no pupil-location pass; expression still needs separate review.",
            "Paper contours measure exposed silhouettes; unexpected occlusion requires visual review.",
            "This diagnostic cannot replace pixel, timing, motion, or collision acceptance.",
        ],
    }
    (output / "geometry.json").write_text(json.dumps(report, indent=2) + "\n")
    cards = []
    for row in rows:
        measurements = {
            "pupils": row["landmarks"],
            "paper": row["paper_contours"],
            "upper_wire_overlap": row["upper_wire_iou"],
        }
        cards.append(
            f"<section><h2>{row['action']} #{row['frame']}</h2>"
            f"<img loading='lazy' src='{row['action']}-{row['frame']:03d}.png'>"
            f"<pre>{html.escape(json.dumps(measurements, indent=2))}</pre></section>"
        )
    (output / "index.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>Clippy geometry measurements</title>"
        "<style>body{background:#202020;color:#eee;font:16px sans-serif;margin:24px}"
        "img{max-width:100%;image-rendering:pixelated}section{border-top:1px solid #666;padding:12px 0}</style>"
        "<h1>Geometry measurements — not artwork approval</h1><p>Cyan: original. Orange: candidate. "
        "Red lines show pupil displacement. Offsets use native 124x93 pixels, x right and y down. "
        "Reference pupil landmarks are frozen and source-hashed; missing/ambiguous candidate detections fail.</p>"
        + "".join(cards)
    )
    print(
        json.dumps(
            {
                "frames": len(rows),
                "pass": report["pass"],
                "unresolved_pupils": sum(
                    item["status"] == "unresolved" for row in rows for item in row["landmarks"].values()
                ),
            }
        )
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if run(args.folder, args.output)["pass"] else 1)
