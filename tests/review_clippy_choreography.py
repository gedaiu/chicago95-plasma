"""Publish original-only storyboards and a semantic gap list before keyframe editing."""

import argparse
import hashlib
import html
import json
import math
from pathlib import Path

from clippy_acceptance import completion_status
from clippy_all_catalog import ROOT, catalog
from clippy_branch_coverage import routes
from clippy_choreography import study, validate_studies
from PIL import Image, ImageDraw
from review_clippy_3d import original_frames


def build(output, collisions):
    output.mkdir(parents=True, exist_ok=True)
    actions = catalog()
    validate_studies(actions)
    reports = {}
    links = []
    collision = json.loads(collisions.read_text())
    for name in actions:
        beats = study(name)
        if beats is None:
            reports[name] = {"study_status": "not yet reviewed in detail", "semantic_acceptance": False}
            continue
        refs = original_frames(name)
        sheet = Image.new("RGB", (8 * 124, math.ceil(len(refs) / 8) * 113), "#008080")
        draw = ImageDraw.Draw(sheet)
        for index, (image, duration) in enumerate(refs):
            x = index % 8 * 124
            y = index // 8 * 113
            draw.text((x + 2, y + 2), f"{index}: {duration} ms", fill="white")
            sheet.paste(image, (x, y + 20), image)
        sheet.save(output / f"{name}.png")
        rows = [
            dict(
                start_source_index=a,
                end_source_index=b,
                title=t,
                observation=o,
                source_frames=[
                    dict(
                        index=i,
                        metadata=actions[name]["frames"][i],
                        rgba_sha256=hashlib.sha256(refs[i][0].tobytes()).hexdigest(),
                    )
                    for i in range(a, b + 1)
                ],
            )
            for a, b, t, o in beats
        ]
        reports[name] = dict(
            study_status="source beats reviewed; authoring not accepted",
            semantic_acceptance=False,
            beats=rows,
            collision_summary=collision["summary"][name],
            branch_coverage=routes(actions[name]),
        )
        body = "".join(
            f"<tr><td>{a}–{b}</td><td>{html.escape(t)}</td><td>{html.escape(o)}</td></tr>" for a, b, t, o in beats
        )
        (output / f"{name}.html").write_text(
            '<!doctype html><meta charset="utf-8">' + f"<title>{name} source study</title>"
            "<style>body{font:16px system-ui;margin:24px}td{padding:8px}img{max-width:100%}</style>"
            f"<h1>{name}: original source study</h1><p>Frame numbers below refer to the original atlas sequence. "
            "This sheet includes alternatives and exit poses, not a single linear playback path.</p>"
            "<p><strong>New artwork is not accepted.</strong> Each beat must be authored "
            "and checked before promotion.</p>"
            "<table><tr><th>Source frames</th><th>Beat</th><th>Observed action</th></tr>" + body + "</table>"
            f'<img src="{name}.png" alt="Every original frame with its display duration">'
        )
        links.append(f'<li><a href="{name}.html">{name}</a></li>')
    report = dict(
        source_definition_sha256=hashlib.sha256((ROOT / "data/clippy/agent.js").read_bytes()).hexdigest(),
        source_atlas_sha256=hashlib.sha256((ROOT / "data/clippy/map.png").read_bytes()).hexdigest(),
        actions=reports,
        semantic_acceptance=False,
        acceptance_requirements=[
            "Every source beat represented, including prop deformation and relative motion",
            "Source timestamps, branch choices, holds, and exit paths retained",
            "Per-eye blink/gaze poses checked rather than periodic procedural blinking",
            "Source-frame image comparisons and intermediate collision checks pass",
        ],
    )
    (output / "completion.json").write_text(json.dumps(completion_status(actions, {}), indent=2) + "\n")
    (output / "choreography.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "collisions.json").write_text(json.dumps(collision, indent=2) + "\n")
    (output / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Clippy choreography study</title>'
        "<style>body{font:16px system-ui;margin:24px;max-width:1000px}</style>"
        "<h1>Original choreography, before keyframe changes</h1>"
        "<p>The current 3D recipes omit major transformations and prop interactions. Correct timing "
        "does not repair those gaps. "
        "No animations have passed semantic acceptance. All 43 source entries are studied here; "
        "none has passed reconstruction acceptance.</p>"
        "<ul>" + "".join(links) + '</ul><p><a href="choreography.json">Source beats and acceptance gaps</a> · '
        '<a href="collisions.json">All 9,227 output-sample surface checks</a> · '
        '<a href="completion.json">Completion gates: 0/43 accepted</a></p>'
        "<p>Collision counts include contacts still requiring classification, not only "
        "confirmed unintended penetrations. "
        "These checks do not certify containment or motion between samples.</p>"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--collisions", type=Path, required=True)
    a = p.parse_args()
    build(a.output, a.collisions)
