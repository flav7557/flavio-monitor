"""Minimal live-price pilotage page powered by LSE."""

from __future__ import annotations

import html
import json
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from typing import Optional

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

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
    html, body {
        margin:0; padding:0; background:#08080a; overflow:hidden;
        font-family:"Century Gothic", "Questrial", "Avenir", "Futura", sans-serif;
    }
    .lp-grid {
        display:grid; grid-template-columns:repeat(3,minmax(0,1fr));
        grid-template-rows:repeat(2,335px);
        gap:0; border:1px solid rgba(255,255,255,0.26);
        background:rgba(255,255,255,0.20);
    }
    .lp-cell {
        min-width:0; background:#08080a; border-right:1px solid rgba(255,255,255,0.26);
        border-bottom:1px solid rgba(255,255,255,0.26);
        padding:0.95rem 1.0rem 0.7rem 1.0rem; display:flex; flex-direction:column;
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
        color:#f4f5f7; font-size:clamp(1.9rem,3.5vw,3.7rem);
        line-height:0.95; font-weight:750; letter-spacing:0;
        font-variant-numeric:tabular-nums;
    }
    .lp-chart {
        width:100%; flex:1; min-height:170px; margin:0.65rem 0 0.45rem 0;
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
    .lp-tv {
        color:#6e7681; text-decoration:none; font-size:0.62rem;
        letter-spacing:0.08em; text-transform:uppercase;
    }
    @media (max-width: 900px) {
        .lp-grid { grid-template-columns:1fr; grid-template-rows:none; }
        .lp-cell { min-height:310px; border-right:0; border-bottom:1px solid rgba(255,255,255,0.26); }
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
                    symbol, timeframe="1m", limit=240, order="desc",
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
    candles = []
    if not minute.empty:
        live = _as_float(minute["close"].iloc[-1]) or live
        chart_frame = minute.dropna(subset=["open", "high", "low", "close"]).tail(240)
        for ts, candle in chart_frame.iterrows():
            timestamp = pd.Timestamp(ts)
            if timestamp.tzinfo is None:
                timestamp = timestamp.tz_localize("UTC")
            else:
                timestamp = timestamp.tz_convert("UTC")
            candles.append({
                "time": int(timestamp.timestamp()),
                "open": float(candle["open"]),
                "high": float(candle["high"]),
                "low": float(candle["low"]),
                "close": float(candle["close"]),
            })

    day = None
    if live is not None and previous not in (None, 0):
        day = (live / previous - 1) * 100
    return {"previous": previous, "live": live, "day": day, "candles": candles}


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
            if quote.get("candles"):
                last = quote["candles"][-1]
                last["close"] = tick["live"]
                last["high"] = max(last["high"], tick["live"])
                last["low"] = min(last["low"], tick["live"])
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


def _card(row: dict, index: int) -> str:
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
        f"<div class='lp-chart' id='chart-{index}'></div>"
        "<div class='lp-meta'>"
        f"<span class='lp-change' style='color:{color}'>{html.escape(_fmt_pct(day))}</span>"
        f"<span class='{live_class}'>{state}</span>"
        "</div>"
        "</div>"
    )


def _render_live_html(rows: list[dict], now: pd.Timestamp) -> str:
    chart_rows = [
        {
            "name": row["name"],
            "day": row.get("day"),
            "candles": row.get("candles", []),
        }
        for row in rows
    ]
    payload = json.dumps(chart_rows, ensure_ascii=False)
    cards = "".join(_card(row, index) for index, row in enumerate(rows))
    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
{CSS}
</head>
<body>
<div class="lp">
    <div class="lp-head">
        <div class="lp-title">Live Pilotage</div>
        <div>
            <span class="lp-clock">maj {html.escape(now.strftime('%H:%M:%S'))} Paris</span>
            <span style="color:#30363d;margin:0 0.45rem;">/</span>
            <a class="lp-tv" href="https://www.tradingview.com/" target="_blank">TradingView</a>
        </div>
    </div>
    <div class="lp-grid">{cards}</div>
</div>
<script>
const rows = {payload};
const upColor = "{UP}";
const downColor = "{DOWN}";
const neutralColor = "{DIM}";

function seriesColor(row) {{
    if ((row.day || 0) > 0) return upColor;
    if ((row.day || 0) < 0) return downColor;
    return neutralColor;
}}

function addCandles(chart, options) {{
    if (LightweightCharts.CandlestickSeries && chart.addSeries) {{
        return chart.addSeries(LightweightCharts.CandlestickSeries, options);
    }}
    return chart.addCandlestickSeries(options);
}}

rows.forEach((row, index) => {{
    const container = document.getElementById(`chart-${{index}}`);
    const color = seriesColor(row);
    const chart = LightweightCharts.createChart(container, {{
        width: container.clientWidth,
        height: container.clientHeight,
        autoSize: true,
        layout: {{
            background: {{ type: "solid", color: "#08080a" }},
            textColor: "rgba(139,148,158,0.78)",
            fontFamily: "Century Gothic, Questrial, Avenir, sans-serif",
        }},
        grid: {{
            vertLines: {{ color: "rgba(255,255,255,0.045)" }},
            horzLines: {{ color: "rgba(255,255,255,0.045)" }},
        }},
        crosshair: {{
            mode: LightweightCharts.CrosshairMode.Normal,
            vertLine: {{ color: "rgba(255,255,255,0.22)", width: 1, style: 2, labelBackgroundColor: "#0d1117" }},
            horzLine: {{ color: "rgba(255,255,255,0.22)", width: 1, style: 2, labelBackgroundColor: "#0d1117" }},
        }},
        rightPriceScale: {{
            borderColor: "rgba(255,255,255,0.14)",
            scaleMargins: {{ top: 0.12, bottom: 0.12 }},
        }},
        timeScale: {{
            borderColor: "rgba(255,255,255,0.14)",
            timeVisible: true,
            secondsVisible: false,
            rightOffset: 3,
            barSpacing: 5,
        }},
        localization: {{
            locale: "fr-FR",
        }},
    }});
    const candles = row.candles || [];
    const series = addCandles(chart, {{
        upColor,
        downColor,
        borderUpColor: upColor,
        borderDownColor: downColor,
        wickUpColor: upColor,
        wickDownColor: downColor,
        priceLineColor: color,
        priceLineWidth: 1,
        lastValueVisible: true,
    }});
    if (candles.length > 0) {{
        series.setData(candles);
        chart.timeScale().fitContent();
    }}
    const observer = new ResizeObserver(entries => {{
        const rect = entries[0].contentRect;
        chart.resize(rect.width, rect.height);
    }});
    observer.observe(container);
}});
</script>
</body>
</html>
"""


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

    components.html(_render_live_html(rows, now), height=725, scrolling=False)


def render() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    _live_grid()
