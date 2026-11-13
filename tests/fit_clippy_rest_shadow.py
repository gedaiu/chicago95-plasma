"""Search body-light directions for the reference's displaced cast-shadow pattern."""

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def fit(folder, python):
    bpy.ops.wm.open_mainfile(filepath=str(folder / "rest-after-wire-color.blend"))
    s = bpy.context.scene
    s.render.use_persistent_data = True
    s.cycles.samples = 64
    s.cycles.use_animated_seed = False
    key = bpy.data.objects["key"]
    paper = bpy.data.objects["Plane"]
    camera = s.camera
    points = [paper.matrix_world @ v.co for v in paper.data.vertices]
    target = sum(points, Vector()) / len(points)
    normal = sum((paper.matrix_world.to_3x3() @ p.normal for p in paper.data.polygons), Vector()).normalized()
    if normal.dot(camera.matrix_world.translation - target) < 0:
        normal = -normal
    original = dict(matrix=[list(r) for r in key.matrix_world], energy=key.data.energy, size=key.data.size)
    original_distance = (key.location - target).length
    original_cosine = max(0.2, normal.dot((key.location - target).normalized()))
    basis = camera.matrix_world.to_3x3()
    trials = []

    def snapshot():
        return dict(
            location=list(key.location), rotation=list(key.rotation_euler), energy=key.data.energy, size=key.data.size
        )

    def restore(v):
        key.location = v["location"]
        key.rotation_euler = v["rotation"]
        key.data.energy = v["energy"]
        key.data.size = v["size"]
        bpy.context.view_layer.update()

    def render():
        s.render.filepath = str(folder / "shadow-search.png")
        bpy.ops.render.render(write_still=True)
        return json.loads(
            subprocess.check_output(
                [
                    python,
                    str(Path(__file__).with_name("score_clippy_rest_fit.py")),
                    str(folder / "reference.png"),
                    s.render.filepath,
                ],
                text=True,
            )
        )

    best = initial = render()
    best_light = snapshot()
    for yaw_degrees in (-70, -50, -30, -10, 10):
        yaw = math.radians(yaw_degrees)
        for elevation_degrees in (20, 40, 60):
            elevation = math.radians(elevation_degrees)
            direction = basis @ Vector(
                (math.sin(yaw) * math.cos(elevation), math.sin(elevation), math.cos(yaw) * math.cos(elevation))
            )
            key.location = target + direction * 12
            key.rotation_euler = (target - key.location).to_track_quat("-Z", "Y").to_euler()
            key.data.energy = (
                original["energy"] * (12 / original_distance) ** 2 * original_cosine / max(0.2, normal.dot(direction))
            )
            for size in (0.5, 2.0):
                key.data.size = size
                bpy.context.view_layer.update()
                measured = render()
                row = dict(yaw=yaw_degrees, elevation=elevation_degrees, size=size, metrics=measured, light=snapshot())
                trials.append(row)
                if measured["smoothed_reference_color_similarity"] > best["smoothed_reference_color_similarity"] + 1e-6:
                    best, best_light = measured, snapshot()
        print("SHADOW FIT", yaw_degrees, best, best_light, flush=True)
        # Preserve a resumable actual best scene rather than just its scalar score.
        restore(best_light)
        bpy.ops.wm.save_as_mainfile(filepath=str(folder / "rest-after-shadow.blend"), compress=True)
        (folder / "fitted-shadow.json").write_text(
            json.dumps(
                dict(initial=initial, best_fit=best, best_light=best_light, trials=trials, animation_accepted=False),
                indent=2,
            )
            + "\n"
        )
    restore(best_light)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "rest-after-shadow.blend"), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(folder / "rest-after-shadow.blend"))
    bpy.context.scene.render.filepath = str(folder / "after-shadow.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--python", required=True)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    fit(a.folder, a.python)
