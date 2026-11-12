"""Run with Blender --python; independent fixtures for the surface collision audit."""

import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_clippy_collisions import self_intersections, surface  # noqa: E402


def check(vertices, faces):
    mesh = bpy.data.meshes.new("CollisionFixture")
    mesh.from_pydata(vertices, [], faces)
    obj = bpy.data.objects.new("CollisionFixture", mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.update()
    tree, topology = surface(obj, bpy.context.evaluated_depsgraph_get())
    result = self_intersections(tree, topology)
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    return result


def main():
    # Actual crossing between disconnected triangles must fail.
    assert check(
        [(0, 0, 0), (2, 0, 0), (0, 2, 0), (0.5, 0.5, -1), (0.5, 0.5, 1), (1.5, 0.5, 0)], [(0, 1, 2), (3, 4, 5)]
    )
    # Overlapping bounding boxes alone must not fail.
    assert not check([(0, 0, 0), (2, 0, 0), (0, 2, 0), (2, 2, 0), (2, 0.9, 0), (0.9, 2, 0)], [(0, 1, 2), (3, 4, 5)])
    # Shared edges, including duplicated cap-seam coordinates, are permitted.
    assert not check([(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)], [(0, 1, 2), (1, 3, 2)])
    assert not check([(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [(0, 1, 2), (3, 4, 5)])
    print("4 SURFACE COLLISION FIXTURES PASSED")


if __name__ == "__main__":
    main()
