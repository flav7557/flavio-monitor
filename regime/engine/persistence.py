"""Regime persistence + change tracking.

A raw regime must be observed ``persistence_length`` times in a row before the
*official* displayed regime switches. This prevents one noisy calculation from
flipping the headline. Recent history is stored on disk so the UI can show
whether a regime is newly changed, strengthening, weakening or unchanged.

The store degrades gracefully to an in-memory dict if the filesystem is not
writable (e.g. a locked-down deployment).
"""

from __future__ import annotations

import json
import os
from typing import Dict, Optional

from ..config import RegimeConfig
from .classification import regime_rank


class RegimeStore:
    def __init__(self, path: str, cfg: RegimeConfig):
        self.path = path
        self.cfg = cfg
        self._state: Dict[str, dict] = {}
        self._dirty = False
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                self._state = json.load(fh)
        except (FileNotFoundError, ValueError, OSError):
            self._state = {}

    def save(self) -> None:
        if not self._dirty:
            return
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(self._state, fh)
            self._dirty = False
        except OSError:
            pass  # in-memory only

    def update(
        self, key: str, raw_regime: str, score: float, timestamp: str
    ) -> dict:
        """Advance the persistence state for ``key`` and return a dict with
        ``official`` (regime to display), ``change_status``, ``official_count``
        and ``persistence_frac``."""

        st = self._state.get(key)
        if st is None:
            st = {
                "official": raw_regime,
                "official_count": 1,
                "pending": None,
                "pending_count": 0,
                "last_score": score,
                "history": [],
            }
            change = "newly changed"
        else:
            change = self._advance(st, raw_regime, score)

        st["last_score"] = score
        st.setdefault("history", []).append(
            {"t": timestamp, "score": round(float(score), 2),
             "regime": st["official"]}
        )
        if len(st["history"]) > self.cfg.history_max:
            st["history"] = st["history"][-self.cfg.history_max:]

        self._state[key] = st
        self._dirty = True

        frac = min(1.0, st["official_count"] / max(1, self.cfg.persistence_length))
        return {
            "official": st["official"],
            "change_status": change,
            "official_count": st["official_count"],
            "pending": st["pending"],
            "pending_count": st["pending_count"],
            "persistence_frac": frac,
        }

    def _advance(self, st: dict, raw: str, score: float) -> str:
        prev_score = st.get("last_score", score)

        if raw == st["official"]:
            st["pending"] = None
            st["pending_count"] = 0
            st["official_count"] = st.get("official_count", 1) + 1
            return self._trend(st["official"], prev_score, score)

        # raw differs from official -> accumulate towards a switch
        if st.get("pending") == raw:
            st["pending_count"] = st.get("pending_count", 0) + 1
        else:
            st["pending"] = raw
            st["pending_count"] = 1

        if st["pending_count"] >= self.cfg.persistence_length:
            st["official"] = raw
            st["official_count"] = 1
            st["pending"] = None
            st["pending_count"] = 0
            return "newly changed"

        # not switched yet: keep showing official, flag a pending change
        return "pending change"

    @staticmethod
    def _trend(regime: str, prev_score: float, score: float) -> str:
        rank = regime_rank(regime)
        delta = score - prev_score
        if abs(delta) < 3.0:
            return "unchanged"
        if rank > 0:                       # bullish family
            return "strengthening" if delta > 0 else "weakening"
        if rank < 0:                       # bearish family
            return "strengthening" if delta < 0 else "weakening"
        return "unchanged"

    def history(self, key: str):
        return self._state.get(key, {}).get("history", [])
