"""Separate overlapping eyelid shells, smooth their surfaces and reduce render noise."""

import bpy

EYELIDS = ("Cube.002", "Cube.003", "Cube.005", "Cube.006")
EYES = ("Cube.001", "Cube.004")
LOWER_EYELIDS = ("Cube.003", "Cube.006")
LOWER_SHELL_SCALE = 0.995


def configure(scene, samples=192):
    for name in EYES:
        modifier = bpy.data.objects[name].modifiers["Subdivision"]
        modifier.levels = modifier.render_levels = 3
    # The source's two metal shells occupy almost the same surface when open.
    # A tiny radial inset makes their ordering stable instead of producing dark
    # patches where nearly coincident triangles alternately shade the rim.
    for name in LOWER_EYELIDS:
        mesh = bpy.data.objects[name].data
        previous = mesh.get("clippy_lower_shell_scale", 1.0)
        if previous != LOWER_SHELL_SCALE:
            for vertex in mesh.vertices:
                vertex.co *= LOWER_SHELL_SCALE / previous
            mesh["clippy_lower_shell_scale"] = LOWER_SHELL_SCALE
    for name in EYELIDS:
        obj = bpy.data.objects[name]
        for modifier in list(obj.modifiers):
            if modifier.type == "NODES" and modifier.name == "Auto Smooth":
                obj.modifiers.remove(modifier)
        modifier = obj.modifiers.get("Clippy smooth eyelids")
        if modifier is None:
            modifier = obj.modifiers.new("Clippy smooth eyelids", "SUBSURF")
        modifier.levels = modifier.render_levels = 2
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.01
    scene.cycles.adaptive_min_samples = min(64, samples)
