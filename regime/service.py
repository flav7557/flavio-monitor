"""Wires a data provider to the regime pipeline. Provider-selection and I/O
live here; the engine stays pure."""

from __future__ import annotations

from dataclasses import replace
from typing import Optional, Tuple

from .config import DEFAULT_CONFIG, RegimeConfig
from .data.lse_provider import LSEProvider
from .data.provider import MarketDataProvider
from .data.yf_provider import YahooProvider
from .engine.models import RegimeResult
from .engine.persistence import RegimeStore
from .engine.pipeline import run_pipeline


def select_provider(cfg: RegimeConfig) -> Tuple[MarketDataProvider, str, Optional[str]]:
    """Return ``(provider, name, note)``. Prefers LSE; falls back to Yahoo when
    no key is present (with a user-facing note) unless the caller forced one."""

    if cfg.provider == "yfinance":
        return YahooProvider(), "yfinance", None

    lse = LSEProvider()
    if lse.available():
        return lse, "lse", None

    if cfg.allow_yf_fallback:
        return (
            YahooProvider(),
            "yfinance",
            "LSE_API_KEY not found in this environment — showing Yahoo Finance "
            "fallback data. On the deployed app (with the LSE secret set) the "
            "same engine runs on the London Strategic Edge feed.",
        )
    raise RuntimeError("LSE_API_KEY not found and yfinance fallback disabled.")


def compute_regime(
    cfg: RegimeConfig = DEFAULT_CONFIG,
    store_path: str = ".regime_state/commodities.json",
) -> RegimeResult:
    provider, name, note = select_provider(cfg)
    cfg = replace(cfg, provider=name)
    instruments = provider.fetch_universe(cfg)
    store = RegimeStore(store_path, cfg)
    result = run_pipeline(instruments, cfg, store=store)
    if note:
        result.warnings.insert(0, note)
    return result


def fetch_live_prices(cfg: RegimeConfig, symbols) -> dict:
    """Light, frequently-called latest-price fetch (live terminal)."""
    provider, _name, _note = select_provider(cfg)
    try:
        return provider.latest_prices(symbols)
    except Exception:
        return {}
