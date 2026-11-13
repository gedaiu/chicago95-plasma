"""Apply independent 98% shape/color, local-image and signed-motion checks to all 43 actions."""

import argparse
import hashlib
import html
import json
from pathlib import Path

from clippy_acceptance import MATCH_THRESHOLD
from clippy_all_catalog import ROOT, catalog
from clippy_reference_color import COLOR_REFERENCE_POLICY, smooth_reference_color
from overlay_clippy_3d import downsample, metrics
from PIL import Image
from review_clippy_3d import original_frames
from validate_clippy_fidelity import motion, spatial


def validate(folder, output, smooth_color=False):
    manifest = json.loads((folder / "manifest.json").read_text())
    source = catalog()
    if set(manifest["sequences"]) != set(source):
        raise ValueError("Incomplete source action coverage")
    output.mkdir(parents=True, exist_ok=True)
    sequences = {}
    color_key = "smoothed_reference_color_similarity" if smooth_color else "foreground_color_similarity"
    for name, items in manifest["sequences"].items():
        refs = original_frames(name)
        if len(items) != len(refs):
            raise ValueError(f"{name}: incorrect source frame count")
        rows = []
        previous = None
        for index, (item, (reference, duration)) in enumerate(zip(items, refs, strict=True)):
            path = folder / item["file"]
            with Image.open(path) as full:
                candidate = downsample(full)
            measurements = metrics(reference, candidate)
            measurements["smoothed_reference_color_similarity"] = metrics(smooth_reference_color(reference), candidate)[
                "foreground_color_similarity"
            ]
            image_check = spatial(reference, candidate, smooth_color=smooth_color)
            movement = (
                motion(refs[index - 1][0], reference, previous, candidate, smooth_color=smooth_color)
                if previous is not None
                else None
            )
            timing = (
                item["source_index"] == index
                and item["duration_ms"] == duration
                and item["source"] == source[name]["frames"][index]
            )
            shape_color = all(measurements[k] >= MATCH_THRESHOLD for k in ["silhouette_iou", color_key])
            rows.append(
                {
                    "source_index": index,
                    "png_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "reference_rgba_sha256": hashlib.sha256(reference.tobytes()).hexdigest(),
                    "metrics": measurements,
                    "spatial": image_check,
                    "motion": movement,
                    "timing_metadata_pass": timing,
                    "shape_color_pass": shape_color,
                    "pass": shape_color and image_check["pass"] and timing and (movement is None or movement["pass"]),
                }
            )
            previous = candidate
        sequences[name] = rows
        print(name, sum(r["pass"] for r in rows), "/", len(rows), flush=True)
    rows = [r for action in sequences.values() for r in action]
    report = {
        "threshold": MATCH_THRESHOLD,
        "color_reference_policy": COLOR_REFERENCE_POLICY if smooth_color else "raw-source",
        "manifest_sha256": hashlib.sha256((folder / "manifest.json").read_bytes()).hexdigest(),
        "source_atlas_sha256": hashlib.sha256((ROOT / "data/clippy/map.png").read_bytes()).hexdigest(),
        "source_definition_sha256": hashlib.sha256((ROOT / "data/clippy/agent.js").read_bytes()).hexdigest(),
        "poses": len(rows),
        "actions": len(sequences),
        "passing_frames": sum(r["pass"] for r in rows),
        "pass": all(r["pass"] for r in rows),
        "scope": "Original 124x93 canvas, no image alignment or background-dominated score. "
        "Per-frame shape/color and local pixel/motion gates; semantic pose and collisions need separate review.",
        "sequences": sequences,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    table = "".join(
        f"<tr><td>{html.escape(n)}</td><td>{sum(r['pass'] for r in rs)}/{len(rs)}</td>"
        f"<td>{min(r['metrics']['silhouette_iou'] for r in rs):.3f}</td>"
        f"<td>{min(r['metrics'][color_key] for r in rs):.3f}</td></tr>"
        for n, rs in sequences.items()
    )
    (output / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Clippy 98% acceptance</title>'
        "<style>body{font:16px system-ui;margin:30px}td,th{padding:7px;text-align:left}</style>"
        f"<h1>{'PASS' if report['pass'] else 'FAIL'}: 98% source-match acceptance</h1>"
        f"<p>{report['passing_frames']}/{len(rows)} frames pass all image, motion and timing gates.</p>"
        f"<p>Color reference: {html.escape(report['color_reference_policy'])}. "
        "Raw scores remain in the full report.</p>"
        "<p>These results do not certify collision-free geometry or semantic pose correctness.</p>"
        '<p><a href="report.json">Full per-frame measurements</a></p><table><tr><th>Action</th>'
        "<th>Passing frames</th><th>Minimum silhouette IoU</th><th>Minimum foreground color similarity</th></tr>"
        + table
        + "</table>"
    )
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument(
        "--smooth-color-reference",
        action="store_true",
        help="Use the fixed user-approved smoothed RGB reference; preserve original alpha",
    )
    a = p.parse_args()
    raise SystemExit(0 if validate(a.folder, a.output, a.smooth_color_reference)["pass"] else 1)
