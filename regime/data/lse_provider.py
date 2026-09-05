"""London Strategic Edge provider (primary).

Discovers the commodity universe from the live vault catalog, classifies each
instrument with the taxonomy, and pulls daily + intraday OHLCV candles straight
from the vault. The API key is read from ``LSE_API_KEY`` (never hardcoded); the
``lse`` client falls back to that env var on its own, and we also read it here to
decide availability.
"""

from __future__ import annotations

import os
from typing import List, Optional

from ..config import RegimeConfig, classify_symbol
from ..engine.models import InstrumentData
from .provider import MarketDataProvider, normalize_candles


class LSEProvider(MarketDataProvider):
    name = "lse"

    def __init__(self, api_key: Optional[str] = None, max_instruments: int = 48):
        self._api_key = api_key
        self.max_instruments = max_instruments

    def api_key(self) -> Optional[str]:
        return self._api_key or os.environ.get("LSE_API_KEY")

    def available(self) -> bool:
        return bool(self.api_key())

    def _catalog(self, client) -> List[dict]:
        for category in ("commodities", "commodity"):
            try:
                rows = client.catalog(category)
                if rows:
                    return rows
            except Exception:
                continue
        # last resort: whole catalog, filter by category field
        try:
            rows = client.catalog()
        except Exception:
            return []
        return [
            r for r in rows
            if "commodit" in str(r.get("category", "")).lower()
        ]

    def _descriptors(self, catalog: List[dict]):
        seen = set()
        descriptors = []
        for row in catalog:
            sym = row.get("symbol")
            if not sym or sym in seen:
                continue
            name = row.get("name") or sym
            cls = classify_symbol(sym, name)
            if not cls:
                continue
            seen.add(sym)
            sector, cluster = cls
            descriptors.append((sym, name, sector, cluster, row.get("dataset")))
            if len(descriptors) >= self.max_instruments:
                break
        return descriptors

    def fetch_universe(self, cfg: RegimeConfig) -> List[InstrumentData]:
        key = self.api_key()
        if not key:
            raise RuntimeError("LSE_API_KEY not set")

        from lse import LSE

        client = LSE(api_key=key, timeout=90)
        try:
            catalog = self._catalog(client)
            descriptors = self._descriptors(catalog)

            out: List[InstrumentData] = []
            for sym, name, sector, cluster, dataset in descriptors:
                daily = self._candles(
                    client, sym, cfg.primary_timeframe, cfg.history_bars, dataset
                )
                intraday = None
                if cfg.intraday_enabled:
                    intraday = self._candles(
                        client, sym, cfg.intraday_timeframe,
                        cfg.intraday_bars, dataset,
                    )
                    if intraday is not None and intraday.empty:
                        intraday = None
                out.append(InstrumentData(
                    symbol=sym,
                    name=name,
                    sector=sector,
                    cluster=cluster,
                    daily=daily,
                    intraday=intraday,
                    last_timestamp=self._last_timestamp(daily, intraday),
                ))
            return out
        finally:
            try:
                client.disconnect()
            except Exception:
                pass

    def latest_prices(self, symbols) -> dict:
        key = self.api_key()
        symbols = list(symbols)
        if not key or not symbols:
            return {}
        from lse import LSE

        client = LSE(api_key=key, timeout=30)
        out = {}
        try:
            for sym in symbols:
                try:
                    rows = client.candles(
                        sym, timeframe="1m", limit=1, order="desc")
                    df = normalize_candles(rows)
                    if not df.empty:
                        out[sym] = float(df["close"].iloc[-1])
                except Exception:
                    continue
        finally:
            try:
                client.disconnect()
            except Exception:
                pass
        return out

    @staticmethod
    def _candles(client, symbol, timeframe, limit, dataset):
        try:
            rows = client.candles(
                symbol, timeframe=timeframe, limit=limit,
                order="asc", dataset=dataset,
            )
        except Exception:
            try:
                rows = client.candles(symbol, timeframe=timeframe, limit=limit)
            except Exception:
                rows = []
        return normalize_candles(rows)
