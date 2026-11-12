"""Repair each keyed wire pose, re-check the baked result, and prepare fresh renders."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_clippy_collisions import self_intersections, surface  # noqa: E402
from build_clippy_3d_library import snapshot  # noqa: E402
from clippy_render_quality import configure  # noqa: E402
from repair_clippy_wire import repair  # noqa: E402


def state_error(a, b):
    if isinstance(a, dict):
        return max((state_error(a[k], b[k]) for k in a), default=0) if a.keys() == b.keys() else float("inf")
    if isinstance(a, list):
        if len(a) != len(b):
            return float("inf")
        return max((state_error(x, y) for x, y in zip(a, b, strict=True)), default=0)
    if isinstance(a, str):
        return 0 if a == b else float("inf")
    return abs(a - b)


def main(blend, manifest_path, output):
    output.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    manifest = json.loads(manifest_path.read_text())
    scene = bpy.context.scene
    configure(scene)
    manifest["samples"] = scene.cycles.samples
    manifest["render_quality"] = {"smooth_eyelids": True, "denoising": True, "samples": scene.cycles.samples}
    wire = bpy.data.objects["MorphWire"]
    objects = [o for o in bpy.data.objects if o.type in ("MESH", "CURVE", "ARMATURE")]
    lib = SimpleNamespace(
        rig=bpy.data.objects["Armature"],
        morph=wire,
        paper=bpy.data.objects["Plane"],
        curve_points=wire.data.splines[0].points,
    )
    repairs, cache, expected = [], {}, {}
    for name, items in manifest["sequences"].items():
        for index, item in enumerate(items):
            scene.frame_set(item["frame"])
            bpy.context.view_layer.update()
            if not wire.hide_render:
                key = tuple(tuple(p.co) + (p.radius,) for p in wire.data.splines[0].points)
                if key not in cache:
                    cache[key] = repair(wire, scene.camera)
                fixed, info = cache[key]
                if info["initial_triangle_pairs"]:
                    if fixed is not None:
                        for point, (co, radius) in zip(wire.data.splines[0].points, fixed, strict=True):
                            point.co, point.radius = co, radius
                            point.keyframe_insert("co", frame=item["frame"])
                            point.keyframe_insert("radius", frame=item["frame"])
                        wire.data.update_tag()
                        bpy.context.view_layer.update()
                    repairs.append({"action": name, "source_index": index, "frame": item["frame"], **info})
            expected[item["frame"]] = snapshot(lib, objects)
        print("REPAIRED", name, flush=True)
    failures, render_cache, maximum_error = [], {}, 0
    for name, items in manifest["sequences"].items():
        for index, item in enumerate(items):
            scene.frame_set(item["frame"])
            bpy.context.view_layer.update()
            actual = snapshot(lib, objects)
            error = state_error(actual, expected[item["frame"]])
            maximum_error = max(maximum_error, error)
            if error > 0.000011:
                channels = {
                    k: state_error(actual[k], expected[item["frame"]][k])
                    for k in actual
                    if state_error(actual[k], expected[item["frame"]][k]) > 0.000011
                }
                raise RuntimeError(f"Baked pose changed: {name}/{index}: {channels}")
            for obj_name in ["Vert", "MorphWire"]:
                obj = bpy.data.objects[obj_name]
                if not obj.hide_render:
                    tree, topology = surface(obj, bpy.context.evaluated_depsgraph_get())
                    if self_intersections(tree, topology):
                        failures.append({"action": name, "source_index": index, "object": obj_name})
            signature = hashlib.sha256(json.dumps(snapshot(lib, objects, True), sort_keys=True).encode()).hexdigest()
            item["pose_signature"] = signature
            item["file"] = render_cache.setdefault(signature, f"{name}/{index:03d}.png")
    report = {
        "source_blend_sha256": hashlib.sha256(blend.read_bytes()).hexdigest(),
        "poses_checked": sum(map(len, manifest["sequences"].values())),
        "repairs": repairs,
        "remaining_wire_failures": failures,
        "baked_states_verified": True,
        "maximum_bake_roundtrip_error": maximum_error,
    }
    (output / "wire-repair.json").write_text(json.dumps(report, indent=2) + "\n")
    if failures:
        print("WIRE FAILURES REMAIN", len(failures), flush=True)
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "all-animations.blend"), compress=True)
    manifest["unique_render_frames"] = len(render_cache)
    manifest["status"] = "Wire repair candidate; rendered fidelity and all other contacts require review."
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "bake-verification.json").write_text(
        json.dumps({"poses": report["poses_checked"], "failures": []}) + "\n"
    )
    print("FINISHED", len(repairs), "repaired poses;", len(failures), "wire failures", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--blend", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    main(a.blend, a.manifest, a.output)
