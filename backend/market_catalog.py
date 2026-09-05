from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import MarketSpec


def load_market_specs(path: Path) -> list[MarketSpec]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [MarketSpec(**row) for row in rows]


def _normalized(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", str(value or "").upper()).strip()


def _score(row: dict[str, Any], spec: MarketSpec) -> int:
    symbol = _normalized(row.get("symbol"))
    name = _normalized(row.get("name"))
    category = str(row.get("category") or "")
    if spec.categories and category not in spec.categories:
        return 0

    scores: list[int] = []
    for raw_term in spec.search_terms:
        term = _normalized(raw_term)
        if not term:
            continue
        if spec.strict:
            scores.append(1000 if term in {symbol, name} else 0)
            continue
        if symbol == term:
            scores.append(1000)
        elif name == term:
            scores.append(950)
        elif term in symbol:
            scores.append(800 - max(0, len(symbol) - len(term)))
        elif term in name:
            scores.append(700 - max(0, len(name) - len(term)))
        elif all(part in f"{symbol} {name}" for part in term.split()):
            scores.append(600)

    score = max(scores, default=0)
    if spec.id == "oil" and "WTI" in f"{symbol} {name}":
        score += 120
    if spec.id == "gold" and ("SPOT" in name or symbol in {"XAU USD", "XAUUSD"}):
        score += 100
    return score


def resolve_market_specs(
    specs: list[MarketSpec], catalog: list[dict[str, Any]]
) -> list[MarketSpec]:
    for spec in specs:
        if spec.symbol:
            exact = [
                row
                for row in catalog
                if str(row.get("symbol") or "").upper() == spec.symbol.upper()
                and (not spec.categories or row.get("category") in spec.categories)
            ]
            if exact:
                match = exact[0]
                spec.dataset = match.get("dataset")
                spec.resolved_name = match.get("name") or spec.name
                spec.error = None
                continue
            spec.error = f"Configured symbol unavailable: {spec.symbol}"
            spec.symbol = None

        ranked = sorted(
            ((score, row) for row in catalog if (score := _score(row, spec)) > 0),
            key=lambda item: (item[0], item[1].get("ticks") or 0),
            reverse=True,
        )
        spec.candidates = [row for _, row in ranked[:5]]
        if not ranked:
            spec.error = f"No exact London Strategic Edge match for {spec.name}"
            continue

        match = ranked[0][1]
        spec.symbol = str(match["symbol"])
        spec.dataset = match.get("dataset")
        spec.resolved_name = match.get("name") or spec.name
        spec.error = None
    return specs
