"""End-to-end regime pipeline: instruments -> scores -> clusters -> sectors ->
global, then persistence, confidence and explanations. Pure and deterministic:
give it the same data (and the same store state) and it returns the same result.
"""

from __future__ import annotations

from typing import List, Optional

import pandas as pd

from ..config import COMMODITY_TAXONOMY, RegimeConfig
from .aggregation import build_cluster, build_global, build_sector
from .confidence import compute_confidence
from .explain import explain_global, explain_sector
from .instrument_scorer import score_instrument
from .models import GroupResult, InstrumentData, RegimeResult
from .persistence import RegimeStore


def run_pipeline(
    instruments: List[InstrumentData],
    cfg: RegimeConfig,
    now: Optional[pd.Timestamp] = None,
    store: Optional[RegimeStore] = None,
) -> RegimeResult:
    now = now or pd.Timestamp.utcnow()

    scores = [score_instrument(d, cfg, now=now) for d in instruments]

    # group by sector -> cluster (deterministic order)
    by_sector: dict = {}
    for s in scores:
        by_sector.setdefault(s.sector, {}).setdefault(s.cluster, []).append(s)

    sector_order = (
        [s for s in cfg.sector_weights if s in by_sector]
        + [s for s in by_sector if s not in cfg.sector_weights]
    )

    sectors: List[GroupResult] = []
    for sname in sector_order:
        clusters_map = by_sector[sname]
        tax = COMMODITY_TAXONOMY.get(sname, {})
        corder = (
            [c for c in tax if c in clusters_map]
            + [c for c in clusters_map if c not in tax]
        )
        clusters = [build_cluster(c, clusters_map[c], cfg) for c in corder]
        sectors.append(build_sector(sname, clusters, cfg))

    g = build_global(cfg.asset_class, sectors, cfg)

    # traceable per-instrument contribution to its sector score
    for sector in sectors:
        active_clusters = [c for c in sector.children
                           if isinstance(c, GroupResult) and c.n_active > 0]
        n_c = len(active_clusters)
        for cl in active_clusters:
            active_inst = [i for i in cl.children if i.eligible]
            n_i = len(active_inst)
            for i in active_inst:
                i.contribution = (
                    round(i.score / (n_c * n_i), 2) if n_c and n_i else None
                )

    # persistence + confidence + explanations
    ts = pd.Timestamp(now).isoformat()

    def finalise(group: GroupResult, key: Optional[str]) -> None:
        pf = 1.0
        if store is not None and key is not None:
            res = store.update(key, group.regime, group.score, ts)
            group.regime = res["official"]
            group.change_status = res["change_status"]
            pf = res["persistence_frac"]
        group.confidence = compute_confidence(group, cfg, pf)

    finalise(g, "global" if store else None)
    for sector in sectors:
        finalise(sector, f"sector:{sector.name}" if store else None)
        for cl in sector.children:
            if isinstance(cl, GroupResult):
                cl.confidence = compute_confidence(cl, cfg, 1.0)

    g.explanation = explain_global(g)
    for sector in sectors:
        sector.explanation = explain_sector(sector)

    if store is not None:
        store.save()

    # warnings / data quality
    n_inst = len(scores)
    n_elig = sum(1 for s in scores if s.eligible)
    warnings: List[str] = []
    if n_inst == 0:
        warnings.append("No instruments available from the data provider.")
    elif n_elig / n_inst < cfg.min_eligible_fraction:
        warnings.append(
            f"Only {n_elig}/{n_inst} instruments have sufficient, fresh data — "
            "regime is low-confidence."
        )
    stale = sum(1 for s in scores if s.eligible and s.stale)
    if stale:
        warnings.append(
            f"{stale} instrument(s) have stale quotes (market closed or feed "
            "delayed)."
        )

    return RegimeResult(
        asset_class=cfg.asset_class,
        timestamp=pd.Timestamp(now),
        provider=cfg.provider,
        global_regime=g,
        warnings=warnings,
        n_instruments=n_inst,
        n_eligible=n_elig,
    )
