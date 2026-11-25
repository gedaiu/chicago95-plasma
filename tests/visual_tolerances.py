"""Opt-in visual tolerances keyed by a comparison's path under visual/."""

import json
import os
from functools import cache
from pathlib import Path

import numpy as np


@cache
def read_policy(path):
    policy = json.loads(Path(path).read_text())
    if policy.get("version") != 1 or not isinstance(policy.get("cases"), dict):
        raise ValueError(f"{path}: expected a version 1 visual tolerance policy")
    return policy["cases"]


def comparison_key(directory):
    for parent in directory.parents:
        if parent.name == "visual":
            return directory.relative_to(parent).as_posix()
    return None


def tolerance_map(size, rules):
    width, height = size
    tolerance = np.zeros((height, width), dtype=np.uint8)
    for rule in rules:
        x, y, columns, rows = (rule[field] for field in ("x", "y", "width", "height"))
        limit = rule["max_channel_delta"]
        if (
            any(type(value) is not int for value in (x, y, columns, rows, limit))
            or x < 0 or y < 0 or columns < 1 or rows < 1
            or x + columns > width or y + rows > height
            or not 0 <= limit <= 255
        ):
            raise ValueError(f"Invalid visual tolerance region {rule!r} for {width}×{height}")
        tolerance[y:y + rows, x:x + columns] = limit
    return tolerance


def tolerance_for(directory, size):
    policy_path = os.environ.get("CHICAGO95_VISUAL_TOLERANCES")
    if not policy_path:
        return None
    key = comparison_key(directory)
    case = read_policy(policy_path).get(key)
    if case is None:
        return None
    if tuple(case["size"]) != size:
        raise ValueError(f"Visual tolerance for {key} expects {case['size']}, got {size}")
    return tolerance_map(size, case["regions"])
