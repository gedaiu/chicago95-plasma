"""Rest-pose geometry calibration against the original 124x93 atlas.

Coordinates below are explicit reference landmarks; materials and camera stay fixed.
"""

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

PAPER_LANDMARKS = {
    0: (17, 78),
    1: (78, 91),
    2: (70, 23),
    3: (110, 22),
    4: (32, 72),
    5: (46, 51),
    6: (38, 65),
    7: (42, 58),
    8: (100, 57),
    9: (90, 81),
    10: (97, 65),
    11: (94, 73),
    12: (50, 45),
    13: (65, 26),
    14: (56, 37),
    15: (60, 31),
    16: (108, 27),
    17: (102, 50),
    18: (106, 34),
    19: (104, 42),
}


def screen_position(scene, world, x, y):
    camera = scene.camera
    projected = world_to_camera_view(scene, camera, world)
    frame = camera.data.view_frame(scene=scene)
    width = (max(v.x for v in frame) - min(v.x for v in frame)) * projected.z / abs(frame[0].z)
    height = (max(v.y for v in frame) - min(v.y for v in frame)) * projected.z / abs(frame[0].z)
    shift = Vector(((x / 124 - projected.x) * width, (1 - y / 93 - projected.y) * height, 0))
    return world + camera.matrix_world.to_quaternion() @ shift


def fit_geometry(scene):
    paper = bpy.data.objects["Plane"]
    inverse = paper.matrix_world.inverted()
    for index, (x, y) in PAPER_LANDMARKS.items():
        vertex = paper.data.vertices[index]
        vertex.co = inverse @ screen_position(scene, paper.matrix_world @ vertex.co, x, y)
    rig = bpy.data.objects["Armature"]
    rig["reference_geometry_fit"] = True
    lean_body(scene, rig, -0.05, 0.975)
    rig["prototype_rest_matrix"] = [v for row in rig.matrix_world for v in row]
    bpy.context.view_layer.update()
    for side, target in (("R", (47, 28)), ("L", (64, 33))):
        eye = rig.pose.bones[f"eye.{side}"]
        world = rig.matrix_world @ eye.head
        delta = screen_position(scene, world, *target) - world
        for name in (f"eye.{side}", f"eyebrow.{side}"):
            bone = rig.pose.bones[name]
            local_delta = (rig.matrix_world @ bone.matrix).to_3x3().inverted() @ delta
            bone["prototype_rest_location"] = list(local_delta)
            if name.startswith("eye."):
                bone["prototype_rest_scale"] = [1.2241956 * 0.9, 0.9, 0.9]
    from clippy_3d_motion import reset

    reset(rig)
    for side in ("R", "L"):
        eye = world_to_camera_view(scene, scene.camera, rig.matrix_world @ rig.pose.bones[f"eye.{side}"].head)
        brow = rig.pose.bones[f"eyebrow.{side}"]
        projected = world_to_camera_view(scene, scene.camera, rig.matrix_world @ brow.head)
        brow["prototype_screen_offset"] = [(projected.x - eye.x) * 124, (eye.y - projected.y) * 93]
    bpy.context.view_layer.update()


def track_eyes(scene, rig, sign, turn):
    # Measured centers from the low-resolution turn: eyes remain separated even
    # when the wire is viewed edge-on. Keep viewer-left/right ordering stable.
    if sign < 0:
        landmarks = [((47, 28), (64, 33)), ((45, 28), (64, 30)), ((43, 30), (61, 29)), ((44, 33), (61, 27))]
        position = turn * 3
        index = min(2, int(position))
        weight = position - index
        targets = [
            tuple(a * (1 - weight) + b * weight for a, b in zip(start, end, strict=True))
            for start, end in zip(landmarks[index], landmarks[index + 1], strict=True)
        ]
    else:
        targets = [(47 - 2 * turn, 28 + turn), (64 - 2 * turn, 33)]
    for side, target in zip(("R", "L"), targets, strict=True):
        eye = rig.pose.bones[f"eye.{side}"]
        world = rig.matrix_world @ eye.matrix
        delta = screen_position(scene, world.translation, *target) - world.translation
        for name in (f"eye.{side}", f"eyebrow.{side}"):
            bone = rig.pose.bones[name]
            desired = rig.matrix_world @ bone.matrix
            if name.startswith("eyebrow."):
                offset = bone["prototype_screen_offset"]
                desired.translation = screen_position(
                    scene, desired.translation, target[0] + offset[0], target[1] + offset[1]
                )
            else:
                desired.translation += delta
            bone.matrix = rig.matrix_world.inverted() @ desired
        bpy.context.view_layer.update()


def lean_body(scene, rig, shear, height_scale):
    wire = bpy.data.objects["Vert"]
    center = sum((wire.matrix_world @ Vector(corner) for corner in wire.bound_box), Vector()) / 8
    pivot = screen_position(scene, center, 60, 80)
    orientation = scene.camera.matrix_world.to_quaternion().to_matrix().to_4x4()
    affine = Matrix.Identity(4)
    affine[0][1] = shear
    affine[1][1] = height_scale
    transform = orientation @ affine @ orientation.inverted()
    rig.matrix_world = Matrix.Translation(pivot) @ transform @ Matrix.Translation(-pivot) @ rig.matrix_world
    bpy.context.view_layer.update()
