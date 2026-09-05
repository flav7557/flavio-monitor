"""Deterministic, quantitative explanations built from the score components.

No language model, no invented commentary — every sentence is derived from the
numbers so the reasoning is fully traceable.
"""

from __future__ import annotations

import statistics
from typing import List

from .classification import regime_direction
from .confidence import collect_instruments
from .models import GroupResult, InstrumentScore


def display_regime(group: GroupResult) -> str:
    """Human label. A Neutral group with a clear tilt is shown as
    'Mixed / Slightly Bearish' rather than a flat 'Neutral'."""

    if group.regime != "Neutral":
        return group.regime
    if group.score <= -8:
        return "Mixed / Slightly Bearish"
    if group.score >= 8:
        return "Mixed / Slightly Bullish"
    return "Neutral"


def _dominant_component(instruments: List[InstrumentScore]) -> str:
    """Which component is driving the group hardest, on average."""

    labels = {
        "trend": "trend", "momentum": "momentum",
        "intraday": "intraday impulse", "breakout": "breakout",
    }
    means = {}
    for key in labels:
        vals = [
            i.components.get(key) for i in instruments
            if i.components.get(key) is not None
        ]
        if vals:
            means[key] = statistics.mean(vals)
    if not means:
        return ""
    key = max(means, key=lambda k: abs(means[k]))
    direction = "positive" if means[key] > 0 else "negative"
    return f"{labels[key]} is {direction} on a volatility-adjusted basis"


def explain_sector(sector: GroupResult) -> str:
    active = [c for c in sector.children
              if isinstance(c, GroupResult) and c.n_active > 0]
    if not active:
        return f"{sector.name}: no eligible instruments."

    n = len(active)
    dom = sector.dominant
    dom_word = {"bull": "bullish", "bear": "bearish", "mixed": "mixed"}[dom]
    aligned = [c.name for c in active if regime_direction(c.regime) == dom]

    instruments = [i for i in collect_instruments(sector) if i.eligible]
    driver = _dominant_component(instruments)

    parts = [f"{sector.name} is {display_regime(sector)}."]
    if dom == "mixed":
        parts.append(
            f"Clusters are split ({sector.pct_bull:.0%} bullish, "
            f"{sector.pct_bear:.0%} bearish)."
        )
    else:
        confirming = len(aligned)
        parts.append(
            f"{confirming} of {n} clusters are {dom_word}"
            + (f" ({', '.join(aligned[:3])})" if aligned else "")
            + "."
        )
    if driver:
        parts.append(f"Average {driver}.")
    return " ".join(parts)


def explain_global(g: GroupResult) -> str:
    active = [s for s in g.children
              if isinstance(s, GroupResult) and s.n_active > 0]
    if not active:
        return "No eligible sectors."

    n = len(active)
    bulls = [s.name for s in active if regime_direction(s.regime) == "bull"]
    bears = [s.name for s in active if regime_direction(s.regime) == "bear"]

    parts = [f"Commodity complex is {display_regime(g)} (score {g.score:+.0f})."]
    if bears:
        parts.append(f"{len(bears)}/{n} sectors bearish ({', '.join(bears)}).")
    if bulls:
        parts.append(f"{len(bulls)}/{n} sectors bullish ({', '.join(bulls)}).")
    if g.regime == "Neutral":
        parts.append(
            "Breadth is insufficient for a directional call across the complex."
        )
    return " ".join(parts)


def explain_instrument(inst: InstrumentScore) -> str:
    if not inst.eligible:
        why = inst.reasons[0] if inst.reasons else "no data"
        return f"{inst.name}: excluded ({why})."
    comps = inst.components
    bits = []
    for key, label in (("trend", "trend"), ("momentum", "momentum"),
                       ("intraday", "intraday"), ("breakout", "breakout")):
        v = comps.get(key)
        if v is not None:
            bits.append(f"{label} {v:+.0f}")
    tail = f" · stale ({inst.reasons[0]})" if inst.stale and inst.reasons else ""
    return f"{inst.name} {inst.score:+.0f} — " + ", ".join(bits) + tail
