"""Blender entry point for the limited rest/blink/pointing calibration prototype.

blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
  --python tests/render_clippy_3d.py -- --output /tmp/clippy-3d-review --animate
"""

import argparse
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "data/clippy/3d-prototype"
sys.path.insert(0, str(ROOT / "tests"))
from clippy_3d_fit import fit_geometry  # noqa: E402
from clippy_3d_motion import apply_blink, point, reset, wire_clearance  # noqa: E402
from clippy_3d_timeline import source_timeline  # noqa: E402


def area(scene, name, position, power, size):
    light = bpy.data.lights.new(name, "AREA")
    light.energy = power
    light.shape = "DISK"
    light.size = size
    obj = bpy.data.objects.new(name, light)
    scene.collection.objects.link(obj)
    obj.location = position
    obj.rotation_euler = (-obj.location).to_track_quat("-Z", "Y").to_euler()
    return light


def setup(samples):
    bpy.ops.wm.open_mainfile(filepath=str(ASSETS / "source.blend"))
    scene = bpy.context.scene
    scene.frame_set(1)
    rig = bpy.data.objects["Armature"]
    rig.animation_data_clear()
    for bone in rig.pose.bones:
        bone.rotation_mode = "QUATERNION"
        bone.rotation_quaternion = (1, 0, 0, 0)
    texture = bpy.data.images["paper.png"]
    texture.filepath = str(ASSETS / "paper.png")
    texture.reload()
    texture.pack()
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    scene.cycles.seed = 0
    scene.render.resolution_x = 744
    scene.render.resolution_y = 558
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene.world.use_nodes = True
    nodes = scene.world.node_tree.nodes
    nodes.clear()
    background = nodes.new("ShaderNodeBackground")
    background.inputs["Color"].default_value = (0.7, 0.75, 0.85, 1)
    background.inputs["Strength"].default_value = 0.5
    output = nodes.new("ShaderNodeOutputWorld")
    scene.world.node_tree.links.new(background.outputs[0], output.inputs[0])
    for obj in list(bpy.data.objects):
        if obj.type == "LIGHT":
            bpy.data.objects.remove(obj, do_unlink=True)
    area(scene, "key", (-4, -6, 7), 500, 5)
    area(scene, "fill", (4, -3, 2), 100, 5)
    return scene, rig


def calibrate(scene):
    # Approved material calibration; geometry fitting is a separate step below.
    scene.world.node_tree.nodes.get("Background").inputs["Strength"].default_value = 0.24
    key = bpy.data.objects["key"]
    key.location = (-4, -12, 7)
    key.rotation_euler = (-key.location).to_track_quat("-Z", "Y").to_euler()
    key.data.energy = 2300
    key.data.size = 3.6
    bpy.data.lights["fill"].energy = 70
    shader = bpy.data.materials["metal"].node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (0.28, 0.30, 0.44, 1)
    shader.inputs["Metallic"].default_value = 0.45
    shader.inputs["Roughness"].default_value = 0.3
    eye = bpy.data.materials["eye"].node_tree.nodes.get("Principled BSDF")
    eye.inputs["Base Color"].default_value = (0.8, 0.8, 0.82, 1)
    paper = bpy.data.materials["paper"]
    shader = paper.node_tree.nodes.get("Principled BSDF")
    tint = paper.node_tree.nodes.new("ShaderNodeMixRGB")
    tint.name = "Classic paper calibration"
    tint.blend_type = "MULTIPLY"
    tint.inputs[0].default_value = 1
    tint.inputs[2].default_value = (0.95, 0.89, 0.97, 1)
    paper.node_tree.links.new(paper.node_tree.nodes.get("Image Texture").outputs["Color"], tint.inputs[1])
    paper.node_tree.links.new(tint.outputs[0], shader.inputs["Base Color"])
    shader.inputs["Roughness"].default_value = 0.9
    shader.inputs["Specular IOR Level"].default_value = 0.15


def render(scene, output, name):
    scene.render.filepath = str(output / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    if not (output / f"{name}.png").is_file():
        raise RuntimeError(f"Missing rendered frame: {name}")


def main(output, samples, animate):
    output.mkdir(parents=True, exist_ok=False)
    scene, rig = setup(samples)
    render(scene, output, "baseline")
    calibrate(scene)
    fit_geometry(scene)
    reset(rig)
    render(scene, output, "rest")
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "calibrated.blend"))
    sequences = {"RestPose": [("rest", 100)]}
    reference_frames = {}
    if animate:
        for action, frames in source_timeline().items():
            sequences[action] = []
            reference_frames[action] = []
            for frame in frames:
                index = frame["original_index"]
                if action.startswith("Gesture"):
                    point(rig, 1 if action == "GestureLeft" else -1, frame["progress"])
                else:
                    reset(rig)
                apply_blink(rig, frame["blink"])
                clearance = wire_clearance()
                if clearance["surface_gap_lower_bound"] < 0.02:
                    raise RuntimeError(f"Insufficient wire clearance: {action}/{index}: {clearance}")
                name = f"{action}-{index:03d}"
                render(scene, output, name)
                sequences[action].append((name, frame["duration_ms"]))
                reference_frames[action].append({**frame, "file": name + ".png"})
    reset(rig)
    if animate:
        render(scene, output, "rest-return")
    manifest = {
        "status": "Calibration prototype; original animation fidelity not yet achieved",
        "source": "Fog / Sketchfab Clippy",
        "pixel_size": [744, 558],
        "logical_size": [124, 93],
        "samples": samples,
        "reference_frames": reference_frames,
        "sequences": {
            name: [{"file": file + ".png", "duration_ms": duration} for file, duration in frames]
            for name, frames in sequences.items()
        },
        "limitations": [
            "Paper silhouette and eye shapes still differ from the original.",
            "Pointing includes the original body turn, but detailed posing and timing still need refinement.",
            "Blink and pointing test rig continuity; timing is not a faithful ACS reconstruction.",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=128)
    parser.add_argument("--animate", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    main(args.output, args.samples, args.animate)
