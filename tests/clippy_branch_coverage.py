"""Find legal normal/stop paths covering every reachable original frame.

Unlike a single random demonstration, these routes expose rare variants and exit
choreography. Stop requests are attached to a transition occurrence; once stopping,
playback never returns to the running state. Every edge is checked with the player.
"""

from collections import deque

from clippy_playback_timeline import next_index


def edges(frames, state):
    index, stopping = state
    if index == len(frames):
        return []
    choices = {}
    for stop in [True] if stopping else [False, True]:
        for roll in range(100):
            target, reason = next_index(frames, index, stop, roll)
            if not 0 <= target <= len(frames):
                raise ValueError(f"Invalid target {target}")
            choices.setdefault(
                (target, stop),
                dict(source_index=index, next_source_index=target, stopping=stop, roll=roll, transition=reason),
            )
    return list(choices.items())


def paths_from(frames, start, adjacency):
    paths = {start: []}
    queue = deque([start])
    while queue:
        state = queue.popleft()
        for target, event in adjacency[state]:
            if target in paths:
                continue
            paths[target] = paths[state] + [event]
            queue.append(target)
    return paths


def routes(action):
    frames = action["frames"]
    adjacency = {(i, stop): edges(frames, (i, stop)) for i in range(len(frames) + 1) for stop in (False, True)}
    prefixes = paths_from(frames, (0, False), adjacency)
    candidates = []
    for state, prefix in prefixes.items():
        suffixes = paths_from(frames, state, adjacency)
        ends = [p for s, p in suffixes.items() if s[0] == len(frames)]
        if not ends:
            raise ValueError(f"Reachable state has no terminating path: {state}")
        path = prefix + min(ends, key=len)
        if not path:
            continue
        candidates.append(path)
    reachable = {s[0] for s in prefixes if s[0] < len(frames)}
    uncovered = set(reachable)
    selected = []
    while uncovered:
        path = max(candidates, key=lambda p: (len({e["source_index"] for e in p} & uncovered), -len(p)))
        coverage = {e["source_index"] for e in path}
        if not coverage & uncovered:
            raise ValueError("Coverage stalled")
        elapsed = 0
        events = []
        for original_event in path:
            event = dict(original_event)
            duration = frames[event["source_index"]]["duration"]
            event.update(timestamp_ms=elapsed, duration_ms=duration, sound=frames[event["source_index"]].get("sound"))
            elapsed += duration
            events.append(event)
        selected.append(events)
        uncovered -= coverage
    return dict(
        routes=selected,
        reachable_source_indices=sorted(reachable),
        unreachable_source_indices=sorted(set(range(len(frames))) - reachable),
    )
