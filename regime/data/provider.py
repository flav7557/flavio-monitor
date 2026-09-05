"""Data-provider interface + a defensive candle normaliser.

Market-data acquisition is deliberately isolated from the regime logic: a
provider's only job is to return a list of :class:`InstrumentData` with clean
OHLCV frames. The engine never talks to an API directly.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd

from ..config import RegimeConfig
from ..engine.models import InstrumentData


_TIME_KEYS = [
    "time", "timestamp", "date", "datetime", "t", "bar_time", "start", "ts",
]
_OHLC = {
    "open": ["open", "o"],
    "high": ["high", "h"],
    "low": ["low", "l"],
    "close": ["close", "c", "last", "price"],
    "volume": ["volume", "v", "vol"],
}


def _pick(cols, candidates) -> Optional[str]:
    lower = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand in lower:
            return lower[cand]
    return None


def _to_datetime_index(values: pd.Series) -> pd.DatetimeIndex:
    if pd.api.types.is_numeric_dtype(values):
        v = pd.to_numeric(values, errors="coerce")
        med = float(np.nanmedian(v.to_numpy(dtype="float64"))) if len(v) else 0.0
        if med > 1e17:
            unit = "ns"
        elif med > 1e14:
            unit = "us"
        elif med > 1e11:
            unit = "ms"
        else:
            unit = "s"
        return pd.to_datetime(v, unit=unit, utc=True, errors="coerce")
    return pd.to_datetime(values, utc=True, errors="coerce")


def normalize_candles(rows: List[dict]) -> pd.DataFrame:
    """Turn a provider's list-of-dict candles into a tz-aware OHLCV frame.

    Unknown/short shapes degrade gracefully to an empty frame rather than
    raising, so one bad symbol never breaks the run.
    """

    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    df = pd.DataFrame(rows)
    cols = list(df.columns)

    out = pd.DataFrame()
    for target, cands in _OHLC.items():
        src = _pick(cols, cands)
        if src is not None:
            out[target] = pd.to_numeric(df[src], errors="coerce")

    if "close" not in out:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    # fill OHL from close if a provider only returns close
    for c in ("open", "high", "low"):
        if c not in out:
            out[c] = out["close"]
    if "volume" not in out:
        out["volume"] = np.nan

    time_col = _pick(cols, _TIME_KEYS)
    if time_col is not None:
        idx = _to_datetime_index(df[time_col])
        out.index = idx
        out = out[~out.index.isna()]
    out = out.sort_index()
    out = out[["open", "high", "low", "close", "volume"]]
    out = out.dropna(subset=["close"])
    return out


class MarketDataProvider:
    """Interface every provider implements."""

    name = "base"

    def fetch_universe(self, cfg: RegimeConfig) -> List[InstrumentData]:
        raise NotImplementedError

    def latest_prices(self, symbols) -> dict:
        """Best-effort latest price per symbol for the live terminal. Kept
        deliberately light (called every ~30s). Returns ``{symbol: price}``;
        missing symbols simply fall back to the last regime price upstream."""
        return {}

    @staticmethod
    def _last_timestamp(daily: pd.DataFrame,
                        intraday: Optional[pd.DataFrame]) -> Optional[pd.Timestamp]:
        for frame in (intraday, daily):
            if frame is not None and not frame.empty and isinstance(
                frame.index, pd.DatetimeIndex
            ):
                return frame.index[-1]
        return None
