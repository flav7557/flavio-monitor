"""Per-instrument directional scoring.

Combines four volatility-aware components into a single score in ``[-100, 100]``:

* Trend (35%)     — price vs SMA20, SMA20 vs SMA50, SMA20 slope (ATR-normalised)
* Momentum (30%)  — multi-horizon returns as rolling volatility Z-scores
* Intraday (20%)  — short/medium intraday impulse, session-open drift, vs VWAP
* Breakout (15%)  — Donchian channel position / 20-bar breakout

Components that cannot be computed from the available data are *dropped* and the
remaining weights renormalised — missing data is never scored as neutral.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd

from ..config import RegimeConfig
from . import indicators as ind
from .classification import classify_score
from .models import InstrumentData, InstrumentScore
from .normalization import mean_available, tanh_100, weighted_available


def _volatility_unit(close: pd.Series, daily: pd.DataFrame, cfg: RegimeConfig):
    """A price-scale unit for ATR-style normalisation: ATR if available, else a
    return-volatility proxy. Returns ``None`` when neither can be formed."""

    atr = ind.last_atr(daily, cfg.atr_period)
    if atr is not None:
        return atr
    rets = pd.to_numeric(close, errors="coerce").pct_change().dropna()
    if len(rets) < 10:
        return None
    sigma = float(rets.tail(cfg.sma_slow).std(ddof=0))
    price = float(close.dropna().iloc[-1])
    if not math.isfinite(sigma) or sigma <= 0 or price <= 0:
        return None
    return price * sigma


def compute_trend(daily: pd.DataFrame, cfg: RegimeConfig) -> Optional[float]:
    close = pd.to_numeric(daily["close"], errors="coerce").dropna()
    if close.empty:
        return None
    unit = _volatility_unit(close, daily, cfg)
    if unit is None or unit <= 0:
        return None

    price = float(close.iloc[-1])
    sma_f = ind.last_sma(close, cfg.sma_fast)
    sma_s = ind.last_sma(close, cfg.sma_slow)
    slope = ind.slope_per_bar(close, cfg.sma_fast, cfg.slope_lookback)

    subs = []
    if sma_f is not None:
        subs.append(tanh_100((price - sma_f) / unit, scale=1.5))
    if sma_f is not None and sma_s is not None:
        subs.append(tanh_100((sma_f - sma_s) / unit, scale=1.5))
    if slope is not None:
        subs.append(tanh_100((slope / unit) * cfg.slope_scale, scale=1.0))

    if not subs:
        return None
    return mean_available(subs)


def compute_momentum(daily: pd.DataFrame, cfg: RegimeConfig):
    """Returns ``(score, {horizon: component})`` or ``(None, {})``."""

    close = pd.to_numeric(daily["close"], errors="coerce").dropna()
    horizon_scores = {}
    for h in cfg.momentum_horizons:
        z = ind.rolling_return_zscore(close, h, cfg.zscore_window)
        if z is None:
            continue
        horizon_scores[str(h)] = tanh_100(z, scale=cfg.momentum_z_scale)
    if not horizon_scores:
        return None, {}
    return mean_available(list(horizon_scores.values())), horizon_scores


def compute_intraday(
    intraday: Optional[pd.DataFrame], daily: pd.DataFrame, cfg: RegimeConfig
) -> Optional[float]:
    if intraday is None or intraday.empty:
        return None
    close = pd.to_numeric(intraday["close"], errors="coerce").dropna()
    if len(close) < cfg.intraday_medium_bars + 5:
        return None

    subs = []

    z_short = ind.rolling_return_zscore(
        close, cfg.intraday_short_bars, cfg.intraday_vol_window
    )
    if z_short is not None:
        subs.append(tanh_100(z_short, scale=cfg.intraday_z_scale))

    z_med = ind.rolling_return_zscore(
        close, cfg.intraday_medium_bars, cfg.intraday_vol_window
    )
    if z_med is not None:
        subs.append(tanh_100(z_med, scale=cfg.intraday_z_scale))

    # session-open drift, normalised by daily return volatility
    open_ret = ind.session_open_return(intraday)
    daily_close = pd.to_numeric(daily["close"], errors="coerce").pct_change()
    daily_close = daily_close.dropna()
    if open_ret is not None and len(daily_close) >= 20:
        unit = float(daily_close.tail(cfg.sma_slow).std(ddof=0))
        if math.isfinite(unit) and unit > 0:
            subs.append(tanh_100(open_ret / unit, scale=1.5))

    # price vs VWAP, normalised by per-bar intraday return volatility
    vwap = ind.session_vwap(intraday)
    perbar = close.pct_change().dropna()
    if vwap is not None and vwap > 0 and len(perbar) >= 10:
        unit = float(perbar.tail(cfg.intraday_vol_window).std(ddof=0))
        if math.isfinite(unit) and unit > 0:
            subs.append(tanh_100((close.iloc[-1] - vwap) / vwap / unit, scale=2.0))

    if not subs:
        return None
    return mean_available(subs)


def compute_breakout(daily: pd.DataFrame, cfg: RegimeConfig) -> Optional[float]:
    state = ind.donchian_state(daily, cfg.donchian_period)
    if state is None:
        return None
    if state["breakout"] == 1:
        return 100.0
    if state["breakout"] == -1:
        return -100.0
    return float(state["position"] * cfg.breakout_mid_cap)


def _age_days(last_ts, now) -> Optional[float]:
    if last_ts is None:
        return None
    try:
        last_ts = pd.Timestamp(last_ts)
        now = pd.Timestamp(now)
        if last_ts.tzinfo is not None:
            last_ts = last_ts.tz_convert("UTC").tz_localize(None)
        if now.tzinfo is not None:
            now = now.tz_convert("UTC").tz_localize(None)
        return (now - last_ts).total_seconds() / 86400.0
    except Exception:
        return None


def score_instrument(
    data: InstrumentData, cfg: RegimeConfig, now: Optional[pd.Timestamp] = None
) -> InstrumentScore:
    now = now or pd.Timestamp.utcnow()
    daily = data.daily
    reasons: list[str] = []

    result = InstrumentScore(
        symbol=data.symbol,
        name=data.name,
        sector=data.sector,
        cluster=data.cluster,
        score=0.0,
        regime="Neutral",
        component_weights=cfg.component_weights(),
        last_timestamp=data.last_timestamp,
    )

    if daily is None or daily.empty or "close" not in daily:
        result.eligible = False
        result.reasons = ["no price data"]
        return result

    close = pd.to_numeric(daily["close"], errors="coerce").dropna()
    if len(close) < cfg.min_history_bars:
        result.eligible = False
        result.reasons = [f"insufficient history ({len(close)} bars)"]
        result.price = float(close.iloc[-1]) if len(close) else None
        result.sparkline = [float(x) for x in close.tail(30)]
        return result

    trend = compute_trend(daily, cfg)
    momentum, horizon_scores = compute_momentum(daily, cfg)
    intraday = (
        compute_intraday(data.intraday, daily, cfg)
        if cfg.intraday_enabled else None
    )
    breakout = compute_breakout(daily, cfg)

    components = {
        "trend": trend,
        "momentum": momentum,
        "intraday": intraday,
        "breakout": breakout,
    }

    # Require at least one structural component (trend or momentum): without it
    # a "score" would be noise, so we mark the instrument ineligible instead of
    # emitting a spurious signal.
    if trend is None and momentum is None:
        result.eligible = False
        result.reasons = ["trend/momentum unavailable"]
        result.components = components
        result.price = float(close.iloc[-1])
        result.sparkline = [float(x) for x in close.tail(30)]
        return result

    weights = cfg.component_weights()
    score = weighted_available([
        (trend, weights["trend"]),
        (momentum, weights["momentum"]),
        (intraday, weights["intraday"]),
        (breakout, weights["breakout"]),
    ])

    price = float(close.iloc[-1])
    daily_change = ind.period_return(close, 1)

    age = _age_days(data.last_timestamp, now)
    stale = age is not None and age > cfg.max_stale_days
    if stale:
        reasons.append(f"stale quote ({age:.1f}d old)")
    if intraday is None and cfg.intraday_enabled:
        reasons.append("no intraday data")

    result.score = round(float(score), 2)
    result.regime = classify_score(result.score, cfg)
    result.price = price
    result.daily_change_pct = None if daily_change is None else daily_change * 100.0
    result.components = {
        k: (None if v is None else round(float(v), 2))
        for k, v in components.items()
    }
    result.momentum_horizon_scores = {
        k: round(float(v), 2) for k, v in horizon_scores.items()
    }
    result.eligible = True
    result.stale = stale
    result.reasons = reasons
    result.sparkline = [float(x) for x in close.tail(30)]
    return result
