"""Blender rig helpers and conservative wire-clearance checks for the prototype."""

import math

import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.kdtree import KDTree

TIP_BONES = ("Bone.02", "Bone.31", "Bone.01", "Bone.00")


def reset(rig):
    if "prototype_rest_matrix" not in rig:
        rig["prototype_rest_matrix"] = [v for row in rig.matrix_world for v in row]
    values = rig["prototype_rest_matrix"]
    rig.matrix_world = Matrix([values[i : i + 4] for i in range(0, 16, 4)])
    for bone in rig.pose.bones:
        bone.rotation_mode = "QUATERNION"
        bone.rotation_quaternion = (1, 0, 0, 0)
        if "prototype_rest_location" not in bone:
            bone["prototype_rest_location"] = list(bone.location)
        if "prototype_rest_scale" not in bone:
            bone["prototype_rest_scale"] = list(bone.scale)
        bone.location = bone["prototype_rest_location"]
        bone.scale = bone["prototype_rest_scale"]
    bpy.context.view_layer.update()


def bend_tip(rig, angle):
    axes = {
        name: (rig.matrix_world @ rig.pose.bones[name].matrix).to_quaternion().inverted() @ Vector((0, 1, 0))
        for name in TIP_BONES
    }
    for name, axis in axes.items():
        rig.pose.bones[name].rotation_quaternion = Quaternion(axis, angle)
    bpy.context.view_layer.update()


def point(rig, sign, fraction, angle=None):
    reset(rig)
    if angle is not None:
        # Regression fixture for the former inward bend, without the necessary turn.
        bend_tip(rig, sign * angle * fraction)
        return
    # GestureRight in the original turns the body around before extending the
    # same free end outward. Bending that end inward instead crosses the wire.
    turn = min(1.0, fraction * 2) if sign < 0 else fraction
    extension = max(0.0, fraction * 2 - 1) if sign < 0 else fraction
    yaw = math.pi * turn if sign < 0 else -0.15 * turn
    # Pivot through the wire's center. The paper, camera, and lights stay fixed.
    wire = bpy.data.objects["Vert"]
    center = sum((wire.matrix_world @ Vector(corner) for corner in wire.bound_box), Vector()) / 8
    pivot = Vector((center.x, center.y, 0))
    bend_tip(rig, 0.32 * extension)
    for name in TIP_BONES:
        rig.pose.bones[name].scale.y *= 1 + 0.10 * extension
    bpy.context.view_layer.update()
    rotation = Matrix.Rotation(yaw, 4, "Z")
    rig.matrix_world = Matrix.Translation(pivot) @ rotation @ Matrix.Translation(-pivot) @ rig.matrix_world
    bpy.context.view_layer.update()
    if "reference_geometry_fit" in rig:
        from clippy_3d_fit import lean_body

        lean_body(bpy.context.scene, rig, -0.10 * turn if sign < 0 else 0.02 * turn, 1 - 0.04 * turn)
    # Eyes and eyebrows track the viewer as the wire turns, as in the atlas.
    for name in ("eye.L", "eye.R", "eyebrow.L", "eyebrow.R"):
        bone = rig.pose.bones[name]
        axis = (rig.matrix_world @ bone.matrix).to_quaternion().inverted() @ Vector((0, 0, 1))
        bone.rotation_quaternion = Quaternion(axis, -yaw)
    bpy.context.view_layer.update()
    if "reference_geometry_fit" in rig:
        from clippy_3d_fit import track_eyes

        track_eyes(bpy.context.scene, rig, sign, turn)


def blink(rig, fraction):
    reset(rig)
    apply_blink(rig, fraction)


def apply_blink(rig, fraction):
    # Lid bones have rolled local X axes. Rotating those axes twists the lids in depth.
    # Use one world-space horizontal hinge for both lids instead.
    for side in ("L", "R"):
        for kind, angle in (("upper", 2.4), ("lower", -1.2)):
            bone = rig.pose.bones[f"eyelid_{kind}.{side}"]
            axis = (rig.matrix_world @ bone.matrix).to_quaternion().inverted() @ Vector((1, 0, 0))
            bone.rotation_quaternion = Quaternion(axis, angle * fraction)
    bpy.context.view_layer.update()


def wire_clearance():
    """Lower bound on separation of nonlocal strands, using the smoothed centerline.

    Sample spacing is at most 0.01 world units; subtract twice this spacing from
    the measured distance. Exclude neighbors within two wire diameters of arc
    length, since adjacent portions of a continuous tube necessarily touch.
    The radius uses the Skin half-width before the final rounding subdivision.
    """
    wire = bpy.data.objects["Vert"]
    diameter = 2 * max(max(v.radius) for v in wire.data.skin_vertices[0].data) * max(wire.matrix_world.to_scale())
    modifiers = [(m, m.show_viewport) for m in wire.modifiers]
    after_skin = False
    try:
        for modifier, _ in modifiers:
            after_skin |= modifier.type == "SKIN"
            if after_skin:
                modifier.show_viewport = False
        bpy.context.view_layer.update()
        evaluated = wire.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        vertices = [wire.matrix_world @ v.co for v in mesh.vertices]
        neighbors = [[] for _ in vertices]
        for edge in mesh.edges:
            a, b = edge.vertices
            neighbors[a].append(b)
            neighbors[b].append(a)
        current = next(i for i, links in enumerate(neighbors) if len(links) == 1)
        ordered, previous = [], None
        while True:
            ordered.append(vertices[current])
            following = [v for v in neighbors[current] if v != previous]
            if not following:
                break
            previous, current = current, following[0]
        evaluated.to_mesh_clear()
    finally:
        for modifier, enabled in modifiers:
            modifier.show_viewport = enabled
        bpy.context.view_layer.update()
    samples, arcs, arc = [], [], 0.0
    spacing = 0.01
    for a, b in zip(ordered[:-1], ordered[1:], strict=True):
        length = (b - a).length
        count = max(1, int(length / spacing) + 1)
        for i in range(count):
            samples.append(a.lerp(b, i / count))
            arcs.append(arc + length * i / count)
        arc += length
    samples.append(ordered[-1])
    arcs.append(arc)
    tree = KDTree(len(samples))
    for i, position in enumerate(samples):
        tree.insert(position, i)
    tree.balance()
    closest = float("inf")
    for i, position in enumerate(samples):
        for _, j, distance in tree.find_range(position, diameter + 0.15):
            if abs(arcs[i] - arcs[j]) > 2 * diameter:
                closest = min(closest, distance)
    return {"surface_gap_lower_bound": closest - 2 * spacing - diameter, "diameter": diameter}
