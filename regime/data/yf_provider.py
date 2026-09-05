"""Yahoo Finance provider — real market data, used as the local/dev fallback
when no LSE key is present. Same interface and output shape as the LSE provider.
"""

from __future__ import annotations

from typing import List, Optional

import pandas as pd

from ..config import RegimeConfig, YF_COMMODITY_UNIVERSE
from ..engine.models import InstrumentData
from .provider import MarketDataProvider


def _extract(df, sym: str) -> Optional[pd.DataFrame]:
    if df is None or getattr(df, "empty", True):
        return None
    try:
        if isinstance(df.columns, pd.MultiIndex):
            if sym not in df.columns.get_level_values(0):
                return None
            sub = df[sym].copy()
        else:
            sub = df.copy()
    except Exception:
        return None
    sub.columns = [str(c).lower() for c in sub.columns]
    keep = [c for c in ["open", "high", "low", "close", "volume"]
            if c in sub.columns]
    if "close" not in keep:
        return None
    sub = sub[keep].dropna(how="all")
    return sub


class YahooProvider(MarketDataProvider):
    name = "yfinance"

    def fetch_universe(self, cfg: RegimeConfig) -> List[InstrumentData]:
        import yfinance as yf

        tickers = [u[0] for u in YF_COMMODITY_UNIVERSE]

        daily = yf.download(
            tickers, period="1y", interval="1d", group_by="ticker",
            auto_adjust=True, progress=False, threads=True,
        )
        intraday = None
        if cfg.intraday_enabled:
            try:
                intraday = yf.download(
                    tickers, period="5d", interval=cfg.intraday_timeframe,
                    group_by="ticker", auto_adjust=True, progress=False,
                    threads=True,
                )
            except Exception:
                intraday = None

        out: List[InstrumentData] = []
        for sym, name, sector, cluster in YF_COMMODITY_UNIVERSE:
            d = _extract(daily, sym)
            if d is None:
                d = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
            intr = _extract(intraday, sym) if intraday is not None else None
            out.append(InstrumentData(
                symbol=sym,
                name=name,
                sector=sector,
                cluster=cluster,
                daily=d,
                intraday=intr,
                last_timestamp=self._last_timestamp(d, intr),
            ))
        return out
