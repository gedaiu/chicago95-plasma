"""Blender regression: open eyelid shells must not compete for the same visible surface.

Reproduce the source defect by undoing the tiny lower-shell inset in memory, then
check actual ray/surface distances after applying the production correction.
The saved Blender file is never changed.
"""

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_clippy_collisions import surface  # noqa: E402
from clippy_render_quality import LOWER_EYELIDS, configure  # noqa: E402


def measure(scene, names, bounds):
    deps = bpy.context.evaluated_depsgraph_get()
    trees = {name: surface(bpy.data.objects[name], deps)[0] for name in names}
    camera = scene.camera
    origin = camera.matrix_world.translation
    corners = camera.data.view_frame(scene=scene)
    xmin, xmax = min(v.x for v in corners), max(v.x for v in corners)
    ymin, ymax = min(v.y for v in corners), max(v.y for v in corners)
    left, top, right, bottom = bounds
    gaps = []
    for y in range(top, bottom):
        for x in range(left, right):
            local = Vector((xmin + (xmax - xmin) * x / 1488, ymax - (ymax - ymin) * y / 1116, corners[0].z))
            direction = (camera.matrix_world.to_3x3() @ local).normalized()
            eye, upper, lower = [trees[name].ray_cast(origin, direction)[3] for name in names]
            if upper is not None and lower is not None and (eye is None or min(upper, lower) < eye):
                gaps.append(abs(upper - lower))
    return {
        "visible_overlap_rays": len(gaps),
        "near_coincident_rays": sum(gap < 0.0001 for gap in gaps),
        "minimum_surface_gap": min(gaps) if gaps else None,
    }


def check(folder, output):
    manifest = json.loads((folder / "manifest.json").read_text())
    bpy.ops.wm.open_mainfile(filepath=str(folder / "all-animations.blend"))
    scene = bpy.context.scene
    scene.frame_set(manifest["sequences"]["RestPose"][0]["frame"])
    for name in LOWER_EYELIDS:
        mesh = bpy.data.objects[name].data
        factor = mesh.get("clippy_lower_shell_scale", 1.0)
        for vertex in mesh.vertices:
            vertex.co /= factor
        mesh["clippy_lower_shell_scale"] = 1.0
    cases = [
        (("Cube.001", "Cube.002", "Cube.003"), (440, 250, 670, 420)),
        (("Cube.004", "Cube.005", "Cube.006"), (670, 310, 885, 480)),
    ]
    bpy.context.view_layer.update()
    before = [measure(scene, names, bounds) for names, bounds in cases]
    configure(scene)
    bpy.context.view_layer.update()
    after = [measure(scene, names, bounds) for names, bounds in cases]
    for original, corrected in zip(before, after, strict=True):
        assert original["visible_overlap_rays"] > 100, "Fixture no longer samples the metal rim"
        assert original["near_coincident_rays"] / original["visible_overlap_rays"] > 0.9
        assert corrected["visible_overlap_rays"] > 100
        assert corrected["near_coincident_rays"] == 0, corrected
    coordinates = [[tuple(v.co) for v in bpy.data.objects[name].data.vertices] for name in LOWER_EYELIDS]
    configure(scene)
    assert coordinates == [[tuple(v.co) for v in bpy.data.objects[name].data.vertices] for name in LOWER_EYELIDS]
    report = {
        "pass": True,
        "before": before,
        "after": after,
        "idempotent": True,
        "scope": "Visible open-eye rim separation; this is not a general collision or source-fidelity certificate.",
    }
    if output:
        output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    check(args.folder, args.output)
