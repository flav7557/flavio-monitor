from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MarketSpec:
    id: str
    name: str
    symbol: str | None
    categories: list[str]
    search_terms: list[str]
    position: str
    strict: bool = False
    dataset: str | None = None
    resolved_name: str | None = None
    error: str | None = None
    candidates: list[dict[str, Any]] = field(default_factory=list)

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "symbol": self.symbol,
            "dataset": self.dataset,
            "resolvedName": self.resolved_name,
            "position": self.position,
            "status": "available" if self.symbol else "unavailable",
            "error": self.error,
        }
