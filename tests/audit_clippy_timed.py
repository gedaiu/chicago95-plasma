"""Resumable surface audit of actual 60-fps samples, with source correspondence."""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_clippy_collisions import inspect_pose


def audit(folder, output, shard, shards):
    manifest = json.loads((folder / "manifest.json").read_text())
    fingerprint = hashlib.sha256((folder / "all-animations.blend").read_bytes()).hexdigest()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(folder / "all-animations.blend"))
    queue = {}
    for name, items in manifest["sequences"].items():
        for item in items:
            queue.setdefault(item["file"], dict(action=name, **item))
    for index, (filename, item) in enumerate(queue.items()):
        if index % shards != shard:
            continue
        target = output / (hashlib.sha256(filename.encode()).hexdigest() + ".json")
        if target.exists():
            assert json.loads(target.read_text())["blend_sha256"] == fingerprint
            continue
        frame = item["frame"]
        bpy.context.scene.frame_set(math.floor(frame), subframe=frame % 1)
        bpy.context.view_layer.update()
        row = dict(blend_sha256=fingerprint, file=filename, frame=frame, **inspect_pose())
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(row) + "\n")
        temp.replace(target)
        if index % 30 == shard:
            print("AUDITED", index, "/", len(queue), item["action"], flush=True)


def summarize(folder, output):
    m = json.loads((folder / "manifest.json").read_text())
    fingerprint = hashlib.sha256((folder / "all-animations.blend").read_bytes()).hexdigest()
    cache = {}
    for path in output.glob("*.json"):
        r = json.loads(path.read_text())
        if "file" in r:
            assert r["blend_sha256"] == fingerprint
            cache[r["file"]] = r
    summary = {}
    rows = {}
    for name, items in m["sequences"].items():
        records = []
        contacts = {}
        for item in items:
            r = cache[item["file"]]
            bad = [c for c in r["object_contacts"] if c["kind"] != "source_eye_assembly"]
            bad_self = [c for c in r["self_intersections"] if c["kind"] != "source_pupil_eye_join_review"]
            for c in bad:
                key = " / ".join(sorted(c["objects"]))
                contacts[key] = contacts.get(key, 0) + 1
            for c in bad_self:
                key = c["object"] + " (self)"
                contacts[key] = contacts.get(key, 0) + 1
            records.append(
                dict(
                    tick=item["tick"],
                    source_index=item["source_index"],
                    frame=item["frame"],
                    object_contacts=bad,
                    self_intersections=bad_self,
                )
            )
        rows[name] = records
        summary[name] = dict(
            samples=len(items),
            samples_needing_review=sum(bool(r["object_contacts"] or r["self_intersections"]) for r in records),
            contacts=contacts,
        )
    report = dict(
        blend_sha256=fingerprint,
        unique_states_checked=len(cache),
        samples_checked=sum(len(v) for v in rows.values()),
        summary=summary,
        sequences=rows,
        scope="Evaluated triangle intersections at every output sample. Internal eye construction excluded "
        "from review counts. Other intended joins still require classification. "
        "Containment and motion between 60-fps samples are not certified.",
    )
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--shard", type=int, default=0)
    p.add_argument("--shards", type=int, default=1)
    p.add_argument("--summarize", action="store_true")
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if a.summarize:
        summarize(a.folder, a.output)
    else:
        audit(a.folder, a.output, a.shard, a.shards)
