"""One pointing excursion per action, indexed against the original ACS timeline."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POINT_PROGRESS = {
    "GestureLeft": [0, 0.12, 0.3, 0.6, 0.85, 1, 1, 1, 1, 1, 1, 1, 0.6, 0.3, 0.12, 0],
    "GestureRight": [0, 1 / 6, 1 / 3, 0.5, 0.65, 0.85, 1, 1, 1, 1, 1, 1, 0.65, 0.5, 1 / 3, 1 / 6, 0],
}
GESTURE_BLINK = {"GestureLeft": {6: 0.4, 7: 1, 8: 0.3}, "GestureRight": {7: 0.5, 8: 1}}


def source_timeline():
    text = (ROOT / "data/clippy/agent.js").read_text()
    data = json.loads(text[text.index("{") : text.rindex("}") + 1])["animations"]
    result = {}
    for action in ("RestPose", "Blink", "GestureLeft", "GestureRight"):
        frames = data["Idle1_1" if action == "Blink" else action]["frames"]
        if action == "Blink":
            frames = frames[:5]
        result[action] = [
            {
                "original_index": i,
                "duration_ms": frame["duration"],
                "progress": POINT_PROGRESS[action][i] if action in POINT_PROGRESS else 0,
                "blink": ([0, 0.33, 1, 0.66, 0][i] if action == "Blink" else GESTURE_BLINK.get(action, {}).get(i, 0)),
            }
            for i, frame in enumerate(frames)
        ]
    return result
