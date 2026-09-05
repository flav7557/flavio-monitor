from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
MARKETS_FILE = ROOT_DIR / "config" / "markets.json"

load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    lse_api_key: str | None = os.getenv("LSE_API_KEY")
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
    stream_backoff_max_seconds: float = float(
        os.getenv("STREAM_BACKOFF_MAX_SECONDS", "30")
    )


settings = Settings()
