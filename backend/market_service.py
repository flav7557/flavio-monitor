from __future__ import annotations

import logging

from .config import MARKETS_FILE, Settings
from .lse_client import LSEGateway
from .market_catalog import load_market_specs, resolve_market_specs
from .models import MarketSpec
from .websocket_manager import UpstreamMarketStream, WebSocketManager


logger = logging.getLogger(__name__)

SUPPORTED_TIMEFRAMES = {"1m", "5m", "15m", "1h", "4h", "1d"}


class MarketService:
    def __init__(self, settings: Settings, manager: WebSocketManager) -> None:
        self.settings = settings
        self.manager = manager
        self.gateway = LSEGateway(settings.lse_api_key) if settings.lse_api_key else None
        self.markets: list[MarketSpec] = load_market_specs(MARKETS_FILE)
        self.stream: UpstreamMarketStream | None = None
        self.catalog_loaded = False
        self.catalog_error: str | None = None

    async def start(self) -> None:
        if not self.gateway:
            self.catalog_error = "LSE_API_KEY is missing"
            return
        try:
            catalog = await self.gateway.catalog()
            self.markets = resolve_market_specs(self.markets, catalog)
            self.catalog_loaded = True
            for market in self.markets:
                if market.error:
                    logger.warning("%s: %s", market.name, market.error)
        except Exception as exc:
            self.catalog_error = str(exc)
            logger.exception("Unable to load London Strategic Edge catalog")
            return

        symbols = list(dict.fromkeys(m.symbol for m in self.markets if m.symbol))
        self.stream = UpstreamMarketStream(
            self.gateway.stream,
            symbols,
            self.manager,
            self.settings.stream_backoff_max_seconds,
        )
        await self.stream.start()

    async def stop(self) -> None:
        if self.stream:
            await self.stream.stop()

    def public_markets(self) -> list[dict]:
        return [market.public() for market in self.markets]

    async def candles(self, symbol: str, timeframe: str, limit: int) -> list[dict]:
        if not self.gateway:
            raise RuntimeError("LSE_API_KEY is missing")
        timeframe = timeframe.lower()
        if timeframe not in SUPPORTED_TIMEFRAMES:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        market = next((m for m in self.markets if m.symbol == symbol), None)
        if not market:
            raise LookupError(f"Symbol unavailable: {symbol}")
        return await self.gateway.candles(
            symbol,
            timeframe=timeframe,
            limit=max(1, min(limit, 500)),
            dataset=market.dataset,
        )

    def health(self) -> dict:
        return {
            "status": "ok" if self.settings.lse_api_key else "configuration_required",
            "lse": {
                "keyPresent": bool(self.settings.lse_api_key),
                "catalogLoaded": self.catalog_loaded,
                "streamConnected": bool(self.stream and self.stream.connected),
                "error": self.catalog_error or (self.stream.last_error if self.stream else None),
            },
            "resolvedMarkets": sum(1 for market in self.markets if market.symbol),
            "connectedClients": self.manager.client_count,
        }
