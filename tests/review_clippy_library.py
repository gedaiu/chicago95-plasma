"""Audit all original action frames and publish videos with native-size comparisons.

Technical completeness and original-image fidelity are deliberately separate results.
"""

import argparse
import html
import json
from pathlib import Path

import numpy as np
from clippy_acceptance import MATCH_THRESHOLD
from clippy_all_catalog import catalog
from clippy_show import bounds_error
from export_clippy_video import export
from PIL import Image, ImageDraw
from review_clippy_3d import original_frames


def audit(folder):
    manifest = json.loads((folder / "manifest.json").read_text())
    source = catalog()
    if set(manifest["sequences"]) != set(source):
        raise ValueError("Missing or extra original actions")
    baked = json.loads((folder / "bake-verification.json").read_text())
    if baked["failures"] or baked["poses"] != sum(len(a["frames"]) for a in source.values()):
        raise ValueError("Incomplete or failed baked-pose verification")
    comparisons = folder / "comparisons"
    comparisons.mkdir(exist_ok=True)
    reports = {}
    for name, items in manifest["sequences"].items():
        refs = original_frames(name)
        if len(items) != len(refs):
            raise ValueError(f"{name}: incorrect frame count")
        scores = []
        columns = 8
        sheet = Image.new("RGB", (columns * 372, ((len(items) + columns - 1) // columns) * 116), "#008080")
        draw = ImageDraw.Draw(sheet)
        for index, (item, (reference, duration)) in enumerate(zip(items, refs, strict=True)):
            if (
                item["source_index"] != index
                or item["duration_ms"] != duration
                or item["source"] != source[name]["frames"][index]
            ):
                raise ValueError(f"{name}/{index}: original timing, ordering or branch metadata changed")
            with Image.open(folder / item["file"]) as full:
                if full.mode != "RGBA" or full.size != tuple(manifest["pixel_size"]):
                    raise ValueError(f"{name}/{index}: malformed render")
                # Premultiplied filtering avoids dark halos in the low-resolution comparison.
                low = full.convert("RGBa").resize((124, 93), Image.Resampling.LANCZOS).convert("RGBA")
                alpha = np.asarray(full.getchannel("A"))
                border = np.concatenate([alpha[0], alpha[-1], alpha[:, 0], alpha[:, -1]])
                clipped = int(np.count_nonzero(border > 127))
                if clipped:
                    raise ValueError(f"{name}/{index}: opaque artwork clips the render border")
            a = np.asarray(low).astype(float) / 255
            if name in {"Show", "Hide"} and bounds_error(reference, low) > 1:
                raise ValueError(f"{name}/{index}: size or position differs from the source by more than one pixel")
            b = np.asarray(reference).astype(float) / 255
            am, bm = a[:, :, 3] > 0.5, b[:, :, 3] > 0.5
            union = am | bm
            iou = float(np.count_nonzero(am & bm) / np.count_nonzero(union)) if union.any() else 1.0
            rgb_error = np.abs(a[:, :, :3] * a[:, :, 3:] - b[:, :, :3] * b[:, :, 3:])
            color = 1 - float(rgb_error[union].mean()) if union.any() else 1.0
            scores.append(
                {
                    "index": index,
                    "silhouette_iou": iou,
                    "foreground_color_similarity": color,
                    "opaque_border_pixels": clipped,
                    "shape_color_pass": iou >= MATCH_THRESHOLD and color >= MATCH_THRESHOLD,
                }
            )
            overlay = Image.blend(reference.convert("RGBa"), low.convert("RGBa"), 0.5).convert("RGBA")
            x, y = index % columns * 372, index // columns * 116
            draw.text((x + 2, y + 2), f"{index}: original | new | 50% overlay", fill="white")
            for offset, picture in enumerate([reference, low, overlay]):
                sheet.paste(picture, (x + offset * 124, y + 20), picture)
        sheet.save(comparisons / f"{name}.png")
        reports[name] = {
            "frames": len(items),
            "duration_ms": sum(i["duration_ms"] for i in items),
            "shape_color_pass_frames": sum(s["shape_color_pass"] for s in scores),
            "scores": scores,
        }
        print("AUDITED", name, flush=True)
    report = {
        "actions": len(reports),
        "source_frames": baked["poses"],
        "frame_checks_pass": True,
        "technical_checks_pass": False,
        "fidelity_certified": False,
        "match_threshold": MATCH_THRESHOLD,
        "fidelity_note": (
            "Shape/color scores do not certify pose or 98% original fidelity. "
            "Videos preserve source holds but use reconstructed poses."
        ),
        "actions_detail": reports,
    }
    (folder / "library-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    return manifest, report


def gallery(folder, manifest, report):
    options = "".join(f"<option>{html.escape(n)}</option>" for n in manifest["sequences"])
    summary = "".join(
        f"<tr><td>{html.escape(n)}</td><td>{r['frames']}</td><td>{r['duration_ms'] / 1000:.2f}s</td>"
        f'<td><a href="videos/{n}/clippy-preview.mp4">MP4</a> · '
        f'<a href="videos/{n}/clippy-transparent.webm">WebM</a></td>'
        f'<td><a href="comparisons/{n}.png">Every frame + overlay</a></td></tr>'
        for n, r in report["actions_detail"].items()
    )
    page = """<!doctype html><html lang="en"><meta charset="utf-8"><title>Clippy animation library</title>
<style>
body{font:16px system-ui;max-width:1100px;margin:30px auto;background:#e9ecef;color:#17212a}
video{width:744px;max-width:100%;background:repeating-conic-gradient(#c4c4c4 0% 25%,#eee 0% 50%) 0/24px 24px}
select{font:inherit;padding:8px}
table{border-collapse:collapse;width:100%}
td,th{padding:8px;text-align:left;border-bottom:1px solid #bbb}
a{color:#164d8a}
p{line-height:1.5}</style>
<h1>Clippy — 43 reconstructed animations</h1>
<p>All original action names and frame holds are represented. 
These are authored Blender reconstructions, not a certified 98% reproduction. 
Exports hold the audited source poses at RATE fps; they do not interpolate new poses.
Frame boundaries are rounded to the nearest output frame without accumulating timing drift.
Source holds shorter than one output frame may be omitted from playback; every source pose
remains available in the frame comparisons below.
The videos follow linear source-frame order; 
runtime random branches are retained in the manifest but are not exercised here.</p>
<p><a href="videos/all/clippy-preview.mp4">Play all animations (MP4)</a> ·
<a href="videos/all/clippy-transparent.webm">All animations with transparency</a> ·
<a href="all-animations.blend">Editable Blender timeline</a> ·
<a href="library-verification.json">Frame audit</a></p>
EXTRAS
<label>Animation <select id="clip">OPTIONS</select></label>
<label>Speed <select id="speed"><option value="1">1×</option><option value="0.5">½×</option>
<option value="0.25">¼×</option></select></label><p><video id="player" controls loop playsinline></video></p>
<p id="links"></p><p id="transition-note"></p>
<table><thead><tr><th>Action</th><th>Source frames</th><th>Duration</th><th>Videos</th>
<th>Low-resolution comparison</th></tr></thead><tbody>ROWS</tbody></table>
<script>const clip=document.querySelector('#clip'),player=document.querySelector('#player');
function change(){player.loop=!['Show','Hide'].includes(clip.value);
player.src='videos/'+clip.value+'/clippy-transparent.webm';
document.querySelector('#transition-note').textContent=clip.value==='Show'
?'Show is a 50 ms entrance. Play once or slow playback; it finishes on the rest pose.'
:clip.value==='Hide'?'Hide is a 50 ms exit. Play once or slow playback; it finishes fully transparent.':'';
document.querySelector('#links').innerHTML='<a href="videos/'+clip.value+'/clippy-preview.mp4">Opaque MP4</a> · '+
'<a href="comparisons/'+clip.value+'.png">Original, new and overlay at 124 × 93</a>';}
clip.onchange=()=>{location.hash=clip.value;change();};
document.querySelector('#speed').onchange=event=>player.playbackRate=+event.target.value;
player.onloadedmetadata=()=>player.playbackRate=+document.querySelector('#speed').value;
const requested=location.hash.slice(1);
if([...clip.options].some(option=>option.value===requested))clip.value=requested;
change();</script></html>"""
    rates = ", ".join(str(rate) for rate in report["export_frame_rates"])
    extra_links = [
        ("../preview-getattention/index.html", "GetAttention: corrected collision review and video"),
        ("eye-rims-before-after.png", "Eye rims: before and after"),
        ("eyelid-verification.json", "Eyelid surface-separation regression"),
        ("show-layout-review.png", "Show: original, corrected and overlay"),
        ("show-layout-verification.json", "Show size and position check"),
        ("hide-layout-review.png", "Hide: original, corrected and overlay"),
        ("hide-layout-verification.json", "Hide size, position and disappearance check"),
        ("wire-collisions.html", "Wire surface audit"),
        ("collisions.html", "All recorded surface contacts"),
        ("validation/repaired-98/index.html", "98% source-match results"),
    ]
    extras = " · ".join(f'<a href="{path}">{label}</a>' for path, label in extra_links if (folder / path).exists())
    page = page.replace("OPTIONS", options).replace("ROWS", summary).replace("RATE", rates)
    (folder / "index.html").write_text(page.replace("EXTRAS", f"<p>{extras}</p>" if extras else ""))


def main(folder, shard=0, shards=1, review_only=False, fps=60):
    manifest = json.loads((folder / "manifest.json").read_text())
    if not review_only:
        for i, name in enumerate([*manifest["sequences"], "all"]):
            if i % shards != shard:
                continue
            output = folder / "videos" / name
            if (output / "verification.json").exists():
                continue
            export(folder, output, None if name == "all" else [name], fps=fps)
    else:
        manifest, report = audit(folder)
        rates = set()
        for name in [*manifest["sequences"], "all"]:
            verification = json.loads((folder / "videos" / name / "verification.json").read_text())
            expected = list(manifest["sequences"]) if name == "all" else [name]
            duration = sum(sum(i["duration_ms"] for i in manifest["sequences"][n]) for n in expected)
            source_duration = verification.get("source_duration_ms", round(verification["duration_seconds"] * 1000))
            rate = verification["fps"]
            rates.add(rate)
            if verification["actions"] != expected or source_duration != duration:
                raise ValueError(f"{name}: exported sequence/timing mismatch")
            if verification["frames"] != (duration * rate + 500) // 1000:
                raise ValueError(f"{name}: frame-rate conversion accumulated timing drift")
            if verification.get("max_boundary_error_ms", 0) > 500 / rate + 1e-6:
                raise ValueError(f"{name}: a frame boundary moved by more than half an output frame")
            if verification["max_alpha_error"] or not verification["mp4_fully_decoded"]:
                raise ValueError(f"{name}: video verification failed")
        report["technical_checks_pass"] = True
        report["verified_video_pairs"] = len(manifest["sequences"]) + 1
        report["export_frame_rates"] = sorted(rates)
        (folder / "library-verification.json").write_text(json.dumps(report, indent=2) + "\n")
        gallery(folder, manifest, report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--review-only", action="store_true")
    parser.add_argument("--fps", type=int, default=60)
    args = parser.parse_args()
    main(args.folder, args.shard, args.shards, args.review_only, args.fps)
