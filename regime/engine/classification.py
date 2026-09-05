"""Map a directional score onto a regime label, with optional hysteresis.

Hysteresis keeps the previous label until the score crosses back past an exit
band, which stops the regime flickering when a score sits on a threshold.
"""

from __future__ import annotations

from typing import Optional

from ..config import RegimeConfig


def classify_score(score: float, cfg: RegimeConfig) -> str:
    if score >= cfg.t_strong_bull:
        return "Strong Bullish"
    if score >= cfg.t_bull:
        return "Bullish"
    if score <= cfg.t_strong_bear:
        return "Strong Bearish"
    if score <= cfg.t_bear:
        return "Bearish"
    return "Neutral"


def classify_with_hysteresis(
    score: float, previous: Optional[str], cfg: RegimeConfig
) -> str:
    """Classify ``score`` but resist leaving ``previous`` until the score
    clears the corresponding exit band."""

    raw = classify_score(score, cfg)
    if previous is None or previous == raw:
        return raw

    # Hold the stronger previous state while the score is still inside its
    # exit band (prevents one-tick flips around a boundary).
    if previous == "Strong Bullish" and score >= cfg.h_strong_bull_exit:
        return "Strong Bullish"
    if previous == "Bullish" and score >= cfg.h_bull_exit:
        return "Bullish" if raw != "Strong Bullish" else raw
    if previous == "Strong Bearish" and score <= cfg.h_strong_bear_exit:
        return "Strong Bearish"
    if previous == "Bearish" and score <= cfg.h_bear_exit:
        return "Bearish" if raw != "Strong Bearish" else raw
    return raw


def regime_direction(regime: str) -> str:
    if "Bull" in regime:
        return "bull"
    if "Bear" in regime:
        return "bear"
    return "neutral"


def regime_rank(regime: str) -> int:
    """Ordinal used to detect strengthening/weakening."""

    order = {
        "Strong Bearish": -2,
        "Bearish": -1,
        "Neutral": 0,
        "Bullish": 1,
        "Strong Bullish": 2,
    }
    return order.get(regime, 0)
