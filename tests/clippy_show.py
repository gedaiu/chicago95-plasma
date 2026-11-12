"""Source-derived Show layout; Hide uses the same five frames in reverse."""

import math

# Visible alpha bounds from the five original Show frames. The first is blank.
SHOW_BOUNDS = (None, (51, 38, 80, 67), (39, 25, 92, 76), (26, 15, 100, 83), (17, 5, 111, 91))


def bounds_error(reference, candidate):
    """Maximum visible-bound displacement on an already native-size canvas."""
    boxes = [
        image.getchannel("A").point(lambda alpha: 255 if alpha >= 128 else 0).getbbox()
        for image in (reference, candidate)
    ]
    if boxes[0] is None or boxes[1] is None:
        return 0 if boxes[0] == boxes[1] else float("inf")
    return max(abs(a - b) for a, b in zip(*boxes, strict=True))


def layout(index):
    bounds = SHOW_BOUNDS[index]
    if bounds is None:
        return None
    left, top, right, bottom = bounds
    full_left, full_top, full_right, full_bottom = SHOW_BOUNDS[-1]
    # Preserve 3D proportions. Raster rounding makes the two scale ratios differ
    # slightly in the small source frames; their geometric mean balances them.
    scale = math.sqrt((right - left) * (bottom - top) / ((full_right - full_left) * (full_bottom - full_top)))
    return scale, (left + right) / 2, (top + bottom) / 2


def world_transform(scene, index):
    from mathutils import Matrix, Vector

    placement = layout(index)
    if placement is None:
        return Matrix.Identity(4)
    scale, x, y = placement
    camera = scene.camera
    view = camera.data.view_frame(scene=scene)
    depth = 21.0
    width = (max(v.x for v in view) - min(v.x for v in view)) * depth / abs(view[0].z)
    height = (max(v.y for v in view) - min(v.y for v in view)) * depth / abs(view[0].z)

    def world(px, py):
        return camera.matrix_world @ Vector(((px / 124 - 0.5) * width, (0.5 - py / 93) * height, -depth))

    left, top, right, bottom = SHOW_BOUNDS[-1]
    pivot = world((left + right) / 2, (top + bottom) / 2)
    return Matrix.Translation(world(x, y)) @ Matrix.Scale(scale, 4) @ Matrix.Translation(-pivot)
