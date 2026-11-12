"""Exact closest points between every pair of finite line segments (NumPy only)."""

import numpy as np


def segment_distances(points):
    points = np.asarray(points, dtype=float)
    start, direction = points[:-1], np.diff(points, axis=0)
    w = start[:, None] - start[None, :]
    a = np.sum(direction * direction, axis=1)[:, None]
    c = a.T
    b = direction @ direction.T
    d = np.sum(direction[:, None, :] * w, axis=2)
    e = np.sum(direction[None, :, :] * w, axis=2)
    determinant = a * c - b * b
    safe_a, safe_c = np.maximum(a, 1e-20), np.maximum(c, 1e-20)
    ss = (b * e - c * d) / np.where(abs(determinant) > 1e-20, determinant, 1)
    tt = (a * e - b * d) / np.where(abs(determinant) > 1e-20, determinant, 1)
    valid = (determinant > 1e-20) & (ss >= 0) & (ss <= 1) & (tt >= 0) & (tt <= 1)
    candidates = [
        (ss, tt, valid),
        (np.zeros_like(b), np.clip(e / safe_c, 0, 1), None),
        (np.ones_like(b), np.clip((b + e) / safe_c, 0, 1), None),
        (np.clip(-d / safe_a, 0, 1), np.zeros_like(b), None),
        (np.clip((b - d) / safe_a, 0, 1), np.ones_like(b), None),
    ]
    best = np.full(b.shape, np.inf)
    best_s, best_t = np.zeros_like(b), np.zeros_like(b)
    for s, t, interior in candidates:
        delta = w + s[:, :, None] * direction[:, None, :] - t[:, :, None] * direction[None, :, :]
        distance2 = np.sum(delta * delta, axis=2)
        choose = distance2 < best
        if interior is not None:
            choose &= interior
        best[choose] = distance2[choose]
        best_s[choose], best_t[choose] = s[choose], t[choose]
    return np.sqrt(best), best_s, best_t
