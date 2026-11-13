"""Calibrate wire highlights independently of the paper and eye lighting."""

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def fit(folder, python, face=False):
    suffix = "face-light" if face else "wire-light"
    bpy.ops.wm.open_mainfile(filepath=str(folder / "rest-after-paper-fine-field.blend"))
    s = bpy.context.scene
    s.render.use_persistent_data = True
    s.cycles.samples = 64
    s.cycles.use_animated_seed = False
    wire = bpy.data.objects["Vert"]
    if face:
        key = bpy.data.objects["Face key"]
    else:
        receivers = bpy.data.collections.new("Clippy calibrated wire receivers")
        receivers.objects.link(wire)
        for name in ("key", "fill"):
            original = bpy.data.objects[name]
            copy = original.copy()
            copy.data = original.data.copy()
            copy.name = "Wire " + name
            s.collection.objects.link(copy)
            copy.light_linking.receiver_collection = receivers
            body = original.light_linking.receiver_collection
            if body is None:
                raise ValueError("Expected explicit body receivers")
            if wire.name in body.objects:
                body.objects.unlink(wire)
        key = bpy.data.objects["Wire key"]
    camera = s.camera
    basis = camera.matrix_world.to_3x3()
    subjects = [bpy.data.objects[n] for n in ("Cube.001", "Cube.004")] if face else [wire]
    points = [o.matrix_world @ v.co for o in subjects for v in o.data.vertices]
    target = sum(points, Vector()) / len(points)
    distance = (key.location - target).length
    original_energy = key.data.energy
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
        s.render.filepath = str(folder / "wire-light-search.png")
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

    initial = best = render()
    best_light = snapshot()
    for yaw_degrees in (-45, 0, 45):
        yaw = math.radians(yaw_degrees)
        for elevation_degrees in (15, 45):
            elevation = math.radians(elevation_degrees)
            direction = basis @ Vector(
                (math.sin(yaw) * math.cos(elevation), math.sin(elevation), math.cos(yaw) * math.cos(elevation))
            )
            key.location = target + direction * distance
            key.rotation_euler = (target - key.location).to_track_quat("-Z", "Y").to_euler()
            for energy_scale in (1.0, 3.0):
                key.data.energy = original_energy * energy_scale
                for size in (0.5, 3.0):
                    key.data.size = size
                    bpy.context.view_layer.update()
                    measured = render()
                    trials.append(
                        dict(
                            yaw=yaw_degrees,
                            elevation=elevation_degrees,
                            energy_scale=energy_scale,
                            size=size,
                            metrics=measured,
                        )
                    )
                    if (
                        measured["smoothed_reference_color_similarity"]
                        > best["smoothed_reference_color_similarity"] + 1e-5
                    ):
                        best, best_light = measured, snapshot()
        print("WIRE LIGHT", yaw_degrees, best, best_light, flush=True)
    restore(best_light)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / f"rest-after-{suffix}.blend"), compress=True)
    (folder / f"fitted-{suffix}.json").write_text(
        json.dumps(
            dict(initial=initial, best_fit=best, light=best_light, trials=trials, animation_accepted=False), indent=2
        )
        + "\n"
    )
    bpy.ops.wm.open_mainfile(filepath=str(folder / f"rest-after-{suffix}.blend"))
    bpy.context.scene.render.filepath = str(folder / f"after-{suffix}.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--python", required=True)
    p.add_argument("--face", action="store_true")
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    fit(a.folder, a.python, a.face)
