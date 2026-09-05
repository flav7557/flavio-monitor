from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from lse import LSE


def _value(source: Any, name: str) -> Any:
    if isinstance(source, dict):
        return source.get(name)
    return getattr(source, name, None)


def serialize_tick(tick: Any) -> dict[str, Any] | None:
    symbol = _value(tick, "symbol")
    price = _value(tick, "price")
    if not symbol or price is None:
        return None

    timestamp = _value(tick, "timestamp") or _value(tick, "ts")
    if isinstance(timestamp, datetime):
        timestamp = timestamp.astimezone(timezone.utc).isoformat()
    elif timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()

    return {
        "type": "tick",
        "symbol": str(symbol),
        "price": float(price),
        "bid": _optional_float(_value(tick, "bid")),
        "ask": _optional_float(_value(tick, "ask")),
        "volume": _optional_float(_value(tick, "volume")),
        "timestamp": str(timestamp),
    }


def normalize_candles(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candles: list[dict[str, Any]] = []
    for row in rows:
        timestamp = row.get("timestamp") or row.get("ts") or row.get("time")
        try:
            if isinstance(timestamp, (int, float)):
                epoch = int(timestamp)
            else:
                parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
                epoch = int(parsed.timestamp())
            candle = {
                "time": epoch,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume") or 0),
            }
        except (KeyError, TypeError, ValueError):
            continue
        candles.append(candle)
    candles.sort(key=lambda item: item["time"])
    return candles


def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


class LSEGateway:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def catalog(self) -> list[dict[str, Any]]:
        def fetch() -> list[dict[str, Any]]:
            client = LSE(api_key=self.api_key, timeout=60)
            try:
                return client.catalog()
            finally:
                client.disconnect()

        return await asyncio.to_thread(fetch)

    async def candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        dataset: str | None = None,
    ) -> list[dict[str, Any]]:
        def fetch() -> list[dict[str, Any]]:
            client = LSE(api_key=self.api_key, timeout=60)
            try:
                rows = client.candles(
                    symbol,
                    timeframe=timeframe,
                    limit=limit,
                    order="desc",
                    dataset=dataset,
                )
                return normalize_candles(rows)
            finally:
                client.disconnect()

        return await asyncio.to_thread(fetch)

    async def stream(self, symbols: list[str]) -> AsyncIterator[dict[str, Any]]:
        client = LSE(api_key=self.api_key, timeout=60)
        try:
            async for tick in client.stream_async(symbols, reconnect=False):
                payload = serialize_tick(tick)
                if payload:
                    yield payload
        finally:
            await client.disconnect_async()
