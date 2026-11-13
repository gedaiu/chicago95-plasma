from clippy_all_catalog import catalog
from clippy_branch_coverage import routes
from clippy_playback_timeline import next_index


def test_every_route_is_legal_and_stopping_never_reverses():
    for action in catalog().values():
        result = routes(action)
        visited = set()
        for route in result["routes"]:
            index = elapsed = 0
            stopping = False
            for event in route:
                assert event["source_index"] == index and event["timestamp_ms"] == elapsed
                assert not stopping or event["stopping"]
                stopping = event["stopping"]
                target, reason = next_index(action["frames"], index, stopping, event["roll"])
                assert (target, reason) == (event["next_source_index"], event["transition"])
                visited.add(index)
                elapsed += action["frames"][index]["duration"]
                index = target
            assert index == len(action["frames"])
        assert visited == set(result["reachable_source_indices"])
        assert visited | set(result["unreachable_source_indices"]) == set(range(len(action["frames"])))


def test_wave_coverage_includes_head_down_alternative():
    result = routes(catalog()["Wave"])
    assert set(range(15, 26)) <= {e["source_index"] for r in result["routes"] for e in r}
    assert len(result["routes"]) > 1


def test_idle_atom_does_not_only_test_immediate_exit():
    result = routes(catalog()["IdleAtom"])
    assert set(range(10, 34)) <= {e["source_index"] for r in result["routes"] for e in r}
