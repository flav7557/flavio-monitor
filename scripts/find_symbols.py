from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from lse import LSE


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

QUERIES = ("CAC", "ASX 5", "Gold", "WTI", "Crude Oil", "S&P", "Nasdaq")


def normalized(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", str(value or "").upper()).strip()


def score(row: dict, query: str) -> int:
    symbol = normalized(row.get("symbol"))
    name = normalized(row.get("name"))
    term = normalized(query)
    if term in {symbol, name}:
        return 1000
    if term in symbol:
        return 800
    if term in name:
        return 700
    return 500 if all(part in f"{symbol} {name}" for part in term.split()) else 0


def main() -> int:
    api_key = os.getenv("LSE_API_KEY")
    if not api_key:
        print("LSE_API_KEY is missing. Add it to .env before running this script.")
        return 1

    client = LSE(api_key=api_key, timeout=90)
    try:
        catalog = client.catalog()
    finally:
        client.disconnect()

    for query in QUERIES:
        print(f"\n{query}")
        print("-" * len(query))
        matches = sorted(
            ((score(row, query), row) for row in catalog if score(row, query) > 0),
            key=lambda item: (item[0], item[1].get("ticks") or 0),
            reverse=True,
        )[:8]
        if not matches:
            print("No exact catalog result")
            continue
        for _, row in matches:
            print(
                f"{row.get('symbol', ''):<18} | "
                f"{row.get('name', ''):<44} | "
                f"{row.get('category', ''):<14} | {row.get('dataset', '')}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
