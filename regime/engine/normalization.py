"""Scaling helpers that map raw quantities onto the ``[-100, 100]`` scale.

Using bounded, monotone transforms (``tanh``) keeps every component
interpretable and prevents a single extreme reading from producing a score
outside the documented range.
"""

from __future__ import annotations

import math


def clip100(x: float) -> float:
    return max(-100.0, min(100.0, float(x)))


def tanh_100(x: float, scale: float = 1.0) -> float:
    """Map an unbounded z-like value to ``[-100, 100]`` via ``tanh``.

    ``scale`` divides the input first: larger scale = gentler slope. A value of
    ``scale`` roughly marks the input that reaches ~76 (tanh(1)*100).
    """

    if x is None or not math.isfinite(x):
        return 0.0
    if scale <= 0:
        scale = 1.0
    return clip100(100.0 * math.tanh(x / scale))


def mean_available(values) -> float:
    """Mean of the non-None entries; 0.0 when all are missing."""

    vals = [v for v in values if v is not None and math.isfinite(v)]
    if not vals:
        return 0.0
    return sum(vals) / len(vals)


def weighted_available(pairs) -> float:
    """Weighted mean over ``(value, weight)`` pairs, renormalising weights to
    the entries that are actually present. Missing entries drop out entirely
    rather than being counted as zero (neutral)."""

    num = 0.0
    den = 0.0
    for value, weight in pairs:
        if value is None or not math.isfinite(value) or weight <= 0:
            continue
        num += value * weight
        den += weight
    if den == 0:
        return 0.0
    return num / den
