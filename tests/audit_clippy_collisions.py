"""Inspect evaluated Blender surfaces at every source keyframe.

No sampled-centerline proxy: self-intersection tests operate on final triangles.
Shared (including duplicated cap-seam) vertices are excluded from self contacts.
Explicit source eye/socket construction contacts remain visible in the report;
all other object contacts require review, not an automatic whitelist pass.
"""

import argparse
import hashlib
import html
import json
import sys
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree

EYE_COMPONENTS = [{"Cube.001", "Cube.002", "Cube.003"}, {"Cube.004", "Cube.005", "Cube.006"}]
EYE_PARTS = set.union(*EYE_COMPONENTS) | {"Vert.001", "Vert.002"}
WIRES = {"Vert", "MorphWire"}


def surface(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        vertices = [evaluated.matrix_world @ v.co for v in mesh.vertices]
        faces = [tuple(t.vertices) for t in mesh.loop_triangles]
        # Curve end caps duplicate boundary vertices. A touching seam is not penetration.
        welded = [tuple(round(c, 6) for c in v) for v in vertices]
        topology = [frozenset(welded[i] for i in face) for face in faces]
        tree = BVHTree.FromPolygons(vertices, faces, all_triangles=True, epsilon=0)
        return tree, topology
    finally:
        evaluated.to_mesh_clear()


def contact_kind(a, b):
    pair = {a, b}
    if any(pair <= eye for eye in EYE_COMPONENTS):
        return "source_eye_assembly"
    if (a in WIRES and b in EYE_PARTS) or (b in WIRES and a in EYE_PARTS):
        return "eye_wire_attachment_review"
    if pair == {"Pencil", "Graphite"}:
        return "pencil_tip_join_review"
    return "penetration_review"


def self_intersections(tree, topology):
    return [(a, b) for a, b in tree.overlap(tree) if a < b and not topology[a] & topology[b]]


def inspect_pose(wire_only=False):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    objects = [o for o in bpy.data.objects if o.type in ("MESH", "CURVE") and not o.hide_render]
    if wire_only:
        objects = [o for o in objects if o.name in WIRES]
    surfaces = {o.name: surface(o, depsgraph) for o in objects}
    self_contacts, contacts = [], []
    for name, (tree, topology) in surfaces.items():
        hits = self_intersections(tree, topology)
        if hits:
            self_contacts.append(
                {
                    "object": name,
                    "triangle_pairs": len(hits),
                    "examples": hits[:8],
                    "kind": "source_pupil_eye_join_review"
                    if name in {"Cube.001", "Cube.004"}
                    else "surface_self_intersection",
                }
            )
    names = list(surfaces)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            hits = surfaces[a][0].overlap(surfaces[b][0])
            if hits:
                contacts.append(
                    {"objects": [a, b], "kind": contact_kind(a, b), "triangle_pairs": len(hits), "examples": hits[:4]}
                )
    return {"self_intersections": self_contacts, "object_contacts": contacts}


def audit(blend, manifest, output, wire_only=False):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    source = json.loads(manifest.read_text())
    actions = {}
    for name, items in source["sequences"].items():
        rows = []
        for index, item in enumerate(items):
            bpy.context.scene.frame_set(item["frame"])
            bpy.context.view_layer.update()
            rows.append({"source_index": index, "timeline_frame": item["frame"], **inspect_pose(wire_only)})
        actions[name] = rows
        print("AUDITED", name, "self-intersecting poses", sum(bool(r["self_intersections"]) for r in rows), flush=True)
    rows = [r for action in actions.values() for r in action]
    report = {
        "blend_sha256": hashlib.sha256(blend.read_bytes()).hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "actions": len(actions),
        "poses": len(rows),
        "poses_with_self_intersections": sum(bool(r["self_intersections"]) for r in rows),
        "poses_with_wire_self_intersections": sum(
            any(s["object"] in WIRES for s in r["self_intersections"]) for r in rows
        ),
        "collision_free_certified": False,
        "wire_only": wire_only,
        "scope": "Evaluated triangle-surface intersections at every source keyframe. Shared seam vertices excluded. "
        "Contacts are recorded, including intended eye construction. Containment and inter-keyframe motion "
        "are not certified; this report must not be represented as a complete collision-free proof.",
        "sequences": actions,
    }
    if wire_only:
        report["scope"] = "WIRE OBJECTS ONLY; eye, eyelid and prop contacts were not tested. " + report["scope"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    write_review(report, output.with_suffix(".html"))
    print(json.dumps({k: v for k, v in report.items() if k != "sequences"}, indent=2))
    return report


def write_review(report, output):
    rows = []
    for name, poses in report["sequences"].items():
        wire = [str(p["source_index"]) for p in poses if any(s["object"] in WIRES for s in p["self_intersections"])]
        props = sorted(
            {
                s["object"]
                for p in poses
                for s in p["self_intersections"]
                if s["object"] not in WIRES | {"Cube.001", "Cube.004"}
            }
        )
        rows.append(
            f"<tr><td>{html.escape(name)}</td><td>{len(poses)}</td><td>{len(wire)}</td>"
            f"<td>{', '.join(wire) or '—'}</td><td>{', '.join(props) or '—'}</td></tr>"
        )
    output.write_text(
        '<!doctype html><meta charset="utf-8"><title>Clippy surface-collision review</title>'
        "<style>body{font:16px system-ui;margin:30px}td,th{padding:8px;text-align:left;"
        "border-bottom:1px solid #ddd}td:nth-child(4){max-width:500px}</style>"
        "<h1>Clippy surface-collision review</h1>"
        f"<p>Checked {report['poses']} source keyframes across {report['actions']} actions. "
        f"{report['poses_with_wire_self_intersections']} poses have wire self-intersections.</p>"
        f"<p>{html.escape(report['scope'])}</p>"
        "<p>Frame numbers are zero-based source indices. Eye/pupil and eyelid construction contacts "
        "are recorded separately; no blanket collision-free certification is issued.</p>"
        "<p>Triangle-surface tests do not certify containment or motion between keyframes.</p>"
        f'<p><a href="{html.escape(output.with_suffix(".json").name)}">Full per-frame contact report</a></p>'
        "<table><tr><th>Action</th><th>Keyframes</th><th>Wire failures</th><th>Failing frames</th>"
        "<th>Other self-intersecting props</th></tr>" + "".join(rows) + "</table>"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--blend", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--require-no-wire-intersections", action="store_true")
    p.add_argument("--wire-only", action="store_true", help="Restrict this audit to wire surfaces; omit other contacts")
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    report = audit(a.blend, a.manifest, a.output, a.wire_only)
    if a.require_no_wire_intersections and report["poses_with_wire_self_intersections"]:
        raise SystemExit("FAILED: evaluated wire surfaces intersect; see the per-keyframe report")
