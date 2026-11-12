"""Repair projected wire crossings using evaluated surfaces and bounded camera depth.

The centerline projection and projected tube radius are held fixed. Every proposed
repair must pass the actual triangle-surface test; no triangles are removed and
no collision is hidden by changing visibility or the camera clip planes.
"""

import math

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def crossing_segments(wire):
    wire.data.update_tag()
    bpy.context.view_layer.update()
    evaluated = wire.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        vertices = np.array([list(evaluated.matrix_world @ v.co) for v in mesh.vertices])
        faces = [tuple(t.vertices) for t in mesh.loop_triangles]
        welded = [tuple(round(c, 6) for c in v) for v in vertices]
        topology = [set(welded[i] for i in f) for f in faces]
        tree = BVHTree.FromPolygons(vertices.tolist(), faces, all_triangles=True, epsilon=0)
        hits = [(a, b) for a, b in tree.overlap(tree) if a < b and not topology[a] & topology[b]]
        if not hits:
            return 0, set()
        points = np.array([list(wire.matrix_world @ Vector(p.co[:3])) for p in wire.data.splines[0].points])
        sides, remainder = divmod(len(vertices), len(points) + 2)
        if remainder or sides < 3:
            raise ValueError("Unsupported beveled-curve topology; refusing an unverified ring mapping")
        nearest = np.linalg.norm(vertices[:, None] - points[None, :], axis=2).argmin(axis=1)
        ring_map = list(map(int, nearest))
        for start in range(2 * sides, len(vertices), sides):
            center = vertices[start : start + sides].mean(axis=0)
            ring = int(np.linalg.norm(points - center, axis=1).argmin())
            ring_map[start : start + sides] = [ring] * sides
        pairs = set()
        for a, b in hits:
            i = round(sum(ring_map[k] for k in faces[a]) / 3)
            j = round(sum(ring_map[k] for k in faces[b]) / 3)
            if i == j:
                i, j = max(0, i - 1), min(len(points) - 1, j + 1)
            pairs.add(tuple(sorted((i, j))))
        return len(hits), pairs
    finally:
        evaluated.to_mesh_clear()


def repair(wire, camera, max_iterations=180):
    original_data = wire.data
    work = original_data.copy()
    work.animation_data_clear()
    wire.data = work
    try:
        points = work.splines[0].points
        inverse = camera.matrix_world.inverted()
        local = wire.matrix_world.inverted()
        coordinates = np.array([list(inverse @ wire.matrix_world @ Vector(p.co[:3])) for p in points])
        base = -coordinates[:, 2]
        if np.any(base <= 0):
            raise ValueError("Wire lies behind the camera")
        projected = coordinates / base[:, None]
        radii = np.array([p.radius for p in points])
        initial, pairs = crossing_segments(wire)
        constraints = {}
        depths = base.copy()
        minimum_depth = max(0.5, camera.data.clip_start * 4)
        for iteration in range(max_iterations + 1):
            count, pairs = crossing_segments(wire)
            if not count:
                result = [(tuple(p.co), p.radius) for p in points]
                return result, {
                    "initial_triangle_pairs": initial,
                    "remaining_triangle_pairs": 0,
                    "iterations": iteration,
                    "minimum_camera_depth": float(depths.min()),
                    "maximum_depth_shift": float(np.max(abs(depths - base))),
                }
            if iteration == max_iterations:
                break
            for pair in pairs:
                constraints[pair] = constraints.get(pair, 0.007) + 0.003
            # Ordered depth inequalities prevent the branches from swapping sides.
            # Log depth scales the required separation with the apparent tube radius.
            logs = np.full(len(points), math.log(21.3))
            for j in range(1, len(points)):
                logs[j] = min(logs[j], logs[j - 1])
                for (i, k), gap in constraints.items():
                    if k == j:
                        logs[j] = min(logs[j], logs[i] - gap)
            depths = np.exp(logs)
            if depths.min() < minimum_depth:
                break
            for p, q, depth, radius, old_depth in zip(points, projected, depths, radii, base, strict=True):
                p.co = (*(local @ camera.matrix_world @ Vector(q * depth)), 1)
                p.radius = radius * depth / old_depth
        return None, {
            "initial_triangle_pairs": initial,
            "remaining_triangle_pairs": count,
            "iterations": iteration,
            "reason": "Depth/iteration bound reached; original geometry retained",
        }
    finally:
        wire.data = original_data
        bpy.data.curves.remove(work)
