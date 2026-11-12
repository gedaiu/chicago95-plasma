import numpy as np
import pytest
from clippy_collision_geometry import segment_distances


def test_crossing_between_samples_is_detected():
    p = np.array([[-2, 0, 0], [2, 0, 0], [0, -2, 0], [0, 2, 0]])
    distance, s, t = segment_distances(p)
    assert np.linalg.norm(p[0] - p[2]) > 2
    assert distance[0, 2] == pytest.approx(0)
    assert s[0, 2] == pytest.approx(0.5)
    assert t[0, 2] == pytest.approx(0.5)


@pytest.mark.parametrize(
    "points,expected",
    [
        ([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], 1),
        ([[0, 0, 0], [1, 0, 0], [2, 1, 0], [3, 1, 0]], np.sqrt(2)),
        ([[-1, 0, 0], [1, 0, 0], [0, -1, 2], [0, 1, 2]], 2),
        ([[0, 0, 0], [0, 0, 0], [1, 0, 0], [2, 0, 0]], 1),
    ],
)
def test_parallel_endpoints_skew_and_degenerate(points, expected):
    distance, _, _ = segment_distances(points)
    assert distance[0, 2] == pytest.approx(expected)
    np.testing.assert_allclose(distance, distance.T, atol=1e-10)
