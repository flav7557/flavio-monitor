"""Hierarchical aggregation: instruments -> clusters -> sectors -> global.

Two design choices keep the hierarchy honest:

* Breadth at a level counts its *direct children*. A sector's confirmations are
  its clusters, not its raw instruments, so four correlated crude/refined
  contracts grouped under two clusters cannot masquerade as four independent
  confirmations.
* Each level aggregates its children with equal weight (sectors use configurable
  weights), so a cluster that happens to hold more tickers does not dominate.
"""

from __future__ import annotations

import statistics
from typing import List

from ..config import RegimeConfig
from .breadth import Breadth, adaptive_min, compute_breadth
from .classification import regime_direction
from .models import GroupResult, InstrumentScore
from .normalization import weighted_available


def robust_center(values: List[float]) -> float:
    """Central tendency that resists a single outlier. Uses the median once a
    group has 4+ members (so one extreme child cannot drag the group across a
    regime boundary), and the plain mean for very small groups."""

    vals = [float(v) for v in values]
    if not vals:
        return 0.0
    if len(vals) >= 4:
        return float(statistics.median(vals))
    return sum(vals) / len(vals)


def _group_regime(avg: float, b: Breadth, cfg: RegimeConfig) -> str:
    """Breadth-gated regime for a cluster or sector."""

    strong_min = adaptive_min(cfg.breadth_strong_min_confirm, b.n)
    bull_min = adaptive_min(cfg.breadth_bull_min_confirm, b.n)

    if (b.pct_bull >= cfg.breadth_strong_pct and b.bull >= strong_min
            and avg > cfg.breadth_strong_avg):
        return "Strong Bullish"
    if (b.pct_bear >= cfg.breadth_strong_pct and b.bear >= strong_min
            and avg < -cfg.breadth_strong_avg):
        return "Strong Bearish"
    if (b.pct_bull >= cfg.breadth_bull_pct and b.bull >= bull_min
            and avg > cfg.breadth_bull_avg):
        return "Bullish"
    if (b.pct_bear >= cfg.breadth_bull_pct and b.bear >= bull_min
            and avg < -cfg.breadth_bull_avg):
        return "Bearish"
    return "Neutral"


def _global_regime(avg: float, b: Breadth, cfg: RegimeConfig) -> str:
    min_sectors = (
        cfg.global_min_sectors if b.n >= 4
        else adaptive_min(cfg.global_min_sectors, b.n)
    )
    strong_cut = cfg.global_abs
    mild_cut = cfg.global_abs * 0.5

    if (b.pct_bull >= cfg.global_breadth and b.bull >= min_sectors
            and avg >= strong_cut):
        return "Strong Bullish"
    if (b.pct_bear >= cfg.global_breadth and b.bear >= min_sectors
            and avg <= -strong_cut):
        return "Strong Bearish"
    if avg >= mild_cut and b.pct_bull > b.pct_bear:
        return "Bullish"
    if avg <= -mild_cut and b.pct_bear > b.pct_bull:
        return "Bearish"
    return "Neutral"


def _blended(score: float, breadth_score: float, cfg: RegimeConfig) -> float:
    return (cfg.cluster_blend_directional * score
            + cfg.cluster_blend_breadth * breadth_score)


def build_cluster(
    name: str, instruments: List[InstrumentScore], cfg: RegimeConfig
) -> GroupResult:
    active = [i for i in instruments if i.eligible]
    directions = [regime_direction(i.regime) for i in active]
    b = compute_breadth(directions)

    score = robust_center([i.score for i in active]) if active else 0.0
    regime = _group_regime(score, b, cfg) if active else "Neutral"
    blended = _blended(score, b.breadth_score, cfg)

    # per-instrument contribution to the (equal-weighted) cluster score
    if active:
        for i in active:
            i.contribution = round(i.score / len(active), 2)

    return GroupResult(
        name=name,
        level="cluster",
        score=round(score, 2),
        blended_score=round(blended, 2),
        regime=regime,
        breadth_score=round(b.breadth_score, 2),
        pct_bull=b.pct_bull,
        pct_bear=b.pct_bear,
        pct_neutral=b.pct_neutral,
        confirming=b.confirming,
        n_children=len(instruments),
        n_active=len(active),
        dominant=b.dominant,
        data_quality_ok=len(active) > 0,
        children=list(instruments),
        child_kind="instrument",
    )


def build_sector(
    name: str, clusters: List[GroupResult], cfg: RegimeConfig
) -> GroupResult:
    active = [c for c in clusters if c.n_active > 0]
    directions = [regime_direction(c.regime) for c in active]
    b = compute_breadth(directions)

    score = robust_center([c.score for c in active]) if active else 0.0
    regime = _group_regime(score, b, cfg) if active else "Neutral"
    blended = _blended(score, b.breadth_score, cfg)

    return GroupResult(
        name=name,
        level="sector",
        score=round(score, 2),
        blended_score=round(blended, 2),
        regime=regime,
        breadth_score=round(b.breadth_score, 2),
        pct_bull=b.pct_bull,
        pct_bear=b.pct_bear,
        pct_neutral=b.pct_neutral,
        confirming=b.confirming,
        n_children=len(clusters),
        n_active=len(active),
        dominant=b.dominant,
        data_quality_ok=len(active) > 0,
        children=list(clusters),
        child_kind="group",
    )


def build_global(
    name: str, sectors: List[GroupResult], cfg: RegimeConfig
) -> GroupResult:
    active = [s for s in sectors if s.n_active > 0]
    directions = [regime_direction(s.regime) for s in active]
    b = compute_breadth(directions)

    score = weighted_available([
        (s.score, cfg.sector_weights.get(s.name, 1.0)) for s in active
    ])
    regime = _global_regime(score, b, cfg) if active else "Neutral"
    blended = _blended(score, b.breadth_score, cfg)

    return GroupResult(
        name=name,
        level="global",
        score=round(score, 2),
        blended_score=round(blended, 2),
        regime=regime,
        breadth_score=round(b.breadth_score, 2),
        pct_bull=b.pct_bull,
        pct_bear=b.pct_bear,
        pct_neutral=b.pct_neutral,
        confirming=b.confirming,
        n_children=len(sectors),
        n_active=len(active),
        dominant=b.dominant,
        data_quality_ok=len(active) > 0,
        children=list(sectors),
        child_kind="group",
    )
