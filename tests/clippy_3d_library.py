"""Editable Blender geometry and authored motion for the complete Clippy action set.

All geometry is native Blender geometry; the original atlas supplies timing and
reference review only. Complex actions use a continuous tubular wire, with depth
separation at projected crossings. This is a reconstruction, not original geometry.
"""

import math

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from clippy_3d_motion import apply_blink, point, reset
from clippy_render_quality import configure
from mathutils import Matrix, Quaternion, Vector

N = 192
ALIASES = {"GetTechy": "IdleAtom", "Thinking": "IdleAtom", "GetWizardy": "Congratulate"}
SUPPORTED = {
    "Congratulate",
    "LookRight",
    "SendMail",
    "Thinking",
    "Explain",
    "IdleRopePile",
    "IdleAtom",
    "Print",
    "Hide",
    "GetAttention",
    "Save",
    "GetTechy",
    "GestureUp",
    "Idle1_1",
    "Processing",
    "Alert",
    "LookUpRight",
    "IdleSideToSide",
    "GoodBye",
    "LookLeft",
    "IdleHeadScratch",
    "LookUpLeft",
    "CheckingSomething",
    "Hearing_1",
    "GetWizardy",
    "IdleFingerTap",
    "GestureLeft",
    "Wave",
    "GestureRight",
    "Writing",
    "IdleSnooze",
    "LookDownRight",
    "GetArtsy",
    "Show",
    "LookDown",
    "Searching",
    "EmptyTrash",
    "Greeting",
    "LookUp",
    "GestureDown",
    "RestPose",
    "IdleEyeBrowRaise",
    "LookDownLeft",
}


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def envelope(t, enter=0.22, leave=0.80):
    return min(smooth(t / enter), smooth((1 - t) / (1 - leave)))


def resample(points, count=N):
    points = np.array(points, dtype=float)
    lengths = np.r_[0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    if lengths[-1] < 1e-8:
        raise ValueError("Degenerate wire path")
    distances = np.linspace(0, lengths[-1], count)
    return np.stack([np.interp(distances, lengths, points[:, axis]) for axis in range(3)], axis=1)


def path(points):
    """Catmull-Rom interpolation of native-coordinate control points."""
    pts = np.array([tuple(p) + (0,) if len(p) == 2 else p for p in points], dtype=float)
    padded = np.vstack([pts[0], pts, pts[-1]])
    sampled = []
    for i in range(len(pts) - 1):
        a, b, c, d = padded[i : i + 4]
        for t in np.linspace(0, 1, 12, endpoint=False):
            sampled.append(
                0.5
                * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t * t * t)
            )
    sampled.append(pts[-1])
    return resample(sampled)


class Library:
    def __init__(self, scene):
        self.scene = scene
        configure(scene, scene.cycles.samples)
        self.rig = bpy.data.objects["Armature"]
        self.rig.animation_data_clear()
        self.paper = bpy.data.objects["Plane"]
        self.original_wire = bpy.data.objects["Vert"]
        self.camera = scene.camera
        self.camera_rotation = self.camera.matrix_world.to_quaternion()
        self.depth = 21.0
        self.props = {}
        self.paper_matrix = self.paper.matrix_world.copy()
        self.paper_vertices = [v.co.copy() for v in self.paper.data.vertices]
        reset(self.rig)
        self.eye_rest = {
            b.name: b.matrix.copy() for b in self.rig.pose.bones if b.name.startswith(("eye.", "eyebrow."))
        }
        self.rest_path = self.read_wire_path()
        self.morph = self.curve("MorphWire", self.rest_path, bpy.data.materials["metal"], 0.08)
        self.morph.hide_render = True
        self.curve_points = self.morph.data.splines[0].points
        self.hidden_material = self.material("Prop black", (0.015, 0.018, 0.023, 1), 0.1, 0.35)
        self.red = self.material("Pencil red", (0.65, 0.025, 0.02, 1), 0, 0.3)
        self.white = self.material("Prop ivory", (0.85, 0.84, 0.65, 1), 0, 0.6)
        self.build_props()
        self.dynamic_objects = [self.rig, self.paper, self.original_wire, self.morph] + list(self.props.values())
        self.initial = {o.name: (o.matrix_world.copy(), o.hide_render) for o in self.dynamic_objects}
        self.last_clearance = None

    def material(self, name, color, metallic, roughness):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        shader = mat.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Base Color"].default_value = color
        shader.inputs["Metallic"].default_value = metallic
        shader.inputs["Roughness"].default_value = roughness
        return mat

    def world(self, x, y, z=0):
        depth = self.depth + z * 0.035
        frame = self.camera.data.view_frame(scene=self.scene)
        width = (max(v.x for v in frame) - min(v.x for v in frame)) * depth / abs(frame[0].z)
        height = (max(v.y for v in frame) - min(v.y for v in frame)) * depth / abs(frame[0].z)
        return self.camera.matrix_world @ Vector(((x / 124 - 0.5) * width, (0.5 - y / 93) * height, -depth))

    def screen(self, world):
        p = world_to_camera_view(self.scene, self.camera, world)
        return [p.x * 124, (1 - p.y) * 93, (p.z - self.depth) / 0.035]

    def curve(self, name, points, material, radius=0.08, cyclic=False):
        data = bpy.data.curves.new(name, "CURVE")
        data.dimensions = "3D"
        data.resolution_u = 2
        data.bevel_depth = radius
        data.bevel_resolution = 3
        data.use_fill_caps = not cyclic
        spline = data.splines.new("POLY")
        spline.use_cyclic_u = cyclic
        spline.points.add(len(points) - 1)
        for p, coordinate in zip(spline.points, points, strict=True):
            p.co = (*self.world(*coordinate), 1)
        obj = bpy.data.objects.new(name, data)
        self.scene.collection.objects.link(obj)
        data.materials.append(material)
        return obj

    def box(self, name, center, size, material):
        bpy.ops.mesh.primitive_cube_add(size=1, location=self.world(*center))
        obj = bpy.context.object
        obj.name = name
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = self.camera_rotation
        unit = (self.world(center[0] + 1, center[1], center[2]) - self.world(*center)).length
        obj.scale = Vector(size) * unit
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bevel = obj.modifiers.new("Smooth manufactured edges", "BEVEL")
        bevel.width = unit * 0.6
        bevel.segments = 3
        obj.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
        obj.data.materials.append(material)
        self.props[name] = obj
        obj.hide_render = True
        return obj

    def page(self, name, coordinates):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([self.world(*p) for p in coordinates], [], [(0, 1, 2, 3)])
        mesh.materials.append(bpy.data.materials["paper"])
        uv = mesh.uv_layers.new()
        for loop, co in zip(uv.data, [(0, 0), (1, 0), (1, 1), (0, 1)], strict=True):
            loop.uv = co
        obj = bpy.data.objects.new(name, mesh)
        self.scene.collection.objects.link(obj)
        solid = obj.modifiers.new("Paper thickness", "SOLIDIFY")
        solid.thickness = 0.008
        self.props[name] = obj
        obj.hide_render = True
        return obj

    def build_props(self):
        metal = bpy.data.materials["metal"]
        for side, x in [("Left", 37), ("Right", 79)]:
            self.box("Headphone" + side, (x, 34, -4), (7, 20, 5), self.hidden_material)
        arc = path([(35, 29, -3), (37, 12, -3), (48, 5, -3), (64, 7, -3), (77, 15, -3), (80, 29, -3)])
        self.props["HeadphoneBand"] = self.curve("HeadphoneBand", arc, self.hidden_material, 0.09)
        self.props["HeadphoneBand"].hide_render = True
        for side, x in [("Left", 47), ("Right", 68)]:
            # A genuinely closed rounded rectangle, not two overlapping capped ends.
            pts = [
                (cx + 3 * math.cos(a), cy + 3 * math.sin(a), -4)
                for cx, cy, start in [
                    (x + 5, 34, -math.pi / 2),
                    (x + 5, 41, 0),
                    (x - 6, 41, math.pi / 2),
                    (x - 6, 34, math.pi),
                ]
                for a in np.linspace(start, start + math.pi / 2, 24)
            ]
            self.props["Glasses" + side] = self.curve("Glasses" + side, pts, metal, 0.07, cyclic=True)
            self.props["Glasses" + side].hide_render = True
        self.props["GlassesBridge"] = self.curve("GlassesBridge", path([(55, 34, -4), (59, 33, -4)]), metal, 0.06)
        self.props["GlassesBridge"].hide_render = True
        self.page("Notepad", [(73, 34, -3), (91, 36, -3), (86, 63, -3), (70, 60, -3)])
        self.props["Pencil"] = self.curve("Pencil", path([(60, 45, -5), (74, 55, -5)]), self.red, 0.075)
        self.props["Pencil"].hide_render = True
        self.props["Graphite"] = self.curve("Graphite", path([(74, 55, -5), (76, 57, -5)]), self.hidden_material, 0.04)
        self.props["Graphite"].hide_render = True
        # Rolled paper telescope: tapered tube with an explicitly open, dark aperture.
        unit = (self.world(80, 36, -4) - self.world(79, 36, -4)).length
        direction = self.camera_rotation @ Vector((0.85, 0, 0.53)).normalized()
        center = self.world(79, 36, -4)
        for name, location, length, r1, r2, material in [
            ("Telescope", center, 19, 2.5, 5, self.white),
            ("TelescopeLens", center + direction * unit * 9.6, 0.3, 4.1, 4.1, self.hidden_material),
        ]:
            bpy.ops.mesh.primitive_cone_add(
                vertices=48, radius1=r1 * unit, radius2=r2 * unit, depth=length * unit, location=location
            )
            obj = bpy.context.object
            obj.name = name
            obj.rotation_mode = "QUATERNION"
            obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
            obj.data.materials.append(material)
            for polygon in obj.data.polygons:
                polygon.use_smooth = len(polygon.vertices) == 4
            self.props[name] = obj
            obj.hide_render = True
        for i in range(6):
            self.page(
                f"PaperStrip{i}",
                [
                    (30 + i * 8, 49 + i % 2 * 8, -3),
                    (41 + i * 8, 45 + i % 2 * 8, -3),
                    (44 + i * 8, 50 + i % 2 * 8, -3),
                    (32 + i * 8, 54 + i % 2 * 8, -3),
                ],
            )
        # The original folds its ruled sheet into a plane; retain that material.
        self.page("PlaneWingA", [(35, 62, -3), (105, 51, -3), (67, 75, -3), (64, 64, -6)])
        self.page("PlaneWingB", [(35, 62, -3), (64, 64, -6), (67, 75, -3), (45, 80, -2)])
        for i, (x, y) in enumerate([(82, 50), (101, 64), (91, 76)]):
            ring = [
                (x + 2 * math.cos(t), y + 2 * math.sin(t), -1) for t in np.linspace(0, math.tau, 64, endpoint=False)
            ]
            self.props[f"MobileRing{i}"] = self.curve(f"MobileRing{i}", ring, metal, 0.045, cyclic=True)
            self.props[f"MobileRing{i}"].hide_render = True
        for i, pts in enumerate(
            [
                [(58, 13), (58, 30), (84, 39), (84, 48)],
                [(84, 39), (101, 51), (101, 62)],
                [(101, 51), (91, 65), (91, 74)],
            ]
        ):
            self.props[f"MobileBar{i}"] = self.curve(f"MobileBar{i}", path(pts), metal, 0.045)
            self.props[f"MobileBar{i}"].hide_render = True

    def read_wire_path(self):
        wire = self.original_wire
        flags = [(m, m.show_viewport) for m in wire.modifiers]
        after = False
        for modifier, _ in flags:
            after |= modifier.type == "SKIN"
            if after:
                modifier.show_viewport = False
        bpy.context.view_layer.update()
        evaluated = wire.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        neighbors = [[] for _ in mesh.vertices]
        for edge in mesh.edges:
            a, b = edge.vertices
            neighbors[a].append(b)
            neighbors[b].append(a)
        current = next(i for i, n in enumerate(neighbors) if len(n) == 1)
        previous = None
        coords = []
        while True:
            coords.append(self.screen(wire.matrix_world @ mesh.vertices[current].co))
            following = [n for n in neighbors[current] if n != previous]
            if not following:
                break
            previous, current = current, following[0]
        evaluated.to_mesh_clear()
        for modifier, flag in flags:
            modifier.show_viewport = flag
        bpy.context.view_layer.update()
        return resample(coords)

    def begin(self):
        reset(self.rig)
        for child in self.rig.children:
            child.hide_render = False
        for obj in [self.paper, self.original_wire, self.morph] + list(self.props.values()):
            obj.matrix_world = self.initial[obj.name][0].copy()
            obj.hide_render = self.initial[obj.name][1]
        for vertex, co in zip(self.paper.data.vertices, self.paper_vertices, strict=True):
            vertex.co = co
        self.original_wire.hide_render = False
        self.morph.hide_render = True
        self.paper.hide_render = False
        for obj in self.props.values():
            obj.hide_render = True
        self.last_clearance = None

    def visible(self, *names):
        for name in names:
            self.props[name].hide_render = False

    def translate(self, obj, dx, dy, dz=0):
        obj.matrix_world.translation += self.world(60 + dx, 50 + dy, dz) - self.world(60, 50, 0)

    def eye_position(self, left, right, scale=1):
        for side, target in [("R", left), ("L", right)]:
            eye = self.rig.pose.bones["eye." + side]
            old = self.rig.matrix_world @ eye.matrix
            projected = self.screen(old.translation)
            delta = self.world(target[0], target[1], projected[2]) - old.translation
            for name in ["eye." + side, "eyebrow." + side]:
                bone = self.rig.pose.bones[name]
                matrix = self.rig.matrix_world @ bone.matrix
                matrix.translation += delta
                bone.matrix = self.rig.matrix_world.inverted() @ matrix
            eye.scale *= scale
        bpy.context.view_layer.update()

    def gaze(self, x, y):
        for side in ["L", "R"]:
            bone = self.rig.pose.bones["eye." + side]
            world = (self.rig.matrix_world @ bone.matrix).to_quaternion()
            horizontal = world.inverted() @ (self.camera_rotation @ Vector((0, 1, 0)))
            vertical = world.inverted() @ (self.camera_rotation @ Vector((1, 0, 0)))
            bone.rotation_quaternion = Quaternion(horizontal, x * 0.32) @ Quaternion(vertical, y * 0.26)
        bpy.context.view_layer.update()

    def body_transform(self, scale=(1, 1, 1), rotation=0, dx=0, dy=0):
        pivot = self.world(60, 80, 0)
        orientation = self.camera_rotation.to_matrix().to_4x4()
        transform = (
            orientation @ Matrix.Rotation(rotation, 4, "Z") @ Matrix.Diagonal((*scale, 1)) @ orientation.inverted()
        )
        self.rig.matrix_world = (
            Matrix.Translation(pivot) @ transform @ Matrix.Translation(-pivot) @ self.rig.matrix_world
        )
        self.translate(self.rig, dx, dy)
        bpy.context.view_layer.update()

    def morph_to(self, target, amount):
        if amount <= 1e-8:
            return
        coords = self.rest_path * (1 - amount) + resample(target) * amount
        # Resolve projected crossings in depth, keeping screen coordinates fixed.
        # Only non-neighboring strands are separated; the wire stays continuous.
        for _ in range(320):
            arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(coords, axis=0), axis=1))]
            delta = coords[:, None, :] - coords[None, :, :]
            distance = np.linalg.norm(delta, axis=2)
            permitted = np.abs(arc[:, None] - arc[None, :]) > 7
            close = np.argwhere((distance < 3.5) & permitted & np.triu(np.ones_like(distance, dtype=bool), 1))
            if not len(close):
                break
            shift = np.zeros(N)
            for i, j in close:
                sign = 1 if coords[i, 2] >= coords[j, 2] else -1
                push = (3.6 - distance[i, j]) * 0.3
                shift[i] += sign * push
                shift[j] -= sign * push
            coords[:, 2] += np.clip(shift, -1, 1)
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(coords, axis=0), axis=1))]
        distance = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=2)
        distance[np.abs(arc[:, None] - arc[None, :]) <= 7] = np.inf
        minimum = float(distance.min())
        if minimum < 3.4:
            # Some collapse transitions need a monotonic depth ordering rather
            # than iterative pair separation. Projection is unchanged. Keep all
            # strands in front of the sheet and compensate tube radius for depth.
            projected_arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(coords[:, :2], axis=0), axis=1))]
            coords[:, 2] = -0.6 * projected_arc
            distance = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=2)
            distance[np.abs(projected_arc[:, None] - projected_arc[None, :]) <= 7] = np.inf
            minimum = float(distance.min())
            if minimum < 3.4:
                raise RuntimeError(f"Unresolved morph wire crossing: {minimum:.3f}px")
        self.last_clearance = minimum
        for p, coordinate in zip(self.curve_points, coords, strict=True):
            p.co = (*self.world(*coordinate), 1)
            p.radius = (self.depth + coordinate[2] * 0.035) / self.depth
            if p.radius <= 0.2:
                raise RuntimeError("Wire depth correction exceeded camera clearance")
        self.original_wire.hide_render = True
        self.morph.hide_render = False

    def paper_rectangle(self, amount, top=24, bottom=83, left=33, right=86):
        left_ids = [0, 4, 6, 7, 5, 12, 14, 15, 13, 2]
        right_ids = [1, 9, 11, 10, 8, 17, 19, 18, 16, 3]
        inverse = self.paper.matrix_world.inverted()
        for ids, x in [(left_ids, left), (right_ids, right)]:
            for rank, index in enumerate(ids):
                v = rank / (len(ids) - 1)
                target = self.world(x, bottom + (top - bottom) * v, 35)
                original = self.paper.matrix_world @ self.paper_vertices[index]
                self.paper.data.vertices[index].co = inverse @ original.lerp(target, amount)

    def apply(self, name, index, count):
        if name not in SUPPORTED:
            raise ValueError(f"Unimplemented action: {name}")
        self.begin()
        name = ALIASES.get(name, name)
        t = index / max(1, count - 1)
        e = envelope(t)
        pulse = math.sin(t * math.tau)
        blink = max(0, 1 - abs((t - 0.5) / 0.08))
        if name == "RestPose":
            return
        if name.startswith("Look"):
            x = -1 if "Right" in name else 1 if "Left" in name else 0
            y = 1 if "Up" in name else -1 if "Down" in name else 0
            self.gaze(x * e, y * e)
            apply_blink(self.rig, blink * 0.7)
            return
        if name in ["GestureLeft", "GestureRight"]:
            from clippy_3d_timeline import GESTURE_BLINK, POINT_PROGRESS

            point(self.rig, 1 if name == "GestureLeft" else -1, POINT_PROGRESS[name][index])
            apply_blink(self.rig, GESTURE_BLINK[name].get(index, 0))
            return
        if name in ["Hide", "Show"]:
            value = 1 - 0.85 * t if name == "Hide" else [0, 0.15, 0.4, 0.7, 1][index]
            value = max(0.001, value)
            self.body_transform((value, value, value))
            pivot = self.world(60, 80)
            self.paper.matrix_world = (
                Matrix.Translation(pivot)
                @ Matrix.Diagonal((value, value, value, 1))
                @ Matrix.Translation(-pivot)
                @ self.paper.matrix_world
            )
            if name == "Show" and index == 0:
                self.paper.hide_render = True
                for obj in self.rig.children:
                    obj.hide_render = True
            return
        # Undo Show's deliberately blank first frame for every other clip/frame.
        for obj in self.rig.children:
            if obj != self.original_wire:
                obj.hide_render = False
        if name in ["Idle1_1", "IdleSideToSide", "IdleEyeBrowRaise", "Explain"]:
            self.gaze((0.6 * math.sin(t * math.tau * 2) if name == "IdleSideToSide" else 0.15 * pulse) * e, 0)
            amount = (max(0, math.cos(t * math.tau * 6)) ** 16) * e if name == "Idle1_1" else blink
            apply_blink(self.rig, amount)
            for side in ["L", "R"]:
                b = self.rig.pose.bones["eyebrow." + side]
                b.location.z += 0.18 * e * (1 if side == "L" else 0.6)
            return
        if name == "IdleFingerTap":
            point(self.rig, 1, 0.18 * e * (0.6 + 0.4 * math.sin(t * math.tau * 3)))
            apply_blink(self.rig, blink)
            return
        if name in ["Alert", "Hearing_1"]:
            if e > 0.02:
                self.visible("HeadphoneLeft", "HeadphoneRight", "HeadphoneBand")
            self.body_transform(rotation=0.025 * e * math.sin(t * math.tau * 4))
            self.gaze(0.3 * pulse, 0)
            for obj in self.props.values():
                if not obj.hide_render:
                    self.translate(obj, 0.8 * e * math.sin(t * math.tau * 4), 0)
            apply_blink(self.rig, blink)
            return
        if name in ["GetAttention", "Wave"]:
            point(self.rig, 1, e * (0.35 + 0.35 * math.sin(t * math.tau * 2) ** 2))
            self.body_transform((1 + 0.15 * e, 1 + 0.06 * e, 1), dx=1.5 * pulse * e, dy=3 * e)
            for side in ["L", "R"]:
                self.rig.pose.bones["eye." + side].scale *= 1 + 0.25 * e
            apply_blink(self.rig, blink * 0.6)
            return
        if name in ["Greeting", "GoodBye"]:
            p = t if name == "Greeting" else 1 - t
            grow = smooth((p - 0.12) / 0.72)
            self.body_transform(
                (max(0.02, grow), max(0.02, grow), max(0.02, grow)),
                rotation=math.pi * (1 - grow),
                dy=-6 * math.sin(p * math.pi),
            )
            if grow < 0.025:
                for obj in self.rig.children:
                    obj.hide_render = True
            apply_blink(self.rig, 1 - grow)
            return
        if name == "IdleHeadScratch":
            target = self.rest_path.copy()
            for i in range(40):
                weight = (1 - i / 40) ** 2
                target[i, 1] -= (28 + 2 * math.sin(t * math.tau * 5)) * weight
                target[i, 0] += 2 * weight
            self.morph_to(target, e)
            self.gaze(0.5 * e, 0.5 * e)
            apply_blink(self.rig, blink * 0.5)
            return
        if name in ["GestureUp", "GestureDown"]:
            if name == "GestureUp":
                target = path(
                    [
                        (61, 15),
                        (61, 30),
                        (81, 45),
                        (85, 61),
                        (68, 70),
                        (43, 65),
                        (33, 52),
                        (39, 41),
                        (53, 44),
                        (65, 54),
                        (56, 60),
                        (47, 55),
                    ]
                )
                eyes = ((44, 48), (62, 53))
            else:
                target = path(
                    [
                        (56, 62),
                        (52, 48),
                        (32, 37),
                        (29, 27),
                        (43, 20),
                        (69, 22),
                        (81, 31),
                        (73, 39),
                        (52, 39),
                        (42, 34),
                        (48, 29),
                        (64, 30),
                    ]
                )
                eyes = ((62, 31), (79, 34))
            self.morph_to(target, e)
            self.eye_position(
                tuple(np.array((47, 28)) * (1 - e) + np.array(eyes[0]) * e),
                tuple(np.array((64, 33)) * (1 - e) + np.array(eyes[1]) * e),
            )
            apply_blink(self.rig, blink)
            return
        if name == "IdleAtom":
            u = np.linspace(0, math.tau * 0.96, N)
            spin = t * math.tau * 1.5
            target = np.stack(
                [60 + 20 * np.sin(2 * u + spin), 46 + 30 * np.sin(3 * u), 14 * np.cos(2 * u + spin)], axis=1
            )
            self.morph_to(target, e)
            self.eye_position((47 + 12 * math.sin(spin) * e, 28 + 20 * e), (64 - 12 * math.sin(spin) * e, 33 + 13 * e))
            apply_blink(self.rig, blink * 0.6)
            return
        if name in ["IdleRopePile", "IdleSnooze", "EmptyTrash"]:
            u = np.linspace(0, math.tau * (3.2 if name != "EmptyTrash" else 4.4), N)
            radius = np.linspace(20, 11, N) if name != "EmptyTrash" else np.linspace(27, 3, N)
            base = (78 - u / math.tau * 4) if name != "EmptyTrash" else (24 + u / math.tau * 12)
            target = np.stack([60 + radius * np.cos(u), base + 3 * np.sin(u), radius * 0.75 * np.sin(u)], axis=1)
            amount = e
            if name == "IdleRopePile":
                amount = envelope(t, 0.72, 0.88)
            self.morph_to(target, amount)
            self.eye_position((47 + 3 * amount, 28 + 35 * amount), (64 + 2 * amount, 33 + 31 * amount))
            if name == "IdleSnooze":
                apply_blink(self.rig, amount)
            if name == "EmptyTrash" and amount > 0.05:
                self.paper.hide_render = True
                for i in range(4):
                    self.visible(f"PaperStrip{i}")
                    self.translate(
                        self.props[f"PaperStrip{i}"],
                        3 * math.sin(t * math.tau + i),
                        -20 + 12 * math.cos(t * math.tau + i),
                    )
            return
        if name == "Congratulate":
            target = path([(27, 64), (40, 76), (49, 80), (66, 55), (92, 9)])
            self.morph_to(target, e)
            self.eye_position((47 - 7 * e, 28 + 42 * e), (64 - 9 * e, 33 + 39 * e))
            apply_blink(self.rig, blink)
            return
        if name == "Save":
            amount = smooth(t / 0.45)
            target = path([(86, 48), (86, 82), (34, 82), (34, 47), (86, 47), (89, 48)])
            self.morph_to(target, amount)
            self.paper_rectangle(amount, top=26 + 29 * smooth((t - 0.25) / 0.4), bottom=80, left=37, right=82)
            self.eye_position((47, 28 + 45 * amount), (64, 33 + 40 * amount))
            apply_blink(self.rig, blink)
            return
        if name == "CheckingSomething":
            if e > 0.05:
                self.original_wire.hide_render = True
                self.visible("GlassesLeft", "GlassesRight", "GlassesBridge")
            dy = 6 * e * math.sin(t * math.pi * 3)
            self.eye_position((47, 28 + 9 * e + dy), (64, 33 + 5 * e + dy))
            for key in ["GlassesLeft", "GlassesRight", "GlassesBridge"]:
                self.translate(self.props[key], 0, dy)
            self.gaze(0.5 * math.sin(t * math.tau * 2) * e, -0.5 * e)
            apply_blink(self.rig, blink * 0.5)
            return
        if name == "Writing":
            self.morph_to(
                path(
                    [
                        (88, 55),
                        (78, 70),
                        (60, 75),
                        (46, 66),
                        (45, 22),
                        (58, 9),
                        (68, 18),
                        (64, 49),
                        (57, 61),
                        (52, 54),
                        (55, 42),
                    ]
                ),
                e,
            )
            if e > 0.05:
                self.paper.hide_render = True
                self.visible("Notepad", "Pencil", "Graphite")
            for key in ["Pencil", "Graphite"]:
                self.translate(self.props[key], 2 * math.sin(t * math.tau * 5) * e, 2 * math.cos(t * math.tau * 5) * e)
            self.gaze(0.4 * e, -0.6 * e)
            apply_blink(self.rig, blink * 0.6)
            return
        if name == "Searching":
            if e > 0.05:
                self.paper.hide_render = True
                self.visible("Telescope", "TelescopeLens")
            scan = math.sin(t * math.tau * 1.5) * e
            self.morph_to(
                path(
                    [
                        (84 + 4 * scan, 40 - 2 * scan),
                        (72, 55),
                        (67, 73),
                        (55, 76),
                        (46, 64),
                        (46, 20),
                        (58, 9),
                        (68, 18),
                        (65, 54),
                        (56, 61),
                        (54, 47),
                    ]
                ),
                e,
            )
            for key in ["Telescope", "TelescopeLens"]:
                self.translate(self.props[key], scan * 4, -scan * 2)
            self.gaze(0.6 * scan, 0.3 * scan)
            apply_blink(self.rig, blink * 0.3)
            return
        if name == "Print":
            height = 5 + 15 * math.sin(t * math.pi) ** 2
            target = path(
                [
                    (105, 82),
                    (82, 82),
                    (105, 78),
                    (82, 74),
                    (105, 70),
                    (82, 66),
                    (75, 55),
                    (72, 37),
                    (61, 45),
                    (60, 65),
                    (50, 78),
                    (39, 69),
                    (38, 19),
                    (49, 8),
                    (56, 18),
                    (53, 55),
                    (62, 61),
                    (72, 45),
                ]
            )
            self.morph_to(target, e)
            self.eye_position((47 + 27 * e, 28 + 2 * e), (64 + 9 * e, 33 + 12 * e))
            self.paper_rectangle(0.15 * e, top=25, bottom=85 - height * 0.1)
            apply_blink(self.rig, blink)
            return
        if name == "Processing":
            angle = 0.2 * math.sin(t * math.tau * 4)
            target = path(
                [
                    (40 + 10 * angle, 20),
                    (70, 67),
                    (80, 79),
                    (92, 75),
                    (82, 60),
                    (51, 28),
                    (44, 21),
                    (48, 28),
                    (66, 62),
                    (61, 74),
                    (48, 75),
                    (42, 65),
                    (70 - 10 * angle, 18),
                ]
            )
            self.morph_to(target, e)
            self.eye_position((47 + 9 * e, 28 + 3 * e), (64 + 3 * e, 33 - 4 * e))
            if e > 0.05:
                self.paper.hide_render = True
                for i in range(6):
                    self.visible(f"PaperStrip{i}")
                    self.translate(
                        self.props[f"PaperStrip{i}"], 3 * math.sin(t * math.tau * 3 + i), 8 * math.sin(t * math.tau + i)
                    )
            apply_blink(self.rig, blink * 0.4)
            return
        if name == "SendMail":
            flight = smooth((t - 0.28) / 0.2) * (1 - smooth((t - 0.85) / 0.15))
            if e > 0.05:
                self.paper.hide_render = True
                self.visible("PlaneWingA", "PlaneWingB")
            size = 1 - 0.75 * flight
            before = self.rig.matrix_world.copy()
            self.body_transform(
                (size, size, size),
                rotation=2 * math.tau * smooth((t - 0.28) / 0.57),
                dx=30 * math.sin(t * math.tau * 3) * flight,
                dy=(-28 + 18 * math.cos(t * math.tau * 3)) * flight,
            )
            delta = self.rig.matrix_world @ before.inverted()
            for key in ["PlaneWingA", "PlaneWingB"]:
                self.props[key].matrix_world = delta @ self.props[key].matrix_world
            self.gaze(0.4 * e, 0.5 * e)
            return
        if name == "GetArtsy":
            target = path([(16, 42), (22, 24), (42, 13), (62, 13), (83, 24), (96, 43)])
            self.morph_to(target, e)
            if e > 0.05:
                self.paper.hide_render = True
                self.visible(*[f"MobileRing{i}" for i in range(3)], *[f"MobileBar{i}" for i in range(3)])
            self.eye_position((47 - 20 * e, 28 + 21 * e), (64 + 11 * e, 33 + 20 * e))
            self.rig.pose.bones["eye.R"].scale *= 1 + 1.4 * e
            self.rig.pose.bones["eye.L"].scale *= 1 - 0.25 * e
            for i in range(3):
                self.translate(self.props[f"MobileRing{i}"], 2 * e * math.sin(t * math.tau * 2 + i), 0)
            apply_blink(self.rig, blink)
            return
        raise AssertionError(f"Action has no motion recipe: {name}")
