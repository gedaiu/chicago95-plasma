"""Prepare a small all-action render, reusing only exactly identical channel states."""

import argparse
import array
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from retime_clippy_library import curves


def prepare(folder, output):
    output.mkdir(parents=True, exist_ok=False)
    os.link(folder / "all-animations.blend", output / "all-animations.blend")
    shutil.copy2(folder / "timing-verification.json", output / "timing-verification.json")
    m = json.loads((folder / "manifest.json").read_text())
    m["pixel_size"] = [248, 186]
    m["samples"] = 16
    bpy.ops.wm.open_mainfile(filepath=str(output / "all-animations.blend"))
    assert not bpy.context.scene.cycles.use_animated_seed
    channels = list(curves())
    cache = {}
    for items in [*m["sequences"].values(), *m["reference_anchors"].values()]:
        for item in items:
            signature = hashlib.sha256(
                array.array("f", (c.evaluate(item["frame"]) for _, _, c in channels)).tobytes()
            ).hexdigest()
            item["file"] = cache.setdefault(signature, item["file"])
    m["unique_render_states"] = len(cache)
    (output / "manifest.json").write_text(json.dumps(m, indent=2) + "\n")
    print("Exact channel states to render:", len(cache), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    prepare(a.folder, a.output)
