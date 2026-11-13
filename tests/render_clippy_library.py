"""Render verified keyed library poses, with resumable/disjoint worker shards."""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy


def render(folder, preview=False, shard=0, shards=1, actions=None):
    manifest = json.loads((folder / "manifest.json").read_text())
    bpy.ops.wm.open_mainfile(filepath=str(folder / "all-animations.blend"))
    scene = bpy.context.scene
    target = folder / "preview" if preview else folder
    target.mkdir(exist_ok=True)
    scene.cycles.samples = 64 if preview else manifest["samples"]
    scene.render.use_persistent_data = True
    scene.render.resolution_x, scene.render.resolution_y = manifest["pixel_size"]
    scene.render.resolution_percentage = 50 if preview else 100
    queue = {}
    for name in actions or manifest["sequences"]:
        items = manifest["sequences"][name]
        selected = [items[round((len(items) - 1) * t)] for t in [0.2, 0.5, 0.8]] if preview else items
        for item in selected:
            queue.setdefault(item["file"], item["frame"])
    if not preview:
        for name, items in manifest.get("reference_anchors", {}).items():
            if actions is not None and name not in actions:
                continue
            for item in items:
                queue.setdefault(item["file"], item["frame"])
    completed = 0
    for index, (filename, frame) in enumerate(queue.items()):
        if index % shards != shard:
            continue
        path = target / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > 0:
            completed += 1
            continue
        scene.frame_set(math.floor(frame), subframe=frame - math.floor(frame))
        bpy.context.view_layer.update()
        # Export workers may watch this directory while Blender is rendering.
        # Publish only complete PNGs; interrupted writes stay resumable.
        temporary = path.with_name(f".{path.stem}.rendering.png")
        scene.render.filepath = str(temporary)
        bpy.ops.render.render(write_still=True)
        if not temporary.is_file():
            raise RuntimeError(f"Missing rendered frame: {filename}")
        temporary.replace(path)
        completed += 1
        print("RENDERED", filename, completed, flush=True)
    (target / f"render-worker-{shard}.json").write_text(
        json.dumps({"completed": completed, "shard": shard, "shards": shards, "preview": preview}) + "\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--preview", action="store_true")
    p.add_argument("--shard", type=int, default=0)
    p.add_argument("--shards", type=int, default=1)
    p.add_argument("--actions", nargs="+")
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    render(a.folder, a.preview, a.shard, a.shards, a.actions)
