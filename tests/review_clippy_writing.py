"""Native-resolution before/after evidence for the source-guided Writing clip."""

import argparse
import json
from pathlib import Path

import numpy as np
from clippy_acceptance import MATCH_THRESHOLD
from clippy_all_catalog import catalog
from export_clippy_video import export
from overlay_clippy_3d import downsample, metrics
from PIL import Image, ImageDraw
from review_clippy_3d import original_frames
from validate_clippy_fidelity import motion, spatial


def review(folder, before):
    manifest = json.loads((folder / "manifest.json").read_text())
    previous = json.loads((before / "manifest.json").read_text())
    verified = json.loads((folder / "writing-verification.json").read_text())
    assert verified["reopened_poses_checked"] == 61
    refs = original_frames("Writing")
    source = catalog()["Writing"]["frames"]
    sheet = Image.new("RGB", (4 * 496, 16 * 116), "#008080")
    draw = ImageDraw.Draw(sheet)
    comparison = folder / "comparison-frames"
    comparison.mkdir(exist_ok=True)
    rows = []
    compare_items = []
    last = None
    for i, (item, (ref, duration)) in enumerate(zip(manifest["sequences"]["Writing"], refs, strict=True)):
        assert item["duration_ms"] == duration and item["source"] == source[i]
        full = Image.open(folder / item["file"]).convert("RGBA")
        assert full.size == tuple(manifest["pixel_size"])
        alpha = np.asarray(full)[:, :, 3]
        assert alpha.any() and not any(e.any() for e in [alpha[0], alpha[-1], alpha[:, 0], alpha[:, -1]])
        new = downsample(full)
        old = downsample(Image.open(before / previous["sequences"]["Writing"][i]["file"]))
        old_score, new_score = metrics(ref, old), metrics(ref, new)
        image_check = spatial(ref, new)
        movement = motion(refs[i - 1][0], ref, last, new) if i else None
        passed = (
            all(new_score[k] >= MATCH_THRESHOLD for k in ["silhouette_iou", "foreground_color_similarity"])
            and image_check["pass"]
            and (movement is None or movement["pass"])
        )
        rows.append(
            {
                "source_index": i,
                "before": old_score,
                "after": new_score,
                "spatial": image_check,
                "motion": movement,
                "strict_98_pass": passed,
            }
        )
        overlay = Image.blend(ref.convert("RGBa"), new.convert("RGBa"), 0.5).convert("RGBA")
        x, y = i % 4 * 496, i // 4 * 116
        draw.text((x + 2, y + 2), f"{i}: source | before | candidate | overlay", fill="white")
        for col, im in enumerate([ref, old, new, overlay]):
            sheet.paste(im, (x + col * 124, y + 20), im)
        video = Image.new("RGBA", (1116, 300), "#008080")
        vd = ImageDraw.Draw(video)
        for col, (label, im) in enumerate(
            zip(["Original", "Previous reconstruction", "Source-guided candidate"], [ref, old, new], strict=True)
        ):
            vd.text((col * 372 + 5, 4), label, fill="white")
            large = im.resize((372, 279), Image.Resampling.NEAREST)
            video.alpha_composite(large, (col * 372, 21))
        filename = f"{i:03}.png"
        video.save(comparison / filename)
        compare_items.append({"file": filename, "duration_ms": duration})
        last = new
    sheet.save(folder / "comparison.png")
    report = {
        "pass": all(r["strict_98_pass"] for r in rows),
        "frames": 61,
        "strict_98_passing_frames": sum(r["strict_98_pass"] for r in rows),
        "mean_shape_before": float(np.mean([r["before"]["silhouette_iou"] for r in rows])),
        "mean_shape_after": float(np.mean([r["after"]["silhouette_iou"] for r in rows])),
        "shape_improved_frames": sum(r["after"]["silhouette_iou"] > r["before"]["silhouette_iou"] for r in rows),
        "scope": "Fixed original 124x93 canvas; no registration, image shifting, or background-dominated score.",
        "rows": rows,
    }
    assert report["mean_shape_after"] > report["mean_shape_before"], "Candidate did not improve source silhouette match"
    (folder / "source-match.json").write_text(json.dumps(report, indent=2) + "\n")
    (comparison / "manifest.json").write_text(
        json.dumps(
            {
                "pixel_size": [1116, 300],
                "status": "Native-resolution source/before/candidate comparison.",
                "sequences": {"Writing": compare_items},
            },
            indent=2,
        )
        + "\n"
    )
    if not (folder / "videos/Writing").exists():
        export(folder, folder / "videos/Writing", fps=60)
    if not (folder / "videos/comparison").exists():
        export(comparison, folder / "videos/comparison", fps=60)
    (
        folder / "index.html"
    ).write_text(f"""<!doctype html><meta charset="utf-8"><title>Writing — source comparison</title>
<style>body{{font:16px system-ui;max-width:1200px;margin:24px}}
video,img{{max-width:100%}}video{{background:#008080}}</style>
<h1>Writing — source-guided reconstruction</h1>
<p>61 source poses and original holds retained, with sound/branch metadata preserved in the manifest. Paper lifting,
pencil placement and the return now follow the source. The wire, folds and facial acting are still reconstructed.</p>
<p><strong>Not a finished 98% match:</strong>
{report["strict_98_passing_frames"]}/61 frames pass all strict image/motion gates.
Mean silhouette overlap: {report["mean_shape_before"]:.1%} before → {report["mean_shape_after"]:.1%} now.</p>
<h2>Original / previous / candidate at native resolution</h2>
<video src="videos/comparison/clippy-preview.mp4" controls loop playsinline></video>
<h2>HD candidate</h2>
<video src="videos/Writing/clippy-transparent.webm" controls loop playsinline></video>
<p><a href="videos/Writing/clippy-preview.mp4">Candidate MP4</a> ·
<a href="source-match.json">Per-frame source measurements</a> ·
<a href="writing-verification.json">Reopened geometry and source-prop checks</a> ·
<a href="all-animations.blend">Editable Blender candidate</a></p>
<p>The silent video holds source poses at 60 fps; it does not add intermediate motion or execute random branches.
The older combined library video is unchanged.</p>
<a href="comparison.png"><img src="comparison.png" alt="All source frames, before, after and overlays"></a>""")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
    return report["pass"]


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path)
    p.add_argument("--before", type=Path, required=True)
    a = p.parse_args()
    raise SystemExit(0 if review(a.folder, a.before) else 1)
