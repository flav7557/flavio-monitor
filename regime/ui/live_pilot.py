"""Minimal live-price pilotage page powered by LSE."""

from __future__ import annotations

import html
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from typing import Optional

import pandas as pd
import streamlit as st

from ..data.provider import normalize_candles


UP = "#3fb950"
DOWN = "#f85149"
DIM = "#8b949e"
TXT = "#f4f5f7"

PILOT_TARGETS = [
    ("CAC 40", "indices", ("CAC 40", "FCHI", "FR40", "CAC")),
    ("Gold", "commodities", ("XAU/USD", "GOLD", "GC", "XAU")),
    ("SPX", "indices", ("SPX", "S&P 500", "US500", "SP500")),
    ("SX5E", "indices", ("SX5E", "STOXX50E", "EURO STOXX 50", "EU50")),
    ("Oil", "commodities", ("BRENT", "UKOIL", "BCO", "BZ", "WTI", "USOIL")),
    ("Nasdaq", "indices", ("NDX", "NASDAQ 100", "US100", "NASDAQ")),
]

CSS = """
<style>
    .lp { color:#f4f5f7; }
    .lp-head {
        display:flex; align-items:baseline; justify-content:space-between;
        gap:1rem; margin:0.15rem 0 0.55rem 0;
    }
    .lp-title {
        color:#f4f5f7; font-size:0.74rem; letter-spacing:0.26em;
        text-transform:uppercase; font-weight:700;
    }
    .lp-clock {
        color:#8b949e; font-size:0.72rem; font-variant-numeric:tabular-nums;
    }
    .lp-grid {
        display:grid; grid-template-columns:repeat(3,minmax(0,1fr));
        grid-template-rows:repeat(2,minmax(235px,36vh));
        gap:0; border:1px solid rgba(255,255,255,0.26);
        background:rgba(255,255,255,0.20);
    }
    .lp-cell {
        min-width:0; background:#08080a; border-right:1px solid rgba(255,255,255,0.26);
        border-bottom:1px solid rgba(255,255,255,0.26);
        padding:1.15rem 1.25rem; display:flex; flex-direction:column;
        justify-content:space-between;
    }
    .lp-cell:nth-child(3n) { border-right:0; }
    .lp-cell:nth-child(n+4) { border-bottom:0; }
    .lp-kicker {
        color:#8b949e; font-size:0.58rem; letter-spacing:0.22em;
        text-transform:uppercase; font-weight:700;
    }
    .lp-name {
        color:#f4f5f7; font-size:1.05rem; letter-spacing:0.04em;
        text-transform:uppercase; font-weight:700; margin-top:0.35rem;
    }
    .lp-price {
        color:#f4f5f7; font-size:clamp(2.1rem,4.4vw,4.9rem);
        line-height:0.95; font-weight:750; letter-spacing:0;
        font-variant-numeric:tabular-nums;
    }
    .lp-chart {
        width:100%; height:76px; margin:0.7rem 0 0.85rem 0;
    }
    .lp-chart svg {
        display:block; width:100%; height:100%; overflow:visible;
    }
    .lp-meta {
        display:flex; align-items:center; justify-content:space-between;
        gap:0.8rem; color:#8b949e; font-size:0.82rem;
        font-variant-numeric:tabular-nums;
    }
    .lp-change { font-size:1.0rem; font-weight:750; }
    .lp-live {
        color:#8b949e; font-size:0.58rem; letter-spacing:0.18em;
        text-transform:uppercase; font-weight:700;
    }
    .lp-live.on { color:#3fb950; }
    .lp-error {
        color:#f85149; border:1px solid rgba(248,81,73,0.35);
        padding:0.9rem 1rem; font-size:0.86rem;
    }
    @media (max-width: 900px) {
        .lp-grid { grid-template-columns:1fr; grid-template-rows:none; }
        .lp-cell { min-height:185px; border-right:0; border-bottom:1px solid rgba(255,255,255,0.26); }
        .lp-cell:nth-child(n+4) { border-bottom:1px solid rgba(255,255,255,0.26); }
        .lp-cell:last-child { border-bottom:0; }
    }
</style>
"""


def _as_float(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return None


def _match_score(item: dict, candidates: tuple[str, ...]) -> tuple[int, int]:
    symbol = str(item.get("symbol") or "").upper()
    name = str(item.get("name") or "").upper()
    haystack = f"{symbol} {name}"
    best = 0
    for raw in candidates:
        cand = raw.upper()
        if symbol == cand:
            best = max(best, 100)
        elif symbol.replace("/", "") == cand.replace("/", ""):
            best = max(best, 90)
        elif cand in symbol:
            best = max(best, 80)
        elif cand in name:
            best = max(best, 70)
        elif all(part in haystack for part in cand.split()):
            best = max(best, 60)
    return best, -len(symbol)


def _catalog(client) -> list[dict]:
    rows = []
    for category in ("indices", "commodities", "commodity"):
        try:
            rows.extend(client.catalog(category) or [])
        except Exception:
            continue
    if not rows:
        try:
            rows = client.catalog() or []
        except Exception:
            rows = []

    deduped = []
    seen = set()
    for row in rows:
        key = (row.get("symbol"), row.get("category"), row.get("dataset"))
        if row.get("symbol") and key not in seen:
            deduped.append(row)
            seen.add(key)
    return deduped


def _resolve_rows(catalog: list[dict]) -> list[dict]:
    by_category = {}
    for item in catalog:
        key = str(item.get("category") or "").lower()
        by_category.setdefault(key, []).append(item)

    rows = []
    for display_name, category_name, candidates in PILOT_TARGETS:
        pool = by_category.get(category_name, [])
        if category_name == "commodities":
            pool = pool + by_category.get("commodity", [])
        scored = sorted(
            ((_match_score(item, candidates), item) for item in pool),
            key=lambda pair: pair[0],
            reverse=True,
        )
        item = scored[0][1] if scored and scored[0][0][0] > 0 else None
        rows.append({
            "name": display_name,
            "symbol": item.get("symbol") if item else None,
            "dataset": item.get("dataset") if item else None,
        })
    return rows


def _quote_from_candles(api_key: str, symbol: str, dataset: Optional[str]) -> dict:
    from lse import LSE

    client = LSE(api_key=api_key, timeout=15)
    try:
        try:
            daily = normalize_candles(
                client.candles(
                    symbol, timeframe="1d", limit=2, order="desc",
                    dataset=dataset,
                )
            )
        except Exception:
            daily = pd.DataFrame()
        try:
            minute = normalize_candles(
                client.candles(
                    symbol, timeframe="1m", limit=90, order="desc",
                    dataset=dataset,
                )
            )
        except Exception:
            minute = pd.DataFrame()
    finally:
        try:
            client.disconnect()
        except Exception:
            pass

    previous = None
    live = None
    if not daily.empty:
        previous = _as_float(daily["close"].iloc[-2 if len(daily) > 1 else -1])
        live = _as_float(daily["close"].iloc[-1])
    series = []
    if not minute.empty:
        live = _as_float(minute["close"].iloc[-1]) or live
        series = [
            float(value)
            for value in minute["close"].dropna().tail(90).tolist()
            if _as_float(value) is not None
        ]

    day = None
    if live is not None and previous not in (None, 0):
        day = (live / previous - 1) * 100
    return {"previous": previous, "live": live, "day": day, "series": series}


def _stream_prices(api_key: str, symbols: tuple[str, ...], seconds: float = 1.25) -> dict:
    import queue
    import threading
    import time

    from lse import LSE

    if not symbols:
        return {}

    ticks: dict[str, dict] = {}
    events: queue.Queue = queue.Queue()
    client_box = {"client": None}

    def _worker() -> None:
        client = None
        try:
            client = LSE(api_key=api_key, timeout=8)
            client_box["client"] = client
            for tick in client.stream(list(symbols), reconnect=False):
                events.put(tick)
                if len(ticks) >= len(symbols):
                    break
        except Exception:
            return
        finally:
            if client is not None:
                try:
                    client.disconnect()
                except Exception:
                    pass

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and len(ticks) < len(symbols):
        try:
            tick = events.get(timeout=0.15)
        except queue.Empty:
            continue
        symbol = getattr(tick, "symbol", None)
        price = _as_float(getattr(tick, "price", None))
        if symbol and price is not None:
            ticks[symbol] = {"live": price, "is_stream": True}

    client = client_box.get("client")
    if client is not None:
        try:
            client.disconnect()
        except Exception:
            pass
    return ticks


@st.cache_data(ttl=2, show_spinner=False)
def _load_quotes(salt: int) -> list[dict]:
    from lse import LSE

    api_key = os.environ.get("LSE_API_KEY")
    if not api_key:
        raise RuntimeError("LSE_API_KEY manquant : les prix live utilisent uniquement l'API LSE.")

    client = LSE(api_key=api_key, timeout=20)
    try:
        rows = _resolve_rows(_catalog(client))
    finally:
        try:
            client.disconnect()
        except Exception:
            pass

    resolved = [row for row in rows if row["symbol"]]
    quotes = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(_quote_from_candles, api_key, row["symbol"], row["dataset"]): row["symbol"]
            for row in resolved
        }
        try:
            for future in as_completed(futures, timeout=8):
                symbol = futures[future]
                try:
                    quotes[symbol] = future.result()
                except Exception:
                    quotes[symbol] = {}
        except TimeoutError:
            pass

    stream = _stream_prices(api_key, tuple(row["symbol"] for row in resolved))
    for row in rows:
        symbol = row["symbol"]
        quote = quotes.get(symbol, {}) if symbol else {}
        tick = stream.get(symbol, {}) if symbol else {}
        if tick.get("live") is not None:
            quote["live"] = tick["live"]
            quote["is_stream"] = True
        row.update(quote)
    return rows


def _fmt_price(value, name: str) -> str:
    if value is None:
        return "—"
    if name == "Oil":
        return f"{value:,.2f}"
    if name == "Gold":
        return f"{value:,.1f}"
    return f"{value:,.2f}"


def _fmt_pct(value) -> str:
    if value is None:
        return "—"
    return f"{value:+.2f}%"


def _sparkline(values: list[float], color: str) -> str:
    clean = [v for v in values if _as_float(v) is not None]
    if len(clean) < 2:
        return (
            "<div class='lp-chart'>"
            "<svg viewBox='0 0 360 76' preserveAspectRatio='none'>"
            "<line x1='0' y1='38' x2='360' y2='38' "
            "stroke='rgba(255,255,255,0.14)' stroke-width='1'/>"
            "</svg></div>"
        )

    lo = min(clean)
    hi = max(clean)
    span = hi - lo or abs(hi) * 0.001 or 1.0
    points = []
    count = len(clean)
    for index, value in enumerate(clean):
        x = index / (count - 1) * 360
        y = 68 - ((value - lo) / span) * 60
        points.append(f"{x:.1f},{y:.1f}")

    last_y = points[-1].split(",")[1]
    return (
        "<div class='lp-chart'>"
        "<svg viewBox='0 0 360 76' preserveAspectRatio='none'>"
        "<line x1='0' y1='38' x2='360' y2='38' "
        "stroke='rgba(255,255,255,0.10)' stroke-width='1'/>"
        f"<polyline points='{' '.join(points)}' fill='none' stroke='{color}' "
        "stroke-width='2.1' vector-effect='non-scaling-stroke'/>"
        f"<circle cx='360' cy='{last_y}' r='3.2' fill='{color}'/>"
        "</svg></div>"
    )


def _card(row: dict) -> str:
    live = row.get("live")
    day = row.get("day")
    color = UP if (day or 0) > 0 else DOWN if (day or 0) < 0 else DIM
    live_class = "lp-live on" if row.get("is_stream") else "lp-live"
    state = "LIVE" if row.get("is_stream") else "LSE"
    return (
        "<div class='lp-cell'>"
        "<div>"
        "<div class='lp-kicker'>Pilotage</div>"
        f"<div class='lp-name'>{html.escape(row['name'])}</div>"
        "</div>"
        f"<div class='lp-price'>{html.escape(_fmt_price(live, row['name']))}</div>"
        f"{_sparkline(row.get('series', []), color)}"
        "<div class='lp-meta'>"
        f"<span class='lp-change' style='color:{color}'>{html.escape(_fmt_pct(day))}</span>"
        f"<span class='{live_class}'>{state}</span>"
        "</div>"
        "</div>"
    )


@st.fragment(run_every=2)
def _live_grid() -> None:
    now = pd.Timestamp.now(tz="Europe/Paris")
    try:
        rows = _load_quotes(int(now.timestamp() // 2))
    except Exception as exc:
        st.markdown(
            f"<div class='lp'><div class='lp-error'>Impossible de charger les prix live LSE : "
            f"{html.escape(str(exc))}</div></div>",
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        "<div class='lp'>"
        "<div class='lp-head'>"
        "<div class='lp-title'>Live Pilotage</div>"
        f"<div class='lp-clock'>maj {now.strftime('%H:%M:%S')} Paris</div>"
        "</div>"
        f"<div class='lp-grid'>{''.join(_card(row) for row in rows)}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def render() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    _live_grid()
