"""Typed result structures shared across the engine.

The engine is deterministic and returns plain data objects (no Streamlit, no
side effects), so the UI and the tests can consume identical structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

import pandas as pd


REGIMES = (
    "Strong Bearish",
    "Bearish",
    "Neutral",
    "Bullish",
    "Strong Bullish",
)


@dataclass
class InstrumentData:
    """Raw market data for one instrument, already normalised to OHLCV frames."""

    symbol: str
    name: str
    sector: str
    cluster: str
    daily: pd.DataFrame                       # index=datetime, cols o/h/l/c[/v]
    intraday: Optional[pd.DataFrame] = None
    last_timestamp: Optional[pd.Timestamp] = None


@dataclass
class InstrumentScore:
    symbol: str
    name: str
    sector: str
    cluster: str
    score: float
    regime: str
    price: Optional[float] = None
    daily_change_pct: Optional[float] = None
    components: Dict[str, Optional[float]] = field(default_factory=dict)
    component_weights: Dict[str, float] = field(default_factory=dict)
    momentum_horizon_scores: Dict[str, float] = field(default_factory=dict)
    eligible: bool = True
    stale: bool = False
    reasons: List[str] = field(default_factory=list)
    sparkline: List[float] = field(default_factory=list)
    contribution: Optional[float] = None      # weight-share of parent cluster
    last_timestamp: Optional[pd.Timestamp] = None


ChildResult = Union["GroupResult", InstrumentScore]


@dataclass
class GroupResult:
    """A cluster, a sector, or the global asset-class node."""

    name: str
    level: str                                # "cluster" | "sector" | "global"
    score: float                              # directional (weighted mean)
    blended_score: float                      # directional*0.7 + breadth*0.3
    regime: str
    breadth_score: float
    pct_bull: float
    pct_bear: float
    pct_neutral: float
    confirming: int
    n_children: int
    n_active: int
    dominant: str                             # "bull" | "bear" | "mixed"
    confidence: float = 0.0
    change_status: str = "unchanged"          # new|strengthening|weakening|unchanged
    explanation: str = ""
    data_quality_ok: bool = True
    children: List[ChildResult] = field(default_factory=list)
    child_kind: str = "instrument"            # "instrument" | "group"


@dataclass
class RegimeResult:
    asset_class: str
    timestamp: pd.Timestamp
    provider: str
    global_regime: GroupResult
    warnings: List[str] = field(default_factory=list)
    n_instruments: int = 0
    n_eligible: int = 0
