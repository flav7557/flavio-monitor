"""Confidence (0-100) — how *trustworthy* a direction is, independent of the
direction itself. High confidence means broad, aligned, well-covered, fresh and
persistent evidence; it says nothing about bullish vs bearish.
"""

from __future__ import annotations

import statistics
from typing import List

from ..config import RegimeConfig
from .models import GroupResult, InstrumentScore


def collect_instruments(group: GroupResult) -> List[InstrumentScore]:
    out: List[InstrumentScore] = []
    for child in group.children:
        if isinstance(child, InstrumentScore):
            out.append(child)
        elif isinstance(child, GroupResult):
            out.extend(collect_instruments(child))
    return out


def instrument_horizon_agreement(inst: InstrumentScore) -> float:
    """Fraction of momentum horizons pointing the same way (0.5 = no info)."""

    scores = list(inst.momentum_horizon_scores.values())
    if not scores:
        return 0.5
    pos = sum(1 for s in scores if s > 0)
    neg = sum(1 for s in scores if s < 0)
    n = len(scores)
    return max(pos, neg) / n


def compute_confidence(
    group: GroupResult, cfg: RegimeConfig, persistence_frac: float = 1.0
) -> float:
    instruments = collect_instruments(group)
    eligible = [i for i in instruments if i.eligible]

    breadth_pct = max(group.pct_bull, group.pct_bear)          # 0..1
    magnitude = min(1.0, abs(group.score) / 60.0)              # 0..1

    if eligible:
        horizon_agreement = statistics.mean(
            instrument_horizon_agreement(i) for i in eligible
        )
    else:
        horizon_agreement = 0.0

    child_scores = [
        c.score for c in group.children
        if isinstance(c, GroupResult) and c.n_active > 0
    ]
    if len(child_scores) >= 2:
        dispersion = statistics.pstdev(child_scores)
        cluster_agreement = max(0.0, 1.0 - min(1.0, dispersion / 60.0))
    else:
        cluster_agreement = breadth_pct

    coverage = (group.n_active / group.n_children) if group.n_children else 0.0
    if eligible:
        freshness = sum(1 for i in eligible if not i.stale) / len(eligible)
    else:
        freshness = 0.0

    parts = {
        "breadth": breadth_pct,
        "magnitude": magnitude,
        "horizon_agreement": horizon_agreement,
        "cluster_agreement": cluster_agreement,
        "persistence": max(0.0, min(1.0, persistence_frac)),
        "coverage": coverage,
        "freshness": freshness,
    }

    weights = cfg.conf_weights
    total_w = sum(weights.get(k, 0.0) for k in parts)
    if total_w <= 0:
        return 0.0
    value = sum(parts[k] * weights.get(k, 0.0) for k in parts) / total_w
    return round(100.0 * max(0.0, min(1.0, value)), 1)
