"""Price-based indicators. Pure functions over pandas Series/DataFrames.

Every function is defensive: when there is not enough history it returns
``None`` rather than raising or fabricating a value. Missing data must never be
turned into a directional signal downstream.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


def _clean_close(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").dropna()


def sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n, min_periods=n).mean()


def last_sma(series: pd.Series, n: int) -> Optional[float]:
    s = _clean_close(series)
    if len(s) < n:
        return None
    return float(s.rolling(n, min_periods=n).mean().iloc[-1])


def slope_per_bar(series: pd.Series, n: int, lookback: int) -> Optional[float]:
    """Average per-bar change of the ``n``-period SMA over the last
    ``lookback`` bars (OLS slope)."""

    s = _clean_close(series)
    ma = s.rolling(n, min_periods=n).mean().dropna()
    if len(ma) < lookback + 1:
        return None
    y = ma.iloc[-(lookback + 1):].to_numpy(dtype=float)
    x = np.arange(len(y), dtype=float)
    slope = float(np.polyfit(x, y, 1)[0])
    return slope


def true_range(df: pd.DataFrame) -> pd.Series:
    high = pd.to_numeric(df["high"], errors="coerce")
    low = pd.to_numeric(df["low"], errors="coerce")
    close = pd.to_numeric(df["close"], errors="coerce")
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def last_atr(df: pd.DataFrame, n: int) -> Optional[float]:
    tr = true_range(df).dropna()
    if len(tr) < n:
        return None
    atr = tr.rolling(n, min_periods=n).mean().iloc[-1]
    if not np.isfinite(atr) or atr <= 0:
        return None
    return float(atr)


def period_return(series: pd.Series, h: int) -> Optional[float]:
    s = _clean_close(series)
    if len(s) < h + 1:
        return None
    prev = s.iloc[-(h + 1)]
    if prev == 0:
        return None
    return float(s.iloc[-1] / prev - 1.0)


def rolling_return_zscore(
    series: pd.Series, h: int, window: int
) -> Optional[float]:
    """Z-score of the latest ``h``-period return versus its own rolling
    distribution (volatility-adjusted momentum)."""

    s = _clean_close(series)
    if len(s) < h + window:
        return None
    rets = s.pct_change(h).dropna()
    if len(rets) < window:
        return None
    ref = rets.iloc[-window:]
    mu = float(ref.mean())
    sigma = float(ref.std(ddof=0))
    if not np.isfinite(sigma) or sigma == 0:
        return None
    return float((rets.iloc[-1] - mu) / sigma)


def donchian_state(df: pd.DataFrame, n: int) -> Optional[dict]:
    """Breakout state versus the prior ``n``-bar Donchian channel.

    Returns a dict with the last close, channel bounds, ``position`` in
    ``[-1, 1]`` (relative to channel mid) and ``breakout`` in ``{-1, 0, 1}``.
    """

    high = pd.to_numeric(df["high"], errors="coerce")
    low = pd.to_numeric(df["low"], errors="coerce")
    close = pd.to_numeric(df["close"], errors="coerce").dropna()
    if len(close) < n + 1:
        return None

    prior_high = high.shift(1).rolling(n, min_periods=n).max().iloc[-1]
    prior_low = low.shift(1).rolling(n, min_periods=n).min().iloc[-1]
    last = float(close.iloc[-1])
    if not (np.isfinite(prior_high) and np.isfinite(prior_low)):
        return None

    rng = prior_high - prior_low
    mid = (prior_high + prior_low) / 2.0
    position = 0.0 if rng <= 0 else float((last - mid) / (rng / 2.0))
    position = max(-1.0, min(1.0, position))

    if last > prior_high:
        breakout = 1
    elif last < prior_low:
        breakout = -1
    else:
        breakout = 0

    return {
        "close": last,
        "upper": float(prior_high),
        "lower": float(prior_low),
        "position": position,
        "breakout": breakout,
    }


def session_vwap(intraday: pd.DataFrame) -> Optional[float]:
    """VWAP over the most recent session (calendar day) of intraday bars.
    Falls back to a typical-price mean when volume is absent."""

    if intraday is None or intraday.empty:
        return None
    df = intraday.copy()
    idx = df.index
    if not isinstance(idx, pd.DatetimeIndex):
        return None
    last_day = idx[-1].date()
    day = df[idx.date == last_day]
    if day.empty:
        return None
    typical = (
        pd.to_numeric(day["high"], errors="coerce")
        + pd.to_numeric(day["low"], errors="coerce")
        + pd.to_numeric(day["close"], errors="coerce")
    ) / 3.0
    if "volume" in day and pd.to_numeric(day["volume"], errors="coerce").sum() > 0:
        vol = pd.to_numeric(day["volume"], errors="coerce").fillna(0.0)
        denom = vol.sum()
        if denom > 0:
            return float((typical * vol).sum() / denom)
    return float(typical.mean())


def session_open_return(intraday: pd.DataFrame) -> Optional[float]:
    if intraday is None or intraday.empty:
        return None
    idx = intraday.index
    if not isinstance(idx, pd.DatetimeIndex):
        return None
    last_day = idx[-1].date()
    day = intraday[idx.date == last_day]
    if day.empty:
        return None
    open_px = pd.to_numeric(day["open"], errors="coerce").dropna()
    close_px = pd.to_numeric(day["close"], errors="coerce").dropna()
    if open_px.empty or close_px.empty or open_px.iloc[0] == 0:
        return None
    return float(close_px.iloc[-1] / open_px.iloc[0] - 1.0)
