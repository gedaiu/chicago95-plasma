"""Summarize exact-pixel measurements from one or more parity run directories."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean


RETIRED_CASES = frozenset({
    "win95/file-manager/gtk4/navigation",
    "win98/file-manager/gtk4/navigation",
})


def measurements(directory):
    for path in sorted(directory.rglob("comparison.metrics.json")):
        for parent in path.parents:
            if parent.name == "visual":
                key = path.relative_to(parent)
                if len(key.parts) == 5 and key.parts[0].endswith("dpi") and key.parts[0][:-3].isdecimal():
                    dpi, theme, component, renderer, filename = key.parts
                    key = Path(theme, component, renderer, dpi, filename)
                if key.parent.as_posix() in RETIRED_CASES:
                    break
                theme, component, *_ = key.parts
                yield theme, component, key, json.loads(path.read_text())
                break


def percent(value):
    return f"{value:.2%}"


def row(label, cases):
    same_size = [case for case in cases if case["rendered_size"] == case["reference_size"]]
    exact = sum(case["changed_pixels"] == 0 for case in same_size)
    count = len(cases)
    if not same_size:
        return f"| {label} | 0/{count} | {count} | — | — |"
    matches = [1 - case["changed_pixels"] / case["compared_pixels"] for case in same_size]
    return (
        f"| {label} | {exact}/{count} | {count - len(same_size)} "
        f"| {percent(mean(matches))} | {percent(min(matches))} |"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs="+", type=Path, help="pytest base temp directories, newest reruns last")
    args = parser.parse_args()
    cases = {}
    for directory in args.directories:
        for theme, component, key, result in measurements(directory):
            cases[key] = theme, component, result
    if not cases:
        parser.error("no parity measurements found in the supplied directories")

    themes, components = defaultdict(list), defaultdict(list)
    for theme, component, result in cases.values():
        themes[theme].append(result)
        components[(theme, component)].append(result)

    print(
        "The average gives each pixel comparison equal weight. Pixel percentages cover "
        "same-size captures. Geometry mismatches appear in their own column. Motion "
        "timing, coverage checks and cases that produced no comparable capture are outside this report.\n"
    )
    for title, groups in (("By theme", themes), ("By theme and component", components)):
        print(f"## {title}\n")
        print("| Surface | Exact captures | Size mismatches | Average pixel match | Lowest pixel match |")
        print("| --- | ---: | ---: | ---: | ---: |")
        for key, group in sorted(groups.items()):
            print(row(" / ".join(key) if isinstance(key, tuple) else key, group))
        print()


if __name__ == "__main__":
    main()
