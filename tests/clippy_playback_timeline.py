"""Deterministic source playback traces and exact 60-fps time correspondence.

Durations are display holds, not author-supplied tween lengths. The optional
100-ms tail interpolation is an explicit reconstruction policy, never source data.
"""

import bisect
import hashlib
import random
from fractions import Fraction


def next_index(frames, index, stopping, roll):
    frame = frames[index]
    if stopping and "exitBranch" in frame:
        return frame["exitBranch"], "exit"
    for branch in frame.get("branching", {}).get("branches", []):
        if roll < branch["weight"]:
            return branch["frameIndex"], "branch"
        roll -= branch["weight"]
    return index + 1, "next"


def trace(action, *, seed=0, stop_ms=5000, max_steps=10000):
    """Request a graceful stop at stop_ms; never silently truncate an exit path."""
    frames = action["frames"]
    rng = random.Random(seed)
    index, elapsed = 0, 0
    events = []
    for _ in range(max_steps):
        if index == len(frames):
            return events
        if not 0 <= index < len(frames):
            raise ValueError(f"Invalid branch target {index}")
        frame = frames[index]
        duration = frame["duration"]
        if duration < 0:
            raise ValueError("Negative duration")
        stopping = stop_ms is not None and elapsed + duration >= stop_ms
        roll = rng.randrange(100)
        target, reason = next_index(frames, index, stopping, roll)
        events.append(
            dict(
                source_index=index,
                timestamp_ms=elapsed,
                duration_ms=duration,
                sound=frame.get("sound"),
                next_source_index=target,
                transition=reason,
                roll=roll,
                stopping=stopping,
            )
        )
        elapsed += duration
        index = target
    raise ValueError("Playback did not terminate; zero-time cycle or nonterminating exit path")


def action_seed(name):
    return int.from_bytes(hashlib.sha256(name.encode()).digest()[:4], "big")


def samples(events, fps=60):
    timed = [e for e in events if e["duration_ms"]]
    if not timed:
        return []
    duration = timed[-1]["timestamp_ms"] + timed[-1]["duration_ms"]
    count = (duration * fps + 500) // 1000
    starts = [e["timestamp_ms"] for e in timed]
    result = []
    for tick in range(count):
        time = Fraction(tick * 1000, fps)
        occurrence = bisect.bisect_right(starts, time) - 1
        e = timed[occurrence]
        result.append(
            dict(
                tick=tick,
                timestamp_numerator=time.numerator,
                timestamp_denominator=time.denominator,
                source_index=e["source_index"],
                occurrence=occurrence,
                duration_ms=round(Fraction((tick + 1) * 1000, fps)) - round(time),
            )
        )
    return result


def anchors(events, start_frame=1, fps=60, tween_ms=100):
    """Source poses land on exact (possibly fractional) frames; long holds stay still."""
    timed = [e for e in events if e["duration_ms"]]
    points = []
    for occurrence, event in enumerate(timed):
        start = Fraction(start_frame) + Fraction(event["timestamp_ms"] * fps, 1000)
        end = start + Fraction(event["duration_ms"] * fps, 1000)
        points.append((start, event["source_index"], occurrence, "source"))
        tail = min(tween_ms, event["duration_ms"]) if occurrence + 1 < len(timed) else 0
        hold_end = end - Fraction(tail * fps, 1000)
        if hold_end > start:
            points.append((hold_end, event["source_index"], occurrence, "hold"))
    return points
