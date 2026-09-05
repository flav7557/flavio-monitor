"""Centralised configuration for the market-regime engine.

Every tunable parameter lives here so the methodology can be adjusted without
touching the engine or the UI. ``DEFAULT_CONFIG`` is the single instance the
application uses; construct a modified copy with :func:`dataclasses.replace` for
experiments or tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Commodity taxonomy
# ---------------------------------------------------------------------------
# Maps human-readable keywords onto (sector -> cluster). The engine discovers
# the *actual* universe from the data provider at runtime and classifies each
# discovered instrument with this taxonomy, so nothing about the real symbol
# list is hardcoded — only the mapping rules are.
#
# Keywords of length <= 3 are matched against the symbol's base token exactly
# (e.g. "ng" only matches a symbol whose base is NG), longer keywords are
# matched as case-insensitive substrings of the instrument name or symbol.

COMMODITY_TAXONOMY: Dict[str, Dict[str, List[str]]] = {
    "Energy": {
        "Crude": ["brent", "wti", "crude", "ukoil", "usoil", "bco", "cl", "bz"],
        "Refined Products": [
            "gasoline", "rbob", "heating oil", "gasoil", "diesel", "ho", "rb",
        ],
        "Natural Gas": ["natural gas", "nat gas", "natgas", "ng"],
    },
    "Precious Metals": {
        "Gold": ["gold", "xau", "gc"],
        "Silver": ["silver", "xag", "si"],
        "PGM": ["platinum", "xpt", "palladium", "xpd", "pl", "pa"],
    },
    "Industrial Metals": {
        "Copper": ["copper", "xcu", "hg"],
        "Aluminium": ["aluminium", "aluminum", "alu", "ali"],
        "Other Base": ["zinc", "nickel", "lead", "tin", "iron ore", "steel"],
    },
    "Agriculture": {
        "Grains": [
            "corn", "wheat", "soybean", "soybeans", "soy", "oats", "rice",
            "zc", "zw", "zs",
        ],
        "Softs": [
            "sugar", "coffee", "cocoa", "cotton", "orange juice",
            "kc", "sb", "cc", "ct",
        ],
        "Livestock": ["cattle", "hogs", "lean hog", "feeder"],
    },
}


@dataclass
class RegimeConfig:
    """All tunable parameters for one asset class (defaults tuned for daily
    commodity bars). The same object structure is reused for equities, rates,
    FX and credit later."""

    asset_class: str = "Commodities"

    # -- data provider -----------------------------------------------------
    provider: str = "lse"
    allow_yf_fallback: bool = False
    primary_timeframe: str = "1d"
    intraday_timeframe: str = "15m"
    intraday_enabled: bool = True
    history_bars: int = 260            # daily bars to request per instrument
    intraday_bars: int = 200

    # -- component weights (must be interpretable; renormalised if a
    #    component is unavailable for an instrument) ------------------------
    w_trend: float = 0.35
    w_momentum: float = 0.30
    w_intraday: float = 0.20
    w_breakout: float = 0.15

    # -- trend -------------------------------------------------------------
    sma_fast: int = 20
    sma_slow: int = 50
    slope_lookback: int = 5
    atr_period: int = 14
    slope_scale: float = 5.0           # scales per-bar slope (in ATR units)

    # -- momentum ----------------------------------------------------------
    momentum_horizons: Tuple[int, ...] = (5, 20, 60)
    zscore_window: int = 60
    momentum_z_scale: float = 2.0      # z divided by this inside tanh

    # -- intraday impulse --------------------------------------------------
    intraday_short_bars: int = 1       # ~ one intraday bar (15m)
    intraday_medium_bars: int = 4      # ~ one hour on 15m bars
    intraday_vol_window: int = 60
    intraday_z_scale: float = 2.0

    # -- breakout ----------------------------------------------------------
    donchian_period: int = 20
    breakout_mid_cap: float = 60.0     # max |score| when inside the channel

    # -- instrument classification thresholds ------------------------------
    t_strong_bull: float = 40.0
    t_bull: float = 20.0
    t_bear: float = -20.0
    t_strong_bear: float = -40.0

    # -- hysteresis (exit bands; a state is kept until score crosses back) --
    h_bull_exit: float = 10.0
    h_bear_exit: float = -10.0
    h_strong_bull_exit: float = 30.0
    h_strong_bear_exit: float = -30.0

    # -- breadth requirements (applied over a group's children) ------------
    breadth_strong_pct: float = 0.65
    breadth_bull_pct: float = 0.55
    breadth_strong_min_confirm: int = 4
    breadth_bull_min_confirm: int = 3
    breadth_strong_avg: float = 35.0
    breadth_bull_avg: float = 20.0

    # -- global regime confirmation ---------------------------------------
    global_breadth: float = 0.60
    global_min_sectors: int = 3
    global_abs: float = 25.0

    # -- cluster / sector aggregation -------------------------------------
    cluster_blend_directional: float = 0.70
    cluster_blend_breadth: float = 0.30
    sector_weights: Dict[str, float] = field(default_factory=lambda: {
        "Energy": 1.0,
        "Precious Metals": 1.0,
        "Industrial Metals": 1.0,
        "Agriculture": 1.0,
    })

    # -- persistence / hysteresis -----------------------------------------
    persistence_length: int = 3        # consecutive calcs before switching
    history_max: int = 400             # regime-history rows kept on disk

    # -- confidence weights (relative; normalised internally) --------------
    conf_weights: Dict[str, float] = field(default_factory=lambda: {
        "breadth": 0.22,
        "magnitude": 0.20,
        "horizon_agreement": 0.14,
        "cluster_agreement": 0.16,
        "persistence": 0.10,
        "coverage": 0.10,
        "freshness": 0.08,
    })

    # -- data quality ------------------------------------------------------
    min_history_bars: int = 60         # bars needed to score an instrument
    max_stale_days: float = 4.0        # daily quote older than this = stale
    min_eligible_fraction: float = 0.5  # below this -> data-quality warning

    def component_weights(self) -> Dict[str, float]:
        return {
            "trend": self.w_trend,
            "momentum": self.w_momentum,
            "intraday": self.w_intraday,
            "breakout": self.w_breakout,
        }


DEFAULT_CONFIG = RegimeConfig()


def classify_symbol(
    symbol: str,
    name: str = "",
    taxonomy: Dict[str, Dict[str, List[str]]] | None = None,
) -> Tuple[str, str] | None:
    """Classify an instrument into ``(sector, cluster)`` using the taxonomy.

    Returns ``None`` when nothing matches (the instrument is then ignored by
    the commodity engine rather than being force-fitted somewhere wrong).
    """

    taxonomy = taxonomy or COMMODITY_TAXONOMY
    sym = (symbol or "").lower()
    base = sym.split("/")[0].split(".")[0]
    name_l = (name or "").lower()

    for sector, clusters in taxonomy.items():
        for cluster, keywords in clusters.items():
            for kw in keywords:
                if len(kw) <= 3:
                    if base == kw:
                        return sector, cluster
                else:
                    if kw in name_l or kw in sym:
                        return sector, cluster
    return None
