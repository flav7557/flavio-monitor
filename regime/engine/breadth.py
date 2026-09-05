"""Breadth statistics over a set of directional children."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List


@dataclass
class Breadth:
    n: int
    bull: int
    bear: int
    neutral: int
    pct_bull: float
    pct_bear: float
    pct_neutral: float
    dominant: str
    confirming: int
    breadth_score: float          # signed, (pct_bull - pct_bear) * 100


def compute_breadth(directions: List[str]) -> Breadth:
    n = len(directions)
    if n == 0:
        return Breadth(0, 0, 0, 0, 0.0, 0.0, 0.0, "mixed", 0, 0.0)

    bull = sum(1 for d in directions if d == "bull")
    bear = sum(1 for d in directions if d == "bear")
    neutral = n - bull - bear

    if bull > bear:
        dominant, confirming = "bull", bull
    elif bear > bull:
        dominant, confirming = "bear", bear
    else:
        dominant, confirming = "mixed", 0

    return Breadth(
        n=n,
        bull=bull,
        bear=bear,
        neutral=neutral,
        pct_bull=bull / n,
        pct_bear=bear / n,
        pct_neutral=neutral / n,
        dominant=dominant,
        confirming=confirming,
        breadth_score=(bull - bear) / n * 100.0,
    )


def adaptive_min(required: int, n: int) -> int:
    """Scale a minimum-confirmation requirement down for small universes so the
    rule stays satisfiable, without letting a 1-instrument group be 'strong'."""

    if n <= 0:
        return required
    if n >= required:
        return required
    return max(1, math.ceil(0.6 * n))
