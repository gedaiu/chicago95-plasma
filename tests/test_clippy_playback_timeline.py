from fractions import Fraction

import pytest
from clippy_all_catalog import catalog
from clippy_playback_timeline import action_seed, anchors, next_index, samples, trace


def test_forced_wave_branches_and_writing_loop():
    data = catalog()
    for roll in range(100):
        assert next_index(data["Wave"]["frames"], 6, False, roll) == (9, "branch")
        assert next_index(data["Wave"]["frames"], 14, False, roll) == (26, "branch")
        assert next_index(data["Writing"]["frames"], 53, False, roll)[0] in [13, 26, 32]
    assert next_index(data["Writing"]["frames"], 30, True, 0) == (55, "exit")


def test_long_hold_and_exact_subframe_anchor():
    events = trace({"frames": [{"duration": 2400}, {"duration": 10}, {"duration": 100}]})
    p = anchors(events)
    assert p[:3] == [(1, 0, 0, "source"), (139, 0, 0, "hold"), (145, 1, 1, "source")]
    assert p[3][0] == Fraction(728, 5)  # 145.6, never rounded to 146
    frames = samples(events)
    assert frames[143]["source_index"] == 0
    assert frames[144]["source_index"] == 1
    assert frames[145]["source_index"] == 2


def test_zero_duration_control_is_traversed_not_rendered():
    events = trace({"frames": [{"duration": 0}, {"duration": 100}]})
    assert len(events) == 2
    assert {s["source_index"] for s in samples(events)} == {1}
    assert anchors(events)[0][1] == 1


def test_cycle_fails_instead_of_truncating():
    with pytest.raises(ValueError, match="did not terminate"):
        trace(
            {"frames": [{"duration": 0, "branching": {"branches": [{"frameIndex": 0, "weight": 100}]}}]}, max_steps=10
        )


def test_all_actions_reproducible_and_every_exit_boundary_terminates():
    for name, action in catalog().items():
        events = trace(action, seed=action_seed(name))
        assert events == trace(action, seed=action_seed(name))
        for e in events:
            assert e["duration_ms"] == action["frames"][e["source_index"]]["duration"]
        # Exercise stop requests at every boundary on several normal paths.
        for seed in range(3):
            route = trace(action, seed=seed)
            for stop in {e["timestamp_ms"] for e in route}:
                assert trace(action, seed=seed, stop_ms=stop)
        rendered = samples(events)
        elapsed = sum(e["duration_ms"] for e in events)
        assert abs(len(rendered) / 60 * 1000 - elapsed) <= 1000 / 120


def test_dense_wave_samples_use_branch_target_not_dense_frame_index():
    action = catalog()["Wave"]
    events = trace(action, seed=action_seed("Wave"))
    assert [e["source_index"] for e in events] == list(range(7)) + list(range(9, 15)) + [26]
    output = samples(events)
    assert len(output) == 84
    assert output[42]["source_index"] == 9  # 700 ms: unconditional jump from source 6.
    assert output[78]["source_index"] == 26  # Exit skips the unused waving alternatives.
    assert output[42]["timestamp_numerator"] == 700
