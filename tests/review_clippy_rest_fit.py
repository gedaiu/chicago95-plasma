"""Publish measured calibration candidates, including regressions and failures."""

import argparse
import hashlib
import html
import json
import shutil
from pathlib import Path

from clippy_acceptance import MATCH_THRESHOLD
from clippy_reference_color import COLOR_REFERENCE_POLICY, smooth_reference_color
from overlay_clippy_3d import downsample, panels, presentation
from PIL import Image
from review_clippy_3d import original_frames
from score_clippy_rest_fit import score

STAGES = [
    ("before", "rest-before", "Original 3D candidate"),
    ("after", "rest-after", "Paper outline"),
    ("after-wire", "rest-after-wire", "Wire outline and thickness"),
    ("after-materials", "rest-after-materials", "Materials"),
    ("after-surface", "rest-after-surface", "Paper surface experiment"),
    ("after-eyes", "rest-after-eyes", "Eye geometry, full-resolution fitting"),
    ("after-materials-hd", "rest-after-materials-hd", "Materials, full-resolution fitting"),
    ("after-lighting", "rest-after-lighting", "Body light direction, softness and energy"),
    ("after-paper-depth", "rest-after-paper-depth", "Paper distance and cast shadows"),
    ("after-shape", "rest-after-shape", "Paper and wire vertex fitting"),
    ("after-shape-detail", "rest-after-shape-detail", "Local wire thickness fitting"),
    ("after-face-depth", "rest-after-face-depth", "Face/wire intersection correction"),
    ("after-face-shape", "rest-after-face-shape", "Eye and eyebrow outlines"),
    ("after-wire-detail", "rest-after-wire-detail", "Posed wire geometry refinement"),
    ("after-paper-ruling", "rest-after-paper-ruling", "Paper ruling frequency and contrast"),
    ("after-surface-hd", "rest-after-surface-hd", "Paper curvature from render differences"),
    ("after-wire-color", "rest-after-wire-color", "Internal wire pose from color evidence"),
    ("after-shadow", "rest-after-shadow", "Wider cast-shadow lighting search"),
    ("after-paper-color", "rest-after-paper-color", "Interpolated paper vertex colors"),
    ("after-metal", "rest-after-metal", "Joint metal material calibration"),
    ("after-paper-field", "rest-after-paper-field", "Smooth procedural paper color field"),
    ("after-paper-uv", "rest-after-paper-uv", "Paper ruling placement"),
    ("after-pupils", "rest-after-pupils", "Independent pupil placement"),
    ("after-paper-fine-field", "rest-after-paper-fine-field", "Refined smooth paper color field"),
    ("after-wire-light", "rest-after-wire-light", "Separate wire lighting experiment"),
    ("after-face-light", "rest-after-face-light", "Face lighting experiment"),
]


def review(folder, output, requested_stage=None):
    output.mkdir(parents=True, exist_ok=True)
    reference = Image.open(folder / "reference.png").convert("RGBA")
    actual_source = original_frames("RestPose")[0][0].convert("RGBA")
    if reference.size != actual_source.size or reference.tobytes() != actual_source.tobytes():
        raise ValueError("Reference must be the unmodified RestPose source frame")
    reference.save(output / "reference.png")
    color_reference = smooth_reference_color(reference)
    color_reference.save(output / "reference-smoothed-color.png")
    rows, sections, best = [], [], None
    selected_master = None
    candidate_master = None
    for stem, master, label in STAGES:
        source = folder / (stem + ".png")
        if not source.exists():
            continue
        full_render = Image.open(source)
        if full_render.size != (744, 558):
            raise ValueError(f"Independent full-resolution render required: {source}")
        candidate = downsample(full_render)
        measured = score(folder / "reference.png", source)
        improvement = best is None or all(
            measured[key] >= best[key] for key in ("silhouette_iou", "smoothed_reference_color_similarity")
        )
        if improvement:
            best = measured
            selected_master = folder / (master + ".blend")
        if stem == requested_stage:
            candidate_master = folder / (master + ".blend")
        image_gate = all(
            measured[key] >= MATCH_THRESHOLD for key in ("silhouette_iou", "smoothed_reference_color_similarity")
        )
        row = dict(
            stage=stem,
            label=label,
            measurements=measured,
            nonregressing_candidate=improvement,
            image_gate_pass=image_gate,
            animation_accepted=False,
            render_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            master_sha256=hashlib.sha256((folder / (master + ".blend")).read_bytes()).hexdigest(),
        )
        rows.append(row)
        fit_report = folder / ("fitted-" + stem.removeprefix("after-") + ".json")
        if fit_report.exists():
            shutil.copy2(fit_report, output / fit_report.name)
            row["fitting_report"] = fit_report.name
        presentation(panels(reference, candidate), label).save(output / (stem + "-comparison.png"))
        presentation(panels(color_reference, candidate), label + " — approved smoothed-color reference").save(
            output / (stem + "-color-comparison.png")
        )
        shutil.copy2(source, output / source.name)
        candidate.save(output / (stem + "-native.png"))
        status = "FAIL" if not image_gate else "Image metrics only; other gates unverified"
        sections.append(
            f"<h2>{html.escape(label)}</h2><p>Shape {measured['silhouette_iou']:.2%}; "
            f"smoothed-reference color {measured['smoothed_reference_color_similarity']:.2%}; "
            f"raw color {measured['foreground_color_similarity']:.2%}. {status}. "
            f"{'' if improvement else 'Trades off a measured metric; not an acceptance pass.'}</p>"
            f'<a href="{stem}.png">Full-resolution render</a>'
            f' · <a href="{stem}-color-comparison.png">Smoothed-color comparison</a>'
            f'<img src="{stem}-comparison.png" alt="Original, candidate, overlay, difference">'
        )
    report = dict(
        threshold=MATCH_THRESHOLD,
        accepted_animations=0,
        total_animations=43,
        scope="Isolated RestPose calibration; no runtime or library replacement.",
        stages=rows,
        color_reference_policy=COLOR_REFERENCE_POLICY,
    )
    if requested_stage is not None:
        if candidate_master is None:
            raise ValueError(f"Missing requested authoring candidate: {requested_stage}")
        selected_master = candidate_master
        report["authoring_candidate"] = requested_stage
    if selected_master is not None:
        shutil.copy2(selected_master, output / "rest-candidate.blend")
        report["selected_master"] = selected_master.name
    (output / "measurements.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Clippy rest calibration — unfinished</title>'
        "<style>body{background:#202020;color:#eee;font:16px sans-serif;margin:24px}"
        "img{display:block;max-width:100%}a{color:#9df}</style>"
        "<h1>Rest-pose calibration — unfinished</h1>"
        "<p>0/43 animations accepted. This page covers one shared source pose only. "
        "Every image is independently rendered at 744×558 then reduced to 124×93. "
        "No registration, crop, sprite projection, or threshold reduction. "
        "Original silhouette and smoothed-reference color scores must both reach 98%. "
        "The approved color reference uses a fixed alpha-normalized Gaussian sigma of 0.5 native pixels; "
        "source alpha is unchanged and candidates are never blurred. Raw color scores remain visible. "
        "choreography, timing, blinks, and collisions remain separate requirements.</p>"
        '<a href="measurements.json">Measurements and artifact hashes</a> · '
        '<a href="rest-candidate.blend">Unfinished Blender candidate</a>' + "".join(sections)
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--candidate", help="Explicit unfinished authoring stage; does not override acceptance gates")
    args = parser.parse_args()
    review(args.folder, args.output, args.candidate)
