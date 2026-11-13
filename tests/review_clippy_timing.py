"""Review exact source identities separately from reconstructed 60-fps samples."""

import argparse
import hashlib
import html
import json
import subprocess
from pathlib import Path

from clippy_all_catalog import ROOT, catalog
from clippy_playback_timeline import action_seed, samples, trace
from export_clippy_video import export
from overlay_clippy_3d import downsample, metrics, panels
from PIL import Image, ImageDraw
from review_clippy_3d import original_frames


def review(folder):
    m = json.loads((folder / "manifest.json").read_text())
    assert m["source_definition_sha256"] == hashlib.sha256((ROOT / "data/clippy/agent.js").read_bytes()).hexdigest()
    timing = json.loads((folder / "timing-verification.json").read_text())
    assert timing["pass_timing_and_pose_mapping"]
    assert timing["blend_sha256"] == hashlib.sha256((folder / "all-animations.blend").read_bytes()).hexdigest()
    assert timing["source_definition_sha256"] == m["source_definition_sha256"]
    results = {}
    for name, action in catalog().items():
        refs = original_frames(name)
        events = trace(action, seed=action_seed(name), stop_ms=m["stop_request_ms"])
        assert events == m["traces"][name]
        sequence = m["sequences"][name]
        expected = samples(events)
        assert len(expected) == len(sequence)
        hashes = set()
        for want, item in zip(expected, sequence, strict=True):
            assert all(item[k] == v for k, v in want.items())
            with Image.open(folder / item["file"]) as im:
                assert im.size == tuple(m["pixel_size"])
                hashes.add(hashlib.sha256(im.convert("RGBA").tobytes()).hexdigest())
        anchors = m["reference_anchors"][name]
        sheet = Image.new("RGB", (496, len(anchors) * 113), "#008080")
        draw = ImageDraw.Draw(sheet)
        checks = []
        for index, item in enumerate(anchors):
            assert item["source_index"] == index and item["source"] == action["frames"][index]
            reference, duration = refs[index]
            assert duration == item["source"]["duration"]
            with Image.open(folder / item["file"]) as im:
                candidate = downsample(im)
            score = metrics(reference, candidate)
            checks.append(
                dict(
                    source_index=index,
                    duration_ms=duration,
                    playback_frames=item["playback_frames"],
                    metrics=score,
                    reference_rgba_sha256=hashlib.sha256(reference.tobytes()).hexdigest(),
                )
            )
            draw.text((2, index * 113), f"{name} source {index}; {duration} ms", fill="white")
            for col, panel in enumerate(panels(reference, candidate)):
                sheet.paste(panel, (124 * col, index * 113 + 20))
        (folder / "comparisons").mkdir(exist_ok=True)
        sheet.save(folder / f"comparisons/{name}.png")
        video = folder / "videos" / name
        if not video.exists():
            export(folder, video, actions=[name], fps=60)
        checked = json.loads((video / "verification.json").read_text())
        assert checked["source_frame_repeats"] == [1] * len(sequence)
        assert checked["max_alpha_error"] == 0 and checked["mp4_fully_decoded"]
        # Side-by-side playback uses each sample's SOURCE identity, never the
        # dense output index as an index into the original atlas sequence.
        comparison = video / "source-comparison.mp4"
        if not comparison.exists():
            proc = subprocess.Popen(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-f",
                    "rawvideo",
                    "-pix_fmt",
                    "rgb24",
                    "-s",
                    "496x208",
                    "-r",
                    "60",
                    "-i",
                    "-",
                    "-an",
                    "-c:v",
                    "libx264",
                    "-crf",
                    "16",
                    "-pix_fmt",
                    "yuv420p",
                    "-threads",
                    "2",
                    str(comparison),
                ],
                stdin=subprocess.PIPE,
            )
            try:
                for item in sequence:
                    canvas = Image.new("RGB", (496, 208), "#008080")
                    ref = refs[item["source_index"]][0].resize((248, 186), Image.Resampling.NEAREST)
                    with Image.open(folder / item["file"]) as im:
                        candidate = im.convert("RGBA")
                    canvas.paste(ref, (0, 22), ref)
                    canvas.paste(candidate, (248, 22), candidate)
                    time = item["timestamp_numerator"] / item["timestamp_denominator"]
                    ImageDraw.Draw(canvas).text(
                        (3, 3), f"{name} | {time:.1f} ms | source {item['source_index']}", fill="white"
                    )
                    proc.stdin.write(canvas.tobytes())
            finally:
                proc.stdin.close()
            assert proc.wait() == 0
        decoded = json.loads(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-count_frames",
                    "-show_entries",
                    "stream=nb_read_frames,r_frame_rate",
                    "-of",
                    "json",
                    str(comparison),
                ]
            )
        )["streams"][0]
        assert int(decoded["nb_read_frames"]) == len(sequence) and decoded["r_frame_rate"] == "60/1"
        results[name] = dict(
            output_frames=len(sequence),
            distinct_rgba_frames=len(hashes),
            traced_duration_ms=sum(e["duration_ms"] for e in events),
            anchors=checks,
            timing_pass=True,
            source_match_pass=all(
                c["metrics"]["silhouette_iou"] >= 0.98 and c["metrics"]["foreground_color_similarity"] >= 0.98
                for c in checks
            ),
        )
        print("REVIEWED", name, len(sequence), flush=True)
    report = dict(
        actions=results,
        timing_pass=True,
        source_match_pass=all(a["source_match_pass"] for a in results.values()),
        scope="Source identity and path timestamps verified. Native-canvas anchor comparisons, "
        "60-fps exports and alpha checked. Intermediate geometry is not collision-certified.",
    )
    (folder / "source-timing-review.json").write_text(json.dumps(report, indent=2) + "\n")
    entries = "".join(
        f"<tr><td>{html.escape(n)}</td><td>{r['traced_duration_ms'] / 1000:.2f}s</td>"
        f'<td><a href="videos/{n}/source-comparison.mp4">Original / reconstructed</a> · '
        f'<a href="videos/{n}/clippy-transparent.webm">Transparent 60 fps</a> · '
        f'<a href="comparisons/{n}.png">Every source pose</a></td></tr>'
        for n, r in results.items()
    )
    (folder / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Clippy source-timed review</title>'
        "<style>body{font:16px system-ui;margin:24px}td{padding:8px}</style><h1>43 source-timed animations</h1>"
        "<p>Actual branch paths, exact source timestamps and 60-fps interpolation. Each preview requests a graceful "
        f"stop at {m['stop_request_ms'] / 1000:g} seconds; completion time depends on its exit path. "
        "These are 248×186 review renders.</p>"
        "<p>Long holds retain a still interval; "
        f"the final {m['tween_tail_ms']} ms may interpolate to the next pose. "
        "That motion is reconstructed, not encoded by the original data. Visibility remains discrete.</p>"
        "<p><strong>Timing passes; original-art fidelity is not accepted. "
        "Intermediate collisions remain unverified.</strong> "
        "Existing authored geometry is reused. Standalone art repairs and the installed assistant are not replaced.</p>"
        '<p><a href="source-timing-review.json">Source correspondence and visual scores</a> · '
        '<a href="timing-verification.json">Reopened Blender keyframe checks</a> · '
        '<a href="all-animations.blend">Editable 60-fps Blender timeline</a></p>'
        "<table><tr><th>Action</th><th>Traced duration</th><th>Review</th></tr>" + entries + "</table>"
    )
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path)
    review(p.parse_args().folder)
