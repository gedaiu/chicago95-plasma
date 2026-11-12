"""Canonical original Clippy action inventory; no fallback or placeholder actions."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def catalog():
    text = (ROOT / "data/clippy/agent.js").read_text()
    return json.loads(text[text.index("{") : text.rindex("}") + 1])["animations"]


def inventory():
    groups = {}
    result = {}
    for name, action in catalog().items():
        signature = hashlib.sha256(json.dumps(action["frames"], sort_keys=True).encode()).hexdigest()
        canonical = groups.setdefault(signature, name)
        result[name] = {
            "frames": len(action["frames"]),
            "duration_ms": sum(f["duration"] for f in action["frames"]),
            "canonical": canonical,
            "source_signature": signature,
            "branch_frames": [i for i, f in enumerate(action["frames"]) if f.get("branching") or "exitBranch" in f],
        }
    return result


if __name__ == "__main__":
    print(json.dumps(inventory(), indent=2))
