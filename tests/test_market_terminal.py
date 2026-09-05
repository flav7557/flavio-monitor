from __future__ import annotations

import unittest

from backend.lse_client import normalize_candles, serialize_tick
from backend.market_catalog import resolve_market_specs
from backend.models import MarketSpec


class CatalogResolutionTests(unittest.TestCase):
    def test_strict_market_is_not_replaced_by_a_similar_instrument(self):
        spec = MarketSpec(
            id="asx5",
            name="ASX 5",
            symbol=None,
            categories=["Indices"],
            search_terms=["ASX 5"],
            position="bottom-left",
            strict=True,
        )
        catalog = [
            {
                "symbol": "ASX50",
                "name": "ASX 50 Index",
                "category": "Indices",
                "dataset": "indices",
            }
        ]

        resolved = resolve_market_specs([spec], catalog)[0]

        self.assertIsNone(resolved.symbol)
        self.assertIn("No exact", resolved.error or "")

    def test_index_resolution_stays_inside_the_requested_category(self):
        spec = MarketSpec(
            id="sp500",
            name="S&P 500",
            symbol=None,
            categories=["Indices"],
            search_terms=["S&P 500", "SPX"],
            position="top-right",
        )
        catalog = [
            {"symbol": "SPX", "name": "Company SPX", "category": "Stocks"},
            {
                "symbol": "SPX",
                "name": "S&P 500 Index",
                "category": "Indices",
                "dataset": "indices",
            },
        ]

        resolved = resolve_market_specs([spec], catalog)[0]

        self.assertEqual(resolved.symbol, "SPX")
        self.assertEqual(resolved.dataset, "indices")


class LSEPayloadTests(unittest.TestCase):
    def test_candles_are_sorted_and_normalized(self):
        rows = [
            {"timestamp": "2026-01-01T00:05:00Z", "open": 2, "high": 3, "low": 1, "close": 2.5},
            {"timestamp": "2026-01-01T00:00:00Z", "open": 1, "high": 2, "low": 0.5, "close": 1.5},
        ]

        candles = normalize_candles(rows)

        self.assertEqual([row["close"] for row in candles], [1.5, 2.5])
        self.assertEqual(candles[0]["volume"], 0)

    def test_tick_does_not_expose_credentials(self):
        payload = serialize_tick(
            {"symbol": "SPX", "price": 5000, "bid": 4999.5, "ask": 5000.5}
        )

        self.assertEqual(payload["type"], "tick")
        self.assertEqual(payload["symbol"], "SPX")
        self.assertNotIn("api_key", payload)


if __name__ == "__main__":
    unittest.main()
