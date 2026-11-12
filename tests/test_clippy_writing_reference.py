"""Freeze meaningful source choreography that the former Writing stub missed."""

import numpy as np
from clippy_writing_reference import extract, hull


def area(points):
    a = np.asarray(points)
    b = np.roll(a, -1, axis=0)
    return abs(float((a[:, 0] * b[:, 1] - b[:, 0] * a[:, 1]).sum())) / 2


def test_writing_reference_retains_sheet_and_pencil_entry():
    rows = extract()
    assert len(rows) == 61
    assert sum(r["duration_ms"] for r in rows) == 8400
    assert all(area(r["paper_polygon"]) > 100 for r in rows)
    assert all(r["pencil_endpoints"] is None for r in rows[:11])
    assert rows[11]["pencil_endpoints"] is not None
    assert rows[58]["pencil_endpoints"] is not None
    assert rows[59]["pencil_endpoints"] is None
    assert rows[0]["reference_sha256"] == rows[-1]["reference_sha256"]
    assert rows[0]["paper_polygon"] == rows[-1]["paper_polygon"]
    assert area(rows[8]["paper_polygon"]) > 2000  # Sheet still large while being lifted.
    assert area(rows[16]["paper_polygon"]) < 600  # Sheet turned toward the writer.
    assert area(rows[56]["paper_polygon"]) < area(hull(rows[56]["paper_polygon"])) * 0.85
