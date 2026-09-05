"""Deterministic tests for the regime engine (no network, no Streamlit)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from regime.config import DEFAULT_CONFIG, classify_symbol
from regime.engine.aggregation import build_cluster, build_global, build_sector
from regime.engine.breadth import adaptive_min, compute_breadth
from regime.engine.classification import classify_score
from regime.engine.confidence import compute_confidence
from regime.engine.instrument_scorer import score_instrument
from regime.engine.models import InstrumentData, InstrumentScore
from regime.engine.persistence import RegimeStore
from regime.engine.pipeline import run_pipeline

CFG = DEFAULT_CONFIG


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def make_daily(drift, n=220, start=100.0, vol=0.004, seed=0):
    rng = np.random.default_rng(seed)
    rets = drift + rng.normal(0, vol, n)
    close = start * np.cumprod(1 + rets)
    idx = pd.date_range(end=pd.Timestamp("2026-09-01"), periods=n, freq="B")
    high = close * (1 + np.abs(rng.normal(0, vol / 2, n)))
    low = close * (1 - np.abs(rng.normal(0, vol / 2, n)))
    open_ = np.concatenate([[close[0]], close[:-1]])
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": 1000.0},
        index=idx,
    )


def make_instrument(drift, name="X", sector="Energy", cluster="Crude", seed=0,
                    vol=0.004):
    d = make_daily(drift, seed=seed, vol=vol)
    return InstrumentData(
        symbol=name, name=name, sector=sector, cluster=cluster,
        daily=d, intraday=None, last_timestamp=d.index[-1],
    )


def iscore(name, score, sector="Energy", cluster="Crude", eligible=True, stale=False):
    return InstrumentScore(
        symbol=name, name=name, sector=sector, cluster=cluster,
        score=score, regime=classify_score(score, CFG),
        eligible=eligible, stale=stale,
        momentum_horizon_scores={"5": score, "20": score, "60": score},
    )


NOW = pd.Timestamp("2026-09-01")


# --------------------------------------------------------------------------- #
# instrument scoring
# --------------------------------------------------------------------------- #
def test_uptrend_is_bullish():
    s = score_instrument(make_instrument(0.006, seed=1), CFG, now=NOW)
    assert s.eligible
    assert s.score >= 25
    assert s.regime in ("Bullish", "Strong Bullish")


def test_downtrend_is_bearish():
    s = score_instrument(make_instrument(-0.006, seed=2), CFG, now=NOW)
    assert s.eligible
    assert s.score <= -25
    assert s.regime in ("Bearish", "Strong Bearish")


def test_flat_is_neutral():
    s = score_instrument(make_instrument(0.0, vol=0.003, seed=3), CFG, now=NOW)
    assert s.eligible
    assert -20 < s.score < 20
    assert s.regime == "Neutral"


def test_score_bounds():
    for drift, seed in [(0.02, 4), (-0.02, 5), (0.0, 6)]:
        s = score_instrument(make_instrument(drift, seed=seed), CFG, now=NOW)
        assert -100.0 <= s.score <= 100.0


def test_insufficient_history_ineligible():
    d = make_daily(0.006).iloc[-30:]
    data = InstrumentData("Y", "Y", "Energy", "Crude", d, None, d.index[-1])
    s = score_instrument(data, CFG, now=NOW)
    assert not s.eligible
    assert "insufficient history" in s.reasons[0]


def test_missing_data_ineligible_and_not_directional():
    empty = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    data = InstrumentData("Z", "Z", "Energy", "Crude", empty, None, None)
    s = score_instrument(data, CFG, now=NOW)
    assert not s.eligible
    assert s.score == 0.0
    # excluded from breadth entirely
    cluster = build_cluster("Crude", [s, iscore("A", -60)], CFG)
    assert cluster.n_active == 1
    assert cluster.dominant == "bear"


def test_stale_quote_flagged():
    data = make_instrument(0.006, seed=7)
    late = data.daily.index[-1]
    s = score_instrument(data, CFG, now=late + pd.Timedelta(days=10))
    assert s.stale
    assert s.eligible  # stale is a warning, not exclusion


# --------------------------------------------------------------------------- #
# classification / breadth
# --------------------------------------------------------------------------- #
def test_classify_thresholds():
    assert classify_score(50, CFG) == "Strong Bullish"
    assert classify_score(25, CFG) == "Bullish"
    assert classify_score(0, CFG) == "Neutral"
    assert classify_score(-25, CFG) == "Bearish"
    assert classify_score(-50, CFG) == "Strong Bearish"


def test_breadth_counts():
    b = compute_breadth(["bull", "bull", "bear", "neutral"])
    assert b.bull == 2 and b.bear == 1 and b.neutral == 1
    assert b.dominant == "bull" and b.confirming == 2


def test_adaptive_min_small_universe():
    assert adaptive_min(4, 3) == 2      # 4-of-4 impossible on 3 -> 2
    assert adaptive_min(4, 4) == 4
    assert adaptive_min(3, 1) == 1


# --------------------------------------------------------------------------- #
# aggregation invariants
# --------------------------------------------------------------------------- #
def test_single_outlier_cannot_flip_sector():
    # three bearish clusters, one wildly bullish single-instrument cluster
    crude = build_cluster("Crude", [iscore("WTI", -70), iscore("Brent", -68)], CFG)
    refined = build_cluster("Refined", [iscore("Gasoline", -55)], CFG)
    gas = build_cluster("Gas", [iscore("NatGas", -45)], CFG)
    outlier = build_cluster("Outlier", [iscore("Spike", +100)], CFG)
    sector = build_sector("Energy", [crude, refined, gas, outlier], CFG)
    assert sector.regime in ("Bearish", "Strong Bearish")
    assert sector.dominant == "bear"


def test_correlated_instruments_do_not_dominate_breadth():
    # 4 correlated bullish crude names in ONE cluster vs 2 bearish clusters.
    # Raw instrument breadth would be 4 bull / 2 bear (bullish); cluster-level
    # breadth is 1 bull / 2 bear -> sector must NOT be bullish.
    crude = build_cluster(
        "Crude",
        [iscore("WTI", 55), iscore("Brent", 57), iscore("Gasoil", 52),
         iscore("Dubai", 54)],
        CFG,
    )
    metals = build_cluster("Copper", [iscore("Copper", -45)], CFG)
    ags = build_cluster("Grains", [iscore("Corn", -50)], CFG)
    sector = build_sector("Mixed", [crude, metals, ags], CFG)
    assert sector.regime not in ("Bullish", "Strong Bullish")


def test_global_not_strong_bear_when_only_energy_collapses():
    energy = build_sector(
        "Energy",
        [build_cluster("Crude", [iscore("WTI", -80), iscore("Brent", -78)], CFG)],
        CFG,
    )
    metals = build_sector(
        "Industrial Metals",
        [build_cluster("Copper", [iscore("Copper", 5)], CFG)], CFG,
    )
    precious = build_sector(
        "Precious Metals",
        [build_cluster("Gold", [iscore("Gold", 40)], CFG)], CFG,
    )
    ags = build_sector(
        "Agriculture",
        [build_cluster("Grains", [iscore("Corn", -3)], CFG)], CFG,
    )
    g = build_global("Commodities", [energy, metals, precious, ags], CFG)
    assert g.regime != "Strong Bearish"


def test_equal_cluster_weighting():
    # A cluster with many tickers must not outweigh a single-ticker cluster.
    big = build_cluster("Big", [iscore(f"b{i}", 60) for i in range(6)], CFG)
    small = build_cluster("Small", [iscore("s", -60)], CFG)
    sector = build_sector("S", [big, small], CFG)
    # equal cluster weighting -> average of +~60 and -60 ≈ 0
    assert abs(sector.score) < 15


# --------------------------------------------------------------------------- #
# confidence
# --------------------------------------------------------------------------- #
def test_confidence_range_and_ordering():
    aligned = build_sector(
        "A",
        [build_cluster("c1", [iscore("a", -60)], CFG),
         build_cluster("c2", [iscore("b", -62)], CFG),
         build_cluster("c3", [iscore("c", -58)], CFG)],
        CFG,
    )
    mixed = build_sector(
        "B",
        [build_cluster("c1", [iscore("a", -60)], CFG),
         build_cluster("c2", [iscore("b", 55)], CFG),
         build_cluster("c3", [iscore("c", 5)], CFG)],
        CFG,
    )
    ca = compute_confidence(aligned, CFG, 1.0)
    cm = compute_confidence(mixed, CFG, 1.0)
    assert 0 <= cm <= 100 and 0 <= ca <= 100
    assert ca > cm


# --------------------------------------------------------------------------- #
# persistence
# --------------------------------------------------------------------------- #
def test_persistence_requires_consecutive_switches(tmp_path):
    store = RegimeStore(str(tmp_path / "s.json"), CFG)
    r = store.update("global", "Bullish", 30, "t0")
    assert r["official"] == "Bullish"          # first observation seeds official
    # now push Bearish; must NOT switch until persistence_length (3) in a row
    r = store.update("global", "Bearish", -30, "t1")
    assert r["official"] == "Bullish" and r["change_status"] == "pending change"
    r = store.update("global", "Bearish", -32, "t2")
    assert r["official"] == "Bullish"
    r = store.update("global", "Bearish", -34, "t3")
    assert r["official"] == "Bearish" and r["change_status"] == "newly changed"


def test_persistence_trend_labels(tmp_path):
    store = RegimeStore(str(tmp_path / "s.json"), CFG)
    store.update("g", "Bearish", -30, "t0")
    r = store.update("g", "Bearish", -45, "t1")
    assert r["change_status"] == "strengthening"
    r = store.update("g", "Bearish", -20, "t2")
    assert r["change_status"] == "weakening"


# --------------------------------------------------------------------------- #
# taxonomy + end-to-end
# --------------------------------------------------------------------------- #
def test_classify_symbol():
    assert classify_symbol("BRENT/USD", "Brent Crude Oil") == ("Energy", "Crude")
    assert classify_symbol("XAU/USD", "Spot Gold") == ("Precious Metals", "Gold")
    assert classify_symbol("HG", "Copper") == ("Industrial Metals", "Copper")
    assert classify_symbol("ZZZ/USD", "Nonsense") is None


def test_pipeline_end_to_end():
    universe = [
        make_instrument(-0.006, "WTI", "Energy", "Crude", seed=10),
        make_instrument(-0.006, "Brent", "Energy", "Crude", seed=11),
        make_instrument(-0.005, "Gasoline", "Energy", "Refined Products", seed=12),
        make_instrument(-0.005, "NatGas", "Energy", "Natural Gas", seed=13),
        make_instrument(0.006, "Gold", "Precious Metals", "Gold", seed=14),
        make_instrument(0.005, "Silver", "Precious Metals", "Silver", seed=15),
        make_instrument(-0.001, "Copper", "Industrial Metals", "Copper", seed=16),
        make_instrument(0.0, "Corn", "Agriculture", "Grains", seed=17),
    ]
    result = run_pipeline(universe, CFG, now=NOW)
    assert result.n_instruments == 8
    assert result.n_eligible == 8
    sectors = {s.name: s for s in result.global_regime.children}
    assert sectors["Energy"].dominant == "bear"
    assert sectors["Precious Metals"].dominant == "bull"
    # global should not be strongly one-sided given the split
    assert result.global_regime.regime != "Strong Bullish"
    assert 0 <= result.global_regime.confidence <= 100
    assert result.global_regime.explanation
