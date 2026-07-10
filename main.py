"""
FLAVIO MONITOR — ALL-IN-ONE AVEC KALMAN SUR TICKS LSE

Installation dans le terminal PyCharm :

python -m pip install --upgrade streamlit pandas plotly yfinance numpy requests
python -m pip install --force-reinstall --no-cache-dir "https://github.com/londonstrategicedge/lse-data/archive/refs/heads/main.zip"

Lancement :

python -m streamlit run Flavio_Monitor_All_In_One_Fixed.py
"""

from __future__ import annotations

import streamlit as st


st.set_page_config(
    page_title="Flavio Monitor",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }

        .unified-navigation-title {
            color: #f4f7fb;
            font-size: 1.45rem;
            font-weight: 750;
            letter-spacing: -0.035em;
            margin: 0 0 0.25rem 0;
        }

        .unified-navigation-subtitle {
            color: #8490a3;
            font-size: 0.78rem;
            margin: 0 0 0.7rem 0;
        }

        .unified-divider {
            height: 1px;
            background: #273142;
            margin: 0.25rem 0 0.8rem 0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        '<div class="unified-navigation-title">Flavio Monitor</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="unified-navigation-subtitle">'
        'Trading workspace · Morning desk · Quant lab'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="unified-divider"></div>',
        unsafe_allow_html=True,
    )

    selected_page = st.radio(
        "Navigation",
        options=[
            "Workspace",
            "Bureau Larbou",
            "Kalman Lab",
        ],
        index=0,
        key="flavio_monitor_navigation",
    )

    st.markdown(
        '<div class="unified-divider"></div>',
        unsafe_allow_html=True,
    )


def execute_embedded_page(
    source: str,
    module_name: str,
    virtual_filename: str,
) -> None:
    namespace = {
        "__name__": module_name,
        "__file__": virtual_filename,
        "__package__": None,
    }

    compiled = compile(
        source,
        virtual_filename,
        "exec",
    )

    exec(
        compiled,
        namespace,
        namespace,
    )


WORKSPACE_SOURCE = r'''
import json
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
from lse import LSE


# =============================================================================
# CONFIGURATION
# =============================================================================


YAHOO_CACHE_SECONDS = 900
MAX_REPLAY_HOURS = 24

MARKETS = {
    "CAC 40": {
        "yahoo": "^FCHI",
        "lse_candidates": [
            "CAC40", "CAC40/EUR", "FR40", "FR40/EUR", "FRA40", "PX1"
        ],
        "search": ["cac 40", "france 40"],
    },
    "DAX": {
        "yahoo": "^GDAXI",
        "lse_candidates": [
            "DAX", "DAX40", "DAX40/EUR", "DE40", "DE40/EUR", "GER40"
        ],
        "search": ["dax 40", "germany 40", "dax"],
    },
    "Euro Stoxx 50": {
        "yahoo": "^STOXX50E",
        "lse_candidates": [
            "SX5E", "EU50", "EU50/EUR", "STOXX50", "ESTX50"
        ],
        "search": ["euro stoxx 50", "stoxx 50"],
    },
    "Nasdaq 100": {
        "yahoo": "^NDX",
        "lse_candidates": [
            "NAS100", "NAS100/USD", "NDX", "NASDAQ100", "US100"
        ],
        "search": ["nasdaq 100", "nasdaq-100"],
    },
    "S&P 500": {
        "yahoo": "^GSPC",
        "lse_candidates": [
            "SPX500", "SPX500/USD", "SPX", "US500", "SP500"
        ],
        "search": ["s&p 500", "sp 500", "standard and poor 500"],
    },
    "Gold": {
        "yahoo": "GC=F",
        "lse_candidates": ["XAU/USD", "GOLD/USD", "GOLD", "GC"],
        "search": ["spot gold", "gold"],
    },
    "Brent": {
        "yahoo": "BZ=F",
        "lse_candidates": [
            "BRENT/USD", "BRENT", "BCO/USD", "UKOIL/USD", "BRN", "BZ"
        ],
        "search": ["brent crude oil", "brent crude", "brent"],
    },
}

YAHOO_INTERVALS = {
    "1 minute": {"interval": "1m", "period": "5d"},
    "5 minutes": {"interval": "5m", "period": "5d"},
    "15 minutes": {"interval": "15m", "period": "5d"},
    "30 minutes": {"interval": "30m", "period": "5d"},
    "1 heure": {"interval": "60m", "period": "1mo"},
}

LSE_INTERVALS = {
    "Ticks": {"seconds": None, "chart_kind": "ticks"},
    "1 seconde": {"seconds": 1, "chart_kind": "candles"},
    "5 secondes": {"seconds": 5, "chart_kind": "candles"},
    "15 secondes": {"seconds": 15, "chart_kind": "candles"},
    "1 minute": {"seconds": 60, "chart_kind": "candles"},
    "5 minutes": {"seconds": 300, "chart_kind": "candles"},
}

REFERENCE_YAHOO_INTERVAL = "15 minutes"

LAYOUTS = {
    "1 — Plein écran": {
        "count": 1,
        "columns": "1fr",
        "rows": "1fr",
        "areas": ["p0"],
        "css_areas": '"p0"',
        "height": 820,
    },
    "2 — Côte à côte": {
        "count": 2,
        "columns": "1fr 1fr",
        "rows": "1fr",
        "areas": ["p0", "p1"],
        "css_areas": '"p0 p1"',
        "height": 820,
    },
    "2 — Empilés": {
        "count": 2,
        "columns": "1fr",
        "rows": "1fr 1fr",
        "areas": ["p0", "p1"],
        "css_areas": '"p0" "p1"',
        "height": 1060,
    },
    "3 — Principal + 2": {
        "count": 3,
        "columns": "2fr 1fr",
        "rows": "1fr 1fr",
        "areas": ["p0", "p1", "p2"],
        "css_areas": '"p0 p1" "p0 p2"',
        "height": 920,
    },
    "4 — Grille 2 × 2": {
        "count": 4,
        "columns": "1fr 1fr",
        "rows": "1fr 1fr",
        "areas": ["p0", "p1", "p2", "p3"],
        "css_areas": '"p0 p1" "p2 p3"',
        "height": 940,
    },
    "5 — Principal + 4": {
        "count": 5,
        "columns": "2fr 1fr 1fr",
        "rows": "1fr 1fr",
        "areas": ["p0", "p1", "p2", "p3", "p4"],
        "css_areas": '"p0 p1 p2" "p0 p3 p4"',
        "height": 940,
    },
    "6 — Grille 3 × 2": {
        "count": 6,
        "columns": "1fr 1fr 1fr",
        "rows": "1fr 1fr",
        "areas": ["p0", "p1", "p2", "p3", "p4", "p5"],
        "css_areas": '"p0 p1 p2" "p3 p4 p5"',
        "height": 940,
    },
}

SETUPS = {
    "Contexte": ["Ouverture", "Clôture veille"],
    "VWAP": ["Ouverture", "Clôture veille", "VWAP séance", "Bandes VWAP"],
    "Microstructure": ["Mid-price", "VWAP séance"],
}

DEFAULT_MARKETS = [
    "CAC 40",
    "DAX",
    "Euro Stoxx 50",
    "Nasdaq 100",
    "S&P 500",
    "Gold",
]


# =============================================================================
# STYLE STREAMLIT
# =============================================================================

st.markdown(
    """
    <style>
        .stApp {
            background: #0b0f15;
        }

        [data-testid="stSidebar"] {
            background: #101620;
            border-right: 1px solid #202938;
        }

        .block-container {
            max-width: 100%;
            padding-top: 0.75rem;
            padding-left: 0.9rem;
            padding-right: 0.9rem;
            padding-bottom: 0.7rem;
        }

        #MainMenu,
        footer {
            visibility: hidden;
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        .workspace-title {
            color: #f4f7fb;
            font-size: 1.7rem;
            font-weight: 730;
            letter-spacing: -0.04em;
            margin: 0;
        }

        .workspace-subtitle {
            color: #8490a3;
            font-size: 0.88rem;
            margin-top: 0.1rem;
            margin-bottom: 0.65rem;
        }

        .sidebar-brand {
            color: #f4f7fb;
            font-size: 1.28rem;
            font-weight: 720;
            letter-spacing: -0.03em;
            margin-bottom: 0.9rem;
        }

        .small-note {
            color: #8490a3;
            font-size: 0.78rem;
            line-height: 1.35;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# API KEY
# =============================================================================

try:
    DEFAULT_API_KEY = st.secrets["LSE_API_KEY"]
except Exception:
    DEFAULT_API_KEY = os.getenv("LSE_API_KEY", "")

with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand">Flavio Monitor</div>',
        unsafe_allow_html=True,
    )

    if DEFAULT_API_KEY:
        api_key = DEFAULT_API_KEY
        st.caption("Clé LSE chargée depuis les secrets du serveur.")
    else:
        api_key = st.text_input(
            "Clé API LSE",
            value="",
            type="password",
            placeholder="lse_live_...",
        )

if not api_key:
    st.markdown(
        '<div class="workspace-title">Flavio Monitor</div>',
        unsafe_allow_html=True,
    )
    st.info("Entre ta clé API LSE dans la barre latérale.")
    st.stop()


# =============================================================================
# CATALOGUE LSE
# =============================================================================

def normalize(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )
    value = value.lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def catalogue_score(row: dict[str, Any], queries: list[str]) -> int:
    symbol = normalize(row.get("symbol"))
    name = normalize(row.get("name"))
    category = normalize(row.get("category"))
    complete_text = f"{symbol} {name}"
    score = 0

    for query in queries:
        query = normalize(query)
        tokens = query.split()

        if query == symbol:
            score = max(score, 1200)
        elif query == name:
            score = max(score, 1100)
        elif query and query in name:
            score = max(score, 700)
        elif query and query in complete_text:
            score = max(score, 500)
        elif tokens and all(token in complete_text for token in tokens):
            score = max(score, 300)

    if any(word in category for word in ["index", "indice", "commodit"]):
        score += 100

    return score


@st.cache_data(ttl=3600, show_spinner=False)
def resolve_lse_symbols(_api_key: str) -> tuple[dict[str, str], list[str]]:
    client = LSE(api_key=_api_key)
    catalogue = client.catalog()

    rows = [row for row in catalogue if row.get("symbol")]
    rows_by_symbol: dict[str, dict[str, Any]] = {}

    for row in rows:
        rows_by_symbol.setdefault(str(row["symbol"]).upper(), row)

    resolved: dict[str, str] = {}
    unresolved: list[str] = []

    for market_name, settings in MARKETS.items():
        selected_row = None

        for candidate in settings["lse_candidates"]:
            selected_row = rows_by_symbol.get(candidate.upper())
            if selected_row is not None:
                break

        if selected_row is None:
            ranked = sorted(
                rows,
                key=lambda row: catalogue_score(row, settings["search"]),
                reverse=True,
            )
            if ranked and catalogue_score(ranked[0], settings["search"]) > 0:
                selected_row = ranked[0]

        if selected_row is None:
            unresolved.append(market_name)
        else:
            resolved[market_name] = str(selected_row["symbol"])

    return resolved, unresolved


try:
    LSE_SYMBOLS, UNRESOLVED_MARKETS = resolve_lse_symbols(api_key)
except Exception as error:
    st.error(f"Impossible de lire le catalogue LSE : {error}")
    st.stop()

AVAILABLE_MARKETS = [
    market_name
    for market_name in MARKETS
    if market_name in LSE_SYMBOLS
]

if not AVAILABLE_MARKETS:
    st.error("Aucun marché demandé n’a été trouvé dans le catalogue LSE.")
    st.stop()


# =============================================================================
# DONNÉES YAHOO
# =============================================================================

@st.cache_data(ttl=YAHOO_CACHE_SECONDS, show_spinner=False)
def load_yahoo_context(
    yahoo_symbol: str,
    yahoo_interval: str,
    yahoo_period: str,
) -> dict[str, Any]:
    ticker = yf.Ticker(yahoo_symbol)

    intraday = ticker.history(
        period=yahoo_period,
        interval=yahoo_interval,
        auto_adjust=False,
        prepost=False,
        actions=False,
    )

    if intraday.empty:
        raise ValueError(f"Aucune donnée intraday pour {yahoo_symbol}.")

    intraday = intraday.rename(columns=str.title)
    intraday = intraday.dropna(subset=["Open", "High", "Low", "Close"])

    if intraday.empty:
        raise ValueError(f"Les bougies reçues pour {yahoo_symbol} sont vides.")

    latest_session_date = intraday.index[-1].date()
    session = intraday[intraday.index.date == latest_session_date].copy()

    daily = ticker.history(
        period="1mo",
        interval="1d",
        auto_adjust=False,
        prepost=False,
        actions=False,
    )
    daily = daily.rename(columns=str.title)
    daily = daily.dropna(subset=["Close"])
    previous_daily = daily[daily.index.date < latest_session_date]

    previous_close = (
        float(previous_daily["Close"].iloc[-1])
        if not previous_daily.empty
        else None
    )

    session_open = float(session["Open"].iloc[0])
    session_high = float(session["High"].max())
    session_low = float(session["Low"].min())
    yahoo_last = float(session["Close"].iloc[-1])

    first_timestamp = pd.Timestamp(session.index[0])
    if first_timestamp.tzinfo is None:
        first_timestamp = first_timestamp.tz_localize("UTC")
    session_start_utc = first_timestamp.tz_convert("UTC")

    now_utc = datetime.now(timezone.utc)
    original_start = session_start_utc.to_pydatetime()
    replay_floor = now_utc - timedelta(hours=MAX_REPLAY_HOURS, minutes=-1)
    replay_is_partial = original_start < replay_floor
    effective_start = max(original_start, replay_floor)

    def numeric_list(column: str) -> list[float | None]:
        result: list[float | None] = []
        for value in session[column].tolist():
            result.append(None if pd.isna(value) else float(value))
        return result

    return {
        "x": [pd.Timestamp(timestamp).isoformat() for timestamp in session.index],
        "open": numeric_list("Open"),
        "high": numeric_list("High"),
        "low": numeric_list("Low"),
        "close": numeric_list("Close"),
        "volume": (
            numeric_list("Volume")
            if "Volume" in session.columns
            else [None] * len(session)
        ),
        "previous_close": previous_close,
        "session_open": session_open,
        "session_high": session_high,
        "session_low": session_low,
        "yahoo_last": yahoo_last,
        "session_date": latest_session_date.isoformat(),
        "session_start_iso": original_start.isoformat(),
        "replay_start_iso": effective_start.isoformat(),
        "replay_is_partial": replay_is_partial,
    }


# =============================================================================
# CONFIGURATION DU WORKSPACE
# =============================================================================

with st.sidebar:
    layout_name = st.selectbox(
        "Disposition",
        options=list(LAYOUTS.keys()),
        index=4,
    )

    layout_config = LAYOUTS[layout_name]
    panel_count = layout_config["count"]

    st.caption(
        "Chaque fenêtre choisit sa source et son timeframe. "
        "LSE : ticks ou bougies live. Yahoo : bougies intraday. "
        "Déplacer reste le mode par défaut."
    )

    panel_settings: list[dict[str, Any]] = []

    for panel_index in range(panel_count):
        default_market = DEFAULT_MARKETS[panel_index % len(DEFAULT_MARKETS)]
        if default_market not in AVAILABLE_MARKETS:
            default_market = AVAILABLE_MARKETS[0]

        with st.expander(
            f"Fenêtre {panel_index + 1}",
            expanded=panel_index < min(panel_count, 2),
        ):
            market = st.selectbox(
                "Marché",
                options=AVAILABLE_MARKETS,
                index=AVAILABLE_MARKETS.index(default_market),
                key=f"workspace_market_{panel_index}",
            )

            source = st.selectbox(
                "Source",
                options=["LSE", "Yahoo"],
                index=0 if panel_index < 3 else 1,
                key=f"workspace_source_{panel_index}",
                help=(
                    "LSE utilise le WebSocket : ticks ou bougies construites "
                    "en direct. Yahoo affiche des bougies historiques."
                ),
            )

            if source == "LSE":
                timeframe_label = st.selectbox(
                    "Timeframe LSE",
                    options=list(LSE_INTERVALS.keys()),
                    index=0,
                    key=f"workspace_lse_interval_{panel_index}",
                )
                timeframe_settings = LSE_INTERVALS[timeframe_label]
                bar_seconds = timeframe_settings["seconds"]
                chart_kind = timeframe_settings["chart_kind"]
                yahoo_interval_label = REFERENCE_YAHOO_INTERVAL
            else:
                timeframe_label = st.selectbox(
                    "Timeframe Yahoo",
                    options=list(YAHOO_INTERVALS.keys()),
                    index=2,
                    key=f"workspace_yahoo_interval_{panel_index}",
                )
                bar_seconds = None
                chart_kind = "candles"
                yahoo_interval_label = timeframe_label

            setup = st.selectbox(
                "Indicateurs",
                options=list(SETUPS.keys()),
                index=0,
                key=f"workspace_setup_{panel_index}",
            )

            panel_settings.append(
                {
                    "id": f"p{panel_index}",
                    "market": market,
                    "source": source,
                    "timeframe_label": timeframe_label,
                    "yahoo_interval_label": yahoo_interval_label,
                    "bar_seconds": bar_seconds,
                    "chart_kind": chart_kind,
                    "setup": setup,
                    "grid_area": layout_config["areas"][panel_index],
                }
            )

    st.divider()
    st.markdown(
        '<div class="small-note">'
        'Clique sur <b>Mode écran</b> pour masquer toute l’interface et ne garder que les graphiques. '
        'Déplace ensuite la fenêtre sur ton deuxième écran. Échap permet de quitter.'
        '</div>',
        unsafe_allow_html=True,
    )


# Charge une seule fois chaque combinaison marché / timeframe.
context_cache: dict[tuple[str, str], dict[str, Any]] = {}
loading_errors: list[str] = []

with st.spinner("Chargement du workspace…"):
    for panel in panel_settings:
        market = panel["market"]
        yahoo_interval_label = panel["yahoo_interval_label"]
        cache_key = (market, yahoo_interval_label)

        if cache_key in context_cache:
            continue

        interval_settings = YAHOO_INTERVALS[yahoo_interval_label]

        try:
            context_cache[cache_key] = load_yahoo_context(
                MARKETS[market]["yahoo"],
                interval_settings["interval"],
                interval_settings["period"],
            )
        except Exception as error:
            loading_errors.append(
                f"{market} ({panel['source']} · {panel['timeframe_label']}) : {error}"
            )
            context_cache[cache_key] = {
                "x": [],
                "open": [],
                "high": [],
                "low": [],
                "close": [],
                "volume": [],
                "previous_close": None,
                "session_open": None,
                "session_high": None,
                "session_low": None,
                "yahoo_last": None,
                "session_date": "—",
                "session_start_iso": (
                    datetime.now(timezone.utc) - timedelta(minutes=30)
                ).isoformat(),
                "replay_start_iso": (
                    datetime.now(timezone.utc) - timedelta(minutes=30)
                ).isoformat(),
                "replay_is_partial": False,
            }

panels_payload: list[dict[str, Any]] = []

for panel in panel_settings:
    market = panel["market"]
    yahoo_interval_label = panel["yahoo_interval_label"]

    panels_payload.append(
        {
            **panel,
            "symbol": LSE_SYMBOLS[market],
            "yahoo_symbol": MARKETS[market]["yahoo"],
            "context": context_cache[(market, yahoo_interval_label)],
            "overlays": SETUPS[panel["setup"]],
        }
    )


# =============================================================================
# COMPOSANT WORKSPACE
# =============================================================================

def render_workspace(
    api_key_value: str,
    layout: dict[str, Any],
    layout_label: str,
    panels: list[dict[str, Any]],
) -> None:
    payload = {
        "apiKey": api_key_value,
        "layoutLabel": layout_label,
        "layout": {
            "columns": layout["columns"],
            "rows": layout["rows"],
            "areas": layout["css_areas"],
        },
        "panels": panels,
    }

    html_template = r"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>

    <style>
        :root {
            color-scheme: dark;
        }

        html,
        body {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: #080c12;
            color: #d1d4dc;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
        }

        * {
            box-sizing: border-box;
        }

        button,
        select {
            font: inherit;
        }

        #workspace {
            width: 100%;
            height: 100vh;
            display: flex;
            flex-direction: column;
            background: #080c12;
        }

        #workspaceBar {
            min-height: 42px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 5px 8px;
            background: #101620;
            border-bottom: 1px solid #273142;
        }

        #brandBlock {
            min-width: 0;
            display: flex;
            align-items: baseline;
            gap: 10px;
        }

        #brand {
            color: #f4f7fb;
            font-size: 15px;
            font-weight: 730;
            letter-spacing: -0.02em;
            white-space: nowrap;
        }

        #workspaceMeta {
            color: #7f8b9c;
            font-size: 11px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        #workspaceActions {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .topButton,
        .chartButton {
            appearance: none;
            border: 1px solid #2b3647;
            background: #151d29;
            color: #abb6c6;
            border-radius: 5px;
            cursor: pointer;
            transition: 120ms ease;
        }

        .topButton {
            min-height: 28px;
            padding: 4px 9px;
            font-size: 11px;
        }

        .chartButton {
            min-height: 22px;
            padding: 2px 6px;
            font-size: 9px;
        }

        .topButton:hover,
        .chartButton:hover {
            background: #202a38;
            color: #f4f7fb;
            border-color: #3b4b61;
        }

        .chartButton.active {
            background: #23324a;
            color: #dce8ff;
            border-color: #456799;
        }

        #connectionStatus {
            color: #f0b90b;
            font-size: 11px;
            white-space: nowrap;
        }

        #grid {
            flex: 1;
            min-height: 0;
            display: grid;
            grid-template-columns: __GRID_COLUMNS__;
            grid-template-rows: __GRID_ROWS__;
            grid-template-areas: __GRID_AREAS__;
            gap: 5px;
            padding: 5px;
        }

        .panel {
            min-width: 0;
            min-height: 0;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            background: #0d121a;
            border: 1px solid #222d3c;
            border-radius: 6px;
        }

        .panel.maximized {
            position: fixed;
            inset: 0;
            z-index: 1000;
            border-radius: 0;
            border: 0;
            background: #080c12;
        }

        .panelHeader {
            min-height: 44px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 7px;
            padding: 4px 6px;
            background: #111823;
            border-bottom: 1px solid #222d3c;
        }

        .panelIdentity {
            min-width: 0;
            display: flex;
            flex-direction: column;
            gap: 1px;
        }

        .panelTitleLine {
            display: flex;
            align-items: baseline;
            gap: 6px;
            min-width: 0;
        }

        .panelTitle {
            color: #f2f5f9;
            font-size: 12px;
            font-weight: 700;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .panelPrice {
            color: #f4f7fb;
            font-size: 12px;
            font-weight: 650;
            white-space: nowrap;
        }

        .panelSubtitle {
            color: #778498;
            font-size: 9px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .panelControls {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 3px;
            flex-wrap: wrap;
        }

        .panelMetrics {
            min-height: 24px;
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 2px 7px;
            background: #0d141d;
            border-bottom: 1px solid #1d2734;
            color: #8592a5;
            font-size: 9px;
            white-space: nowrap;
            overflow: hidden;
        }

        .metricValue {
            color: #dce3ec;
            font-weight: 650;
        }

        .chart {
            flex: 1;
            min-height: 0;
            width: 100%;
        }

        #exitHotZone {
            display: none;
            position: fixed;
            top: 0;
            right: 0;
            width: 56px;
            height: 56px;
            z-index: 4000;
            align-items: flex-start;
            justify-content: flex-end;
            padding: 6px;
        }

        #exitScreenButton {
            width: 30px;
            height: 30px;
            border: 1px solid #334155;
            border-radius: 6px;
            background: rgba(15, 23, 42, 0.88);
            color: #e2e8f0;
            cursor: pointer;
            font-size: 18px;
            opacity: 0;
            transition: opacity 120ms ease;
        }

        #exitHotZone:hover #exitScreenButton {
            opacity: 1;
        }

        #workspace.immersive #workspaceBar,
        #workspace.immersive .panelHeader,
        #workspace.immersive .panelMetrics {
            display: none;
        }

        #workspace.immersive #grid {
            padding: 0;
            gap: 2px;
        }

        #workspace.immersive .panel {
            border-radius: 0;
            border-color: #151c27;
        }

        #workspace.immersive #exitHotZone {
            display: flex;
        }

        @media (max-width: 1050px) {
            .chartButton.axisButton {
                display: none;
            }

            #workspaceMeta {
                display: none;
            }
        }
    </style>
</head>

<body>
<div id="workspace">
    <div id="workspaceBar">
        <div id="brandBlock">
            <div id="brand">Flavio Monitor</div>
            <div id="workspaceMeta"></div>
        </div>

        <div id="workspaceActions">
            <div id="connectionStatus">Connexion…</div>
            <button class="topButton" onclick="enterScreenMode()">Mode écran</button>
        </div>
    </div>

    <div id="grid"></div>

    <div id="exitHotZone">
        <button id="exitScreenButton" onclick="exitScreenMode()" title="Quitter le mode écran (Échap)">×</button>
    </div>
</div>

<script>
const SETTINGS = __SETTINGS__;
const API_KEY = SETTINGS.apiKey;
const PANELS = SETTINGS.panels;

const MAX_POINTS = 5000;
const FLUSH_INTERVAL_MS = 220;
const ROLLING_WINDOW_MS = 15 * 60 * 1000;

const grid = document.getElementById("grid");
const connectionStatus = document.getElementById("connectionStatus");
const workspaceMeta = document.getElementById("workspaceMeta");

workspaceMeta.textContent = SETTINGS.layoutLabel + " · " + PANELS.length + " fenêtre(s)";

const panelRuntime = {};
const symbolStates = {};
let socket = null;
let reconnectTimer = null;


function isFiniteNumber(value) {
    return value !== null
        && value !== undefined
        && Number.isFinite(Number(value));
}


function formatPrice(value) {
    if (!isFiniteNumber(value)) {
        return "—";
    }

    const number = Number(value);
    const absolute = Math.abs(number);

    if (absolute >= 1000) {
        return number.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    if (absolute >= 10) {
        return number.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 3
        });
    }

    return number.toLocaleString(undefined, {
        minimumFractionDigits: 4,
        maximumFractionDigits: 5
    });
}


function formatSignedPercent(value) {
    if (!isFiniteNumber(value)) {
        return "—";
    }

    const number = Number(value);
    return (number >= 0 ? "+" : "") + number.toFixed(2) + "%";
}


function parseTimestamp(value) {
    if (typeof value === "number") {
        return new Date(value < 1e12 ? value * 1000 : value);
    }

    const numericValue = Number(value);

    if (
        value !== null
        && value !== ""
        && Number.isFinite(numericValue)
    ) {
        return new Date(numericValue < 1e12 ? numericValue * 1000 : numericValue);
    }

    return new Date(value);
}


function setDirectionalColor(element, value) {
    if (!isFiniteNumber(value)) {
        element.style.color = "#dce3ec";
    } else if (Number(value) > 0) {
        element.style.color = "#26a69a";
    } else if (Number(value) < 0) {
        element.style.color = "#ef5350";
    } else {
        element.style.color = "#dce3ec";
    }
}


function makeSymbolState(symbol) {
    if (symbolStates[symbol]) {
        return symbolStates[symbol];
    }

    symbolStates[symbol] = {
        symbol: symbol,
        totalTicks: 0,
        positiveVolumeTicks: 0,
        cumulativeVolume: 0,
        cumulativePriceVolume: 0,
        cumulativePriceSquaredVolume: 0,
        firstPrice: null,
        latestTick: null,
        latestPrice: null,
        rollingTicks: [],
        seenKeys: new Set(),
        seenQueue: [],
        pending: {
            x: [],
            price: [],
            mid: [],
            vwap: [],
            upper: [],
            lower: [],
            ticks: []
        }
    };

    return symbolStates[symbol];
}


function calculateSessionVwap(state) {
    if (state.cumulativeVolume <= 0) {
        return null;
    }

    return state.cumulativePriceVolume / state.cumulativeVolume;
}


function calculateSessionSigma(state, vwap) {
    if (!isFiniteNumber(vwap) || state.cumulativeVolume <= 0) {
        return null;
    }

    const variance = Math.max(
        0,
        state.cumulativePriceSquaredVolume / state.cumulativeVolume
        - Number(vwap) * Number(vwap)
    );

    return Math.sqrt(variance);
}


function purgeRollingTicks(state, currentTimeMs) {
    const cutoff = currentTimeMs - ROLLING_WINDOW_MS;

    while (
        state.rollingTicks.length > 0
        && state.rollingTicks[0].timestampMs < cutoff
    ) {
        state.rollingTicks.shift();
    }
}


function getDayPerformance(panel, currentPrice) {
    const previousClose = panel.context.previous_close;

    if (!isFiniteNumber(previousClose) || !isFiniteNumber(currentPrice)) {
        return null;
    }

    return (Number(currentPrice) / Number(previousClose) - 1) * 100;
}


function getOpenPerformance(panel, state, currentPrice) {
    const reference = state.firstPrice !== null
        ? state.firstPrice
        : panel.context.session_open;

    if (!isFiniteNumber(reference) || !isFiniteNumber(currentPrice)) {
        return null;
    }

    return (Number(currentPrice) / Number(reference) - 1) * 100;
}


function buildPanel(panel) {
    const wrapper = document.createElement("section");
    wrapper.className = "panel";
    wrapper.id = "panel-" + panel.id;
    wrapper.style.gridArea = panel.grid_area;

    wrapper.innerHTML = `
        <div class="panelHeader">
            <div class="panelIdentity">
                <div class="panelTitleLine">
                    <span class="panelTitle">${panel.market}</span>
                    <span class="panelPrice" id="price-${panel.id}">—</span>
                </div>
                <div class="panelSubtitle">${panel.source === "LSE" ? panel.symbol : panel.yahoo_symbol} · ${panel.source} · ${panel.timeframe_label} · ${panel.setup}</div>
            </div>

            <div class="panelControls">
                <button class="chartButton active" id="pan-${panel.id}" onclick="setDragMode('${panel.id}', 'pan')">Déplacer</button>
                <button class="chartButton" id="zoom-${panel.id}" onclick="setDragMode('${panel.id}', 'zoom')">Zone</button>
                <button class="chartButton axisButton" onclick="zoomAxis('${panel.id}', 'x', 0.66)">Temps +</button>
                <button class="chartButton axisButton" onclick="zoomAxis('${panel.id}', 'x', 1.52)">Temps −</button>
                <button class="chartButton axisButton" onclick="zoomAxis('${panel.id}', 'y', 0.66)">Prix +</button>
                <button class="chartButton axisButton" onclick="zoomAxis('${panel.id}', 'y', 1.52)">Prix −</button>
                <button class="chartButton" onclick="resetChart('${panel.id}')">Reset</button>
                <button class="chartButton" onclick="togglePanelMaximize('${panel.id}')">Agrandir</button>
            </div>
        </div>

        <div class="panelMetrics">
            <span>Jour <span class="metricValue" id="day-${panel.id}">—</span></span>
            <span>Open <span class="metricValue" id="open-${panel.id}">—</span></span>
            <span>VWAP <span class="metricValue" id="vwap-${panel.id}">—</span></span>
            <span>Spread <span class="metricValue" id="spread-${panel.id}">—</span></span>
            <span id="status-${panel.id}">En attente…</span>
        </div>

        <div class="chart" id="chart-${panel.id}"></div>
    `;

    grid.appendChild(wrapper);

    const chart = document.getElementById("chart-" + panel.id);

    panelRuntime[panel.id] = {
        panel: panel,
        wrapper: wrapper,
        chart: chart,
        userInteracted: false,
        sourceAligned: null
    };

    if (panel.source === "Yahoo") {
        createYahooCandleChart(panel, chart);
        initializeYahooMetrics(panel);
    } else if (panel.chart_kind === "ticks") {
        createLseTickChart(panel, chart);
    } else {
        createLseCandleChart(panel, chart);
    }

    chart.on("plotly_relayout", function(eventData) {
        if (
            eventData["xaxis.range[0]"] !== undefined
            || eventData["xaxis.range[1]"] !== undefined
            || eventData["yaxis.range[0]"] !== undefined
            || eventData["yaxis.range[1]"] !== undefined
        ) {
            panelRuntime[panel.id].userInteracted = true;
        }
    });
}


function commonLayout(panel) {
    return {
        template: "plotly_dark",
        paper_bgcolor: "#0d121a",
        plot_bgcolor: "#0d121a",
        margin: {
            l: 7,
            r: 68,
            t: 8,
            b: 27
        },
        title: {
            text: "",
            x: 0.012,
            font: {color: "#e5eaf1", size: 12}
        },
        showlegend: false,
        hovermode: "x unified",
        dragmode: "pan",
        uirevision: "workspace-" + panel.id,
        xaxis: {
            gridcolor: "#1d2734",
            zeroline: false,
            showspikes: true,
            spikecolor: "#718096",
            rangeslider: {visible: false},
            tickfont: {color: "#9aa7b8", size: 9}
        },
        yaxis: {
            gridcolor: "#1d2734",
            zeroline: false,
            side: "right",
            automargin: true,
            showticklabels: true,
            separatethousands: true,
            ticks: "outside",
            ticklen: 3,
            tickcolor: "#718096",
            showline: true,
            linecolor: "#344154",
            tickfont: {color: "#aab5c4", size: 9}
        }
    };
}


const plotConfig = {
    responsive: true,
    displaylogo: false,
    displayModeBar: false,
    scrollZoom: true,
    doubleClick: "reset+autosize"
};


function createLseTickChart(panel, chart) {
    const showMid = panel.overlays.includes("Mid-price");
    const showVwap = panel.overlays.includes("VWAP séance");
    const showBands = panel.overlays.includes("Bandes VWAP");

    const traces = [
        {
            x: [],
            y: [],
            type: "scattergl",
            mode: "lines",
            name: "Prix",
            line: {color: "#f4f7fb", width: 1.7},
            hovertemplate: "%{x|%H:%M:%S.%L}<br>Prix : %{y:,.5f}<extra></extra>"
        },
        {
            x: [],
            y: [],
            type: "scattergl",
            mode: "lines",
            name: "Mid",
            visible: showMid ? true : "legendonly",
            line: {color: "#8b5cf6", width: 1, dash: "dot"},
            hovertemplate: "%{x|%H:%M:%S.%L}<br>Mid : %{y:,.5f}<extra></extra>"
        },
        {
            x: [],
            y: [],
            type: "scattergl",
            mode: "lines",
            name: "VWAP",
            visible: showVwap ? true : "legendonly",
            line: {color: "#f59e0b", width: 1.5},
            hovertemplate: "%{x|%H:%M:%S.%L}<br>VWAP : %{y:,.5f}<extra></extra>"
        },
        {
            x: [],
            y: [],
            type: "scattergl",
            mode: "lines",
            name: "VWAP +1σ",
            visible: showBands ? true : "legendonly",
            line: {color: "#f59e0b", width: 0.8, dash: "dash"},
            hoverinfo: "skip"
        },
        {
            x: [],
            y: [],
            type: "scattergl",
            mode: "lines",
            name: "VWAP -1σ",
            visible: showBands ? true : "legendonly",
            fill: showBands ? "tonexty" : "none",
            fillcolor: "rgba(245,158,11,0.07)",
            line: {color: "#f59e0b", width: 0.8, dash: "dash"},
            hoverinfo: "skip"
        }
    ];

    Plotly.newPlot(chart, traces, commonLayout(panel), plotConfig);
}


function createYahooCandleChart(panel, chart) {
    const context = panel.context;

    const trace = {
        x: context.x,
        open: context.open,
        high: context.high,
        low: context.low,
        close: context.close,
        type: "candlestick",
        name: panel.market,
        increasing: {
            line: {color: "#26a69a"},
            fillcolor: "#26a69a"
        },
        decreasing: {
            line: {color: "#ef5350"},
            fillcolor: "#ef5350"
        }
    };

    Plotly.newPlot(chart, [trace], commonLayout(panel), plotConfig);
}


function createLseCandleChart(panel, chart) {
    const showVwap = panel.overlays.includes("VWAP séance");
    const showBands = panel.overlays.includes("Bandes VWAP");

    const traces = [
        {
            x: [],
            open: [],
            high: [],
            low: [],
            close: [],
            type: "candlestick",
            name: panel.market,
            increasing: {
                line: {color: "#26a69a"},
                fillcolor: "#26a69a"
            },
            decreasing: {
                line: {color: "#ef5350"},
                fillcolor: "#ef5350"
            }
        },
        {
            x: [],
            y: [],
            type: "scattergl",
            mode: "lines",
            name: "VWAP",
            visible: showVwap ? true : "legendonly",
            line: {color: "#f59e0b", width: 1.4},
            hovertemplate: "%{x|%H:%M:%S}<br>VWAP : %{y:,.5f}<extra></extra>"
        },
        {
            x: [],
            y: [],
            type: "scattergl",
            mode: "lines",
            name: "VWAP +1σ",
            visible: showBands ? true : "legendonly",
            line: {color: "#f59e0b", width: 0.8, dash: "dash"},
            hoverinfo: "skip"
        },
        {
            x: [],
            y: [],
            type: "scattergl",
            mode: "lines",
            name: "VWAP -1σ",
            visible: showBands ? true : "legendonly",
            fill: showBands ? "tonexty" : "none",
            fillcolor: "rgba(245,158,11,0.07)",
            line: {color: "#f59e0b", width: 0.8, dash: "dash"},
            hoverinfo: "skip"
        }
    ];

    panelRuntime[panel.id].barState = {
        currentBucket: null
    };

    Plotly.newPlot(chart, traces, commonLayout(panel), plotConfig);
}


function initializeYahooMetrics(panel) {
    const context = panel.context;
    const latest = context.close.length > 0
        ? Number(context.close[context.close.length - 1])
        : null;

    const previousClose = context.previous_close;
    const sessionOpen = context.session_open;

    const dayPerformance = (
        isFiniteNumber(latest)
        && isFiniteNumber(previousClose)
        && Number(previousClose) !== 0
    )
        ? (latest / Number(previousClose) - 1) * 100
        : null;

    const openPerformance = (
        isFiniteNumber(latest)
        && isFiniteNumber(sessionOpen)
        && Number(sessionOpen) !== 0
    )
        ? (latest / Number(sessionOpen) - 1) * 100
        : null;

    const priceElement = document.getElementById("price-" + panel.id);
    const dayElement = document.getElementById("day-" + panel.id);
    const openElement = document.getElementById("open-" + panel.id);
    const vwapElement = document.getElementById("vwap-" + panel.id);
    const spreadElement = document.getElementById("spread-" + panel.id);
    const statusElement = document.getElementById("status-" + panel.id);

    priceElement.textContent = formatPrice(latest);
    setDirectionalColor(priceElement, openPerformance);

    dayElement.textContent = formatSignedPercent(dayPerformance);
    setDirectionalColor(dayElement, dayPerformance);

    openElement.textContent = formatSignedPercent(openPerformance);
    setDirectionalColor(openElement, openPerformance);

    vwapElement.textContent = "—";
    spreadElement.textContent = "—";
    statusElement.textContent = "Yahoo · " + context.session_date;
    statusElement.style.color = "#94a3b8";
}


function setDragMode(panelId, mode) {
    const runtime = panelRuntime[panelId];
    Plotly.relayout(runtime.chart, {dragmode: mode});

    document.getElementById("pan-" + panelId).classList.toggle("active", mode === "pan");
    document.getElementById("zoom-" + panelId).classList.toggle("active", mode === "zoom");
}


function zoomAxis(panelId, axisName, factor) {
    const runtime = panelRuntime[panelId];
    const chart = runtime.chart;
    const axis = axisName === "x"
        ? chart._fullLayout.xaxis
        : chart._fullLayout.yaxis;

    if (!axis || !axis.range || axis.range.length !== 2) {
        return;
    }

    if (axisName === "x") {
        const start = new Date(axis.range[0]).getTime();
        const end = new Date(axis.range[1]).getTime();

        if (!Number.isFinite(start) || !Number.isFinite(end)) {
            return;
        }

        const center = (start + end) / 2;
        const half = (end - start) * factor / 2;

        Plotly.relayout(chart, {
            "xaxis.autorange": false,
            "xaxis.range": [
                new Date(center - half),
                new Date(center + half)
            ]
        });
    } else {
        const start = Number(axis.range[0]);
        const end = Number(axis.range[1]);

        if (!Number.isFinite(start) || !Number.isFinite(end)) {
            return;
        }

        const center = (start + end) / 2;
        const half = (end - start) * factor / 2;

        Plotly.relayout(chart, {
            "yaxis.autorange": false,
            "yaxis.range": [center - half, center + half]
        });
    }

    runtime.userInteracted = true;
}


function resetChart(panelId) {
    const runtime = panelRuntime[panelId];
    runtime.userInteracted = false;

    Plotly.relayout(runtime.chart, {
        "xaxis.autorange": true,
        "yaxis.autorange": true,
        dragmode: "pan"
    });

    setDragMode(panelId, "pan");
}


function togglePanelMaximize(panelId) {
    const runtime = panelRuntime[panelId];
    runtime.wrapper.classList.toggle("maximized");

    setTimeout(function() {
        Plotly.Plots.resize(runtime.chart);
    }, 80);
}


function setImmersiveChartTitles(enabled) {
    for (const runtime of Object.values(panelRuntime)) {
        const panel = runtime.panel;
        const titleText = enabled
            ? panel.market
                + " · "
                + panel.source
                + " · "
                + panel.timeframe_label
            : "";

        Plotly.relayout(runtime.chart, {
            "title.text": titleText,
            "margin.t": enabled ? 30 : 8
        });
    }
}


async function enterScreenMode() {
    const workspace = document.getElementById("workspace");
    workspace.classList.add("immersive");
    setImmersiveChartTitles(true);

    try {
        if (!document.fullscreenElement) {
            await workspace.requestFullscreen();
        }
    } catch (error) {
        connectionStatus.textContent = "Mode écran actif dans la page · F11 pour masquer le navigateur";
        connectionStatus.style.color = "#f0b90b";
    }

    setTimeout(resizeAllCharts, 140);
}


async function exitScreenMode() {
    const workspace = document.getElementById("workspace");

    try {
        if (document.fullscreenElement) {
            await document.exitFullscreen();
        }
    } catch (error) {
        // Le retrait de la classe suffit si le navigateur bloque l'API.
    }

    workspace.classList.remove("immersive");
    setImmersiveChartTitles(false);
    setTimeout(resizeAllCharts, 140);
}


function resizeAllCharts() {
    for (const runtime of Object.values(panelRuntime)) {
        Plotly.Plots.resize(runtime.chart);
    }
}


function updatePanelMetrics(panel, state) {
    const priceElement = document.getElementById("price-" + panel.id);
    const dayElement = document.getElementById("day-" + panel.id);
    const openElement = document.getElementById("open-" + panel.id);
    const vwapElement = document.getElementById("vwap-" + panel.id);
    const spreadElement = document.getElementById("spread-" + panel.id);
    const statusElement = document.getElementById("status-" + panel.id);

    const price = state.latestPrice;
    const vwap = calculateSessionVwap(state);
    const dayPerformance = getDayPerformance(panel, price);
    const openPerformance = getOpenPerformance(panel, state, price);

    priceElement.textContent = formatPrice(price);
    setDirectionalColor(priceElement, openPerformance);

    dayElement.textContent = formatSignedPercent(dayPerformance);
    setDirectionalColor(dayElement, dayPerformance);

    openElement.textContent = formatSignedPercent(openPerformance);
    setDirectionalColor(openElement, openPerformance);

    vwapElement.textContent = formatPrice(vwap);
    if (isFiniteNumber(vwap)) {
        setDirectionalColor(vwapElement, price - vwap);
    }

    const tick = state.latestTick;
    if (
        tick
        && isFiniteNumber(tick.bid)
        && isFiniteNumber(tick.ask)
        && Number(tick.ask) >= Number(tick.bid)
    ) {
        const spread = Number(tick.ask) - Number(tick.bid);
        spreadElement.textContent = formatPrice(spread);
    } else {
        spreadElement.textContent = "—";
    }

    if (tick) {
        const tickDate = parseTimestamp(tick.ts ?? tick.timestamp);
        statusElement.textContent = (tick.replay ? "Replay" : "Live")
            + " · "
            + tickDate.toLocaleTimeString([], {hour12: false});
        statusElement.style.color = tick.replay ? "#f0b90b" : "#26a69a";
    }
}


function buildReferenceShapes(panel, state) {
    const shapes = [];
    const annotations = [];
    const context = panel.context;

    if (panel.overlays.includes("Clôture veille") && isFiniteNumber(context.previous_close)) {
        shapes.push({
            type: "line",
            xref: "paper",
            x0: 0,
            x1: 1,
            yref: "y",
            y0: Number(context.previous_close),
            y1: Number(context.previous_close),
            line: {color: "#64748b", width: 0.8, dash: "dash"}
        });
    }

    const openingValue = state.firstPrice !== null
        ? state.firstPrice
        : context.session_open;

    if (panel.overlays.includes("Ouverture") && isFiniteNumber(openingValue)) {
        shapes.push({
            type: "line",
            xref: "paper",
            x0: 0,
            x1: 1,
            yref: "y",
            y0: Number(openingValue),
            y1: Number(openingValue),
            line: {color: "#38bdf8", width: 0.8, dash: "dash"}
        });
    }

    if (isFiniteNumber(state.latestPrice)) {
        const lineColor = state.firstPrice !== null && state.latestPrice >= state.firstPrice
            ? "#26a69a"
            : "#ef5350";

        shapes.push({
            type: "line",
            xref: "paper",
            x0: 0,
            x1: 1,
            yref: "y",
            y0: state.latestPrice,
            y1: state.latestPrice,
            line: {color: lineColor, width: 0.8, dash: "dot"}
        });

        annotations.push({
            xref: "paper",
            x: 1.006,
            xanchor: "left",
            yref: "y",
            y: state.latestPrice,
            yanchor: "middle",
            text: formatPrice(state.latestPrice),
            showarrow: false,
            bgcolor: lineColor,
            bordercolor: lineColor,
            borderpad: 2,
            font: {color: "#ffffff", size: 9}
        });
    }

    return {shapes: shapes, annotations: annotations};
}


function updateLseCandlePanel(panel, state, batch) {
    const runtime = panelRuntime[panel.id];
    const chart = runtime.chart;
    const barSeconds = Number(panel.bar_seconds);

    if (!Number.isFinite(barSeconds) || barSeconds <= 0) {
        return;
    }

    for (const tick of batch.ticks) {
        const bucketMs = Math.floor(
            tick.date.getTime() / (barSeconds * 1000)
        ) * barSeconds * 1000;

        const data = chart.data[0];
        const lastIndex = data.x.length - 1;
        const lastBucket = lastIndex >= 0
            ? new Date(data.x[lastIndex]).getTime()
            : null;

        if (lastBucket !== bucketMs) {
            data.x.push(new Date(bucketMs));
            data.open.push(tick.price);
            data.high.push(tick.price);
            data.low.push(tick.price);
            data.close.push(tick.price);

            chart.data[1].x.push(new Date(bucketMs));
            chart.data[1].y.push(tick.vwap);
            chart.data[2].x.push(new Date(bucketMs));
            chart.data[2].y.push(tick.upper);
            chart.data[3].x.push(new Date(bucketMs));
            chart.data[3].y.push(tick.lower);
        } else {
            data.high[lastIndex] = Math.max(data.high[lastIndex], tick.price);
            data.low[lastIndex] = Math.min(data.low[lastIndex], tick.price);
            data.close[lastIndex] = tick.price;

            chart.data[1].y[lastIndex] = tick.vwap;
            chart.data[2].y[lastIndex] = tick.upper;
            chart.data[3].y[lastIndex] = tick.lower;
        }
    }

    const maximumBars = 2500;

    if (chart.data[0].x.length > maximumBars) {
        const removeCount = chart.data[0].x.length - maximumBars;

        for (const trace of chart.data) {
            if (Array.isArray(trace.x)) {
                trace.x.splice(0, removeCount);
            }

            for (const key of ["open", "high", "low", "close", "y"]) {
                if (Array.isArray(trace[key])) {
                    trace[key].splice(0, removeCount);
                }
            }
        }
    }

    Plotly.redraw(chart);
}


function updatePanelChart(panel, state, batch) {
    const runtime = panelRuntime[panel.id];
    const chart = runtime.chart;

    if (panel.source !== "LSE") {
        return;
    }

    if (panel.chart_kind === "ticks" && batch.x.length > 0) {
        Plotly.extendTraces(
            chart,
            {
                x: [batch.x, batch.x, batch.x, batch.x, batch.x],
                y: [batch.price, batch.mid, batch.vwap, batch.upper, batch.lower]
            },
            [0, 1, 2, 3, 4],
            MAX_POINTS
        );
    } else if (panel.chart_kind === "candles" && batch.ticks.length > 0) {
        updateLseCandlePanel(panel, state, batch);
    }

    const references = buildReferenceShapes(panel, state);

    Plotly.relayout(chart, {
        shapes: references.shapes,
        annotations: references.annotations
    });

    updatePanelMetrics(panel, state);
}


function processTick(message) {
    const state = makeSymbolState(message.symbol);
    const tickDate = parseTimestamp(message.ts ?? message.timestamp);
    const price = Number(message.price);

    if (Number.isNaN(tickDate.getTime()) || !Number.isFinite(price)) {
        return;
    }

    const volume = isFiniteNumber(message.volume) && Number(message.volume) > 0
        ? Number(message.volume)
        : 0;

    const dedupeKey = [
        tickDate.getTime(),
        price,
        volume,
        message.bid ?? "",
        message.ask ?? ""
    ].join("|");

    if (state.seenKeys.has(dedupeKey)) {
        return;
    }

    state.seenKeys.add(dedupeKey);
    state.seenQueue.push(dedupeKey);

    if (state.seenQueue.length > 15000) {
        const removed = state.seenQueue.shift();
        state.seenKeys.delete(removed);
    }

    state.totalTicks += 1;
    state.latestTick = message;
    state.latestPrice = price;

    if (state.firstPrice === null) {
        state.firstPrice = price;
    }

    const bid = isFiniteNumber(message.bid) ? Number(message.bid) : null;
    const ask = isFiniteNumber(message.ask) ? Number(message.ask) : null;
    const mid = bid !== null && ask !== null && ask >= bid
        ? (bid + ask) / 2
        : null;

    if (volume > 0) {
        state.positiveVolumeTicks += 1;
        state.cumulativeVolume += volume;
        state.cumulativePriceVolume += price * volume;
        state.cumulativePriceSquaredVolume += price * price * volume;
    }

    state.rollingTicks.push({
        timestampMs: tickDate.getTime(),
        price: price,
        volume: volume
    });
    purgeRollingTicks(state, tickDate.getTime());

    const vwap = calculateSessionVwap(state);
    const sigma = calculateSessionSigma(state, vwap);

    state.pending.x.push(tickDate);
    state.pending.price.push(price);
    state.pending.mid.push(mid);
    state.pending.vwap.push(vwap);
    state.pending.upper.push(vwap !== null && sigma !== null ? vwap + sigma : null);
    state.pending.lower.push(vwap !== null && sigma !== null ? vwap - sigma : null);
    state.pending.ticks.push({
        date: tickDate,
        price: price,
        vwap: vwap,
        upper: vwap !== null && sigma !== null ? vwap + sigma : null,
        lower: vwap !== null && sigma !== null ? vwap - sigma : null
    });
}


function flushAll() {
    for (const state of Object.values(symbolStates)) {
        const batch = state.pending;

        if (batch.x.length === 0 && state.latestPrice === null) {
            continue;
        }

        for (const panel of PANELS) {
            if (
                panel.source === "LSE"
                && panel.symbol === state.symbol
            ) {
                updatePanelChart(panel, state, batch);
            }
        }

        state.pending = {
            x: [],
            price: [],
            mid: [],
            vwap: [],
            upper: [],
            lower: [],
            ticks: []
        };
    }
}


setInterval(flushAll, FLUSH_INTERVAL_MS);


function buildSubscriptions() {
    const subscriptions = {};

    for (const panel of PANELS) {
        if (panel.source !== "LSE") {
            continue;
        }

        const existing = subscriptions[panel.symbol];
        const candidate = new Date(panel.context.replay_start_iso).getTime();

        if (!existing || candidate < new Date(existing).getTime()) {
            subscriptions[panel.symbol] = panel.context.replay_start_iso;
        }
    }

    return subscriptions;
}


function connect() {
    clearTimeout(reconnectTimer);

    connectionStatus.textContent = "Connexion…";
    connectionStatus.style.color = "#f0b90b";

    socket = new WebSocket("wss://data-ws.londonstrategicedge.com");

    socket.onmessage = function(event) {
        const message = JSON.parse(event.data);

        if (message.type === "welcome") {
            socket.send(JSON.stringify({
                action: "auth",
                api_key: API_KEY
            }));
            return;
        }

        if (message.type === "authenticated") {
            const subscriptions = buildSubscriptions();

            for (const [symbol, start] of Object.entries(subscriptions)) {
                makeSymbolState(symbol);

                socket.send(JSON.stringify({
                    action: "subscribe",
                    symbol: symbol,
                    start: start
                }));
            }

            connectionStatus.textContent = "Reconstruction des séances…";
            return;
        }

        if (message.type === "replay_complete") {
            connectionStatus.textContent = "Flux live";
            connectionStatus.style.color = "#26a69a";
            return;
        }

        if (message.type === "tick") {
            processTick(message);
            return;
        }

        if (message.type === "error") {
            connectionStatus.textContent = "Erreur : " + (message.message || message.code || "inconnue");
            connectionStatus.style.color = "#ef5350";
        }
    };

    socket.onerror = function() {
        connectionStatus.textContent = "Erreur de connexion";
        connectionStatus.style.color = "#ef5350";
    };

    socket.onclose = function() {
        connectionStatus.textContent = "Reconnexion…";
        connectionStatus.style.color = "#f0b90b";
        reconnectTimer = setTimeout(connect, 2500);
    };
}


for (const panel of PANELS) {
    buildPanel(panel);
}

if (PANELS.some(panel => panel.source === "LSE")) {
    connect();
} else {
    connectionStatus.textContent = "Yahoo uniquement";
    connectionStatus.style.color = "#94a3b8";
}

window.addEventListener("resize", resizeAllCharts);

document.addEventListener("keydown", function(event) {
    if (event.key === "Escape") {
        const workspace = document.getElementById("workspace");

        if (workspace.classList.contains("immersive")) {
            exitScreenMode();
        }
    }
});

document.addEventListener("fullscreenchange", function() {
    const workspace = document.getElementById("workspace");

    if (!document.fullscreenElement) {
        workspace.classList.remove("immersive");
        setImmersiveChartTitles(false);
    }

    setTimeout(resizeAllCharts, 120);
});

window.addEventListener("beforeunload", function() {
    if (socket) {
        socket.close();
    }
});
</script>
</body>
</html>
"""

    html = (
        html_template
        .replace("__SETTINGS__", json.dumps(payload))
        .replace("__GRID_COLUMNS__", layout["columns"])
        .replace("__GRID_ROWS__", layout["rows"])
        .replace("__GRID_AREAS__", layout["css_areas"])
    )

    components.html(
        html,
        height=layout["height"],
        scrolling=False,
    )


# =============================================================================
# PAGE
# =============================================================================

st.markdown(
    '<div class="workspace-title">Flavio Monitor — Workspace V5.1</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="workspace-subtitle">'
    'Sources indépendantes LSE / Yahoo · Timeframes adaptés · Mode écran immersif'
    '</div>',
    unsafe_allow_html=True,
)

if UNRESOLVED_MARKETS:
    st.warning(
        "Marchés non trouvés dans le catalogue LSE : "
        + ", ".join(UNRESOLVED_MARKETS)
    )

if loading_errors:
    with st.expander("Certaines données Yahoo n’ont pas pu être chargées"):
        for error in loading_errors:
            st.write(error)

render_workspace(
    api_key_value=api_key,
    layout=layout_config,
    layout_label=layout_name,
    panels=panels_payload,
)

'''

BUREAU_LARBOU_SOURCE = r'''
from __future__ import annotations

from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlencode
import re

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf


# =============================================================================
# PAGE
# =============================================================================


st.markdown(
    """
    <style>
        .stApp {
            background: #0b0f15;
        }

        [data-testid="stSidebar"] {
            background: #101620;
            border-right: 1px solid #202938;
        }

        .block-container {
            max-width: 100%;
            padding-top: 0.9rem;
            padding-left: 1.1rem;
            padding-right: 1.1rem;
            padding-bottom: 2rem;
        }

        #MainMenu,
        footer {
            visibility: hidden;
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        .bureau-title {
            color: #f4f7fb;
            font-size: 2rem;
            font-weight: 740;
            letter-spacing: -0.04em;
            margin: 0;
        }

        .bureau-subtitle {
            color: #8490a3;
            font-size: 0.92rem;
            margin-top: 0.15rem;
            margin-bottom: 1rem;
        }

        .section-label {
            color: #f4f7fb;
            font-size: 1.15rem;
            font-weight: 680;
            margin-top: 0.4rem;
            margin-bottom: 0.35rem;
        }

        [data-testid="stMetric"] {
            background: #151b26;
            border: 1px solid #273142;
            border-radius: 10px;
            padding: 11px 13px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="bureau-title">Bureau Larbou</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="bureau-subtitle">'
    'Performance multi-horizons · Market movers · Calendrier macro'
    '</div>',
    unsafe_allow_html=True,
)


# =============================================================================
# HELPERS
# =============================================================================

INDEX_SYMBOLS = {
    "CAC 40": "^FCHI",
    "S&P 500": "^GSPC",
}

WIKIPEDIA_URLS = {
    "CAC 40": "https://en.wikipedia.org/wiki/CAC_40",
    "S&P 500": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
}

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124 Safari/537.36"
    )
}


def extract_close_frame(
    downloaded: pd.DataFrame,
    requested_symbols: list[str],
) -> pd.DataFrame:
    if downloaded.empty:
        return pd.DataFrame()

    if isinstance(downloaded.columns, pd.MultiIndex):
        level_zero = set(
            str(value)
            for value in downloaded.columns.get_level_values(0)
        )
        level_one = set(
            str(value)
            for value in downloaded.columns.get_level_values(1)
        )

        if "Close" in level_zero:
            close = downloaded["Close"].copy()
        elif "Close" in level_one:
            close = downloaded.xs(
                "Close",
                axis=1,
                level=1,
            ).copy()
        else:
            return pd.DataFrame()

        if isinstance(close, pd.Series):
            close = close.to_frame(
                name=requested_symbols[0]
            )

        return close

    if "Close" not in downloaded.columns:
        return pd.DataFrame()

    symbol = (
        requested_symbols[0]
        if requested_symbols
        else "Close"
    )

    return downloaded[["Close"]].rename(
        columns={"Close": symbol}
    )


def signed_percent(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:+.2f}%"


def style_performance_table(
    dataframe: pd.DataFrame,
) -> pd.io.formats.style.Styler:
    def color_value(value: Any) -> str:
        if pd.isna(value):
            return "color: #8490a3;"
        if float(value) > 0:
            return (
                "color: #26a69a; "
                "background-color: rgba(38,166,154,0.08);"
            )
        if float(value) < 0:
            return (
                "color: #ef5350; "
                "background-color: rgba(239,83,80,0.08);"
            )
        return "color: #d1d4dc;"

    return (
        dataframe.style
        .map(color_value)
        .format(lambda value: "—" if pd.isna(value) else f"{value:+.2f}%")
    )


# =============================================================================
# INDEX PERFORMANCE
# =============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def load_index_performance() -> tuple[pd.DataFrame, pd.DataFrame]:
    symbols = list(INDEX_SYMBOLS.values())

    downloaded = yf.download(
        tickers=symbols,
        period="3mo",
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=True,
        group_by="column",
    )

    close = extract_close_frame(
        downloaded,
        symbols,
    )

    if close.empty:
        raise ValueError(
            "Yahoo n’a retourné aucune clôture pour le CAC 40 et le S&P 500."
        )

    reverse_names = {
        symbol: name
        for name, symbol in INDEX_SYMBOLS.items()
    }

    close = close.rename(
        columns={
            column: reverse_names.get(
                str(column),
                str(column),
            )
            for column in close.columns
        }
    )

    close = close.sort_index().dropna(how="all")

    horizon_values: dict[str, dict[str, float | None]] = {}

    for index_name in INDEX_SYMBOLS:
        if index_name not in close.columns:
            horizon_values[index_name] = {
                f"{day}j": None
                for day in range(1, 22)
            }
            continue

        series = close[index_name].dropna()
        current = (
            float(series.iloc[-1])
            if not series.empty
            else None
        )

        row: dict[str, float | None] = {}

        for day in range(1, 22):
            if current is None or len(series) <= day:
                row[f"{day}j"] = None
            else:
                reference = float(
                    series.iloc[-(day + 1)]
                )
                row[f"{day}j"] = (
                    current / reference - 1
                ) * 100

        horizon_values[index_name] = row

    performance = pd.DataFrame.from_dict(
        horizon_values,
        orient="index",
    )

    return performance, close


with st.sidebar:
    st.markdown("### Bureau Larbou")

    if st.button(
        "Actualiser les données",
        use_container_width=True,
    ):
        st.cache_data.clear()
        st.rerun()

    st.caption(
        "Les horizons sont calculés en séances de bourse : "
        "21j correspond approximativement à un mois."
    )


try:
    performance_table, index_closes = load_index_performance()
except Exception as error:
    st.error(f"Performance indices : {error}")
    st.stop()


st.markdown(
    '<div class="section-label">CAC 40 et S&P 500</div>',
    unsafe_allow_html=True,
)

metric_horizons = [
    ("1j", "1 jour"),
    ("5j", "1 semaine"),
    ("10j", "2 semaines"),
    ("21j", "1 mois"),
]

for index_name in ["CAC 40", "S&P 500"]:
    st.markdown(f"#### {index_name}")

    columns = st.columns(4)

    for column, (horizon_key, horizon_label) in zip(
        columns,
        metric_horizons,
    ):
        value = performance_table.loc[
            index_name,
            horizon_key,
        ]

        column.metric(
            horizon_label,
            signed_percent(value),
        )


chart = go.Figure()

for index_name in ["CAC 40", "S&P 500"]:
    values = performance_table.loc[index_name]

    chart.add_trace(
        go.Scatter(
            x=list(range(1, 22)),
            y=values.tolist(),
            mode="lines+markers",
            name=index_name,
            hovertemplate=(
                index_name
                + "<br>%{x} séance(s)"
                + "<br>%{y:+.2f}%"
                + "<extra></extra>"
            ),
        )
    )

chart.add_hline(
    y=0,
    line_width=1,
    line_dash="dot",
)

chart.update_layout(
    template="plotly_dark",
    paper_bgcolor="#0b0f15",
    plot_bgcolor="#0b0f15",
    height=430,
    margin=dict(l=25, r=25, t=30, b=35),
    hovermode="x unified",
    dragmode="pan",
    legend=dict(
        orientation="h",
        x=0,
        y=1.08,
    ),
    xaxis=dict(
        title="Nombre de séances",
        dtick=1,
        gridcolor="#202938",
        zeroline=False,
    ),
    yaxis=dict(
        title="Performance",
        ticksuffix="%",
        gridcolor="#202938",
        zeroline=False,
        side="right",
    ),
)

st.plotly_chart(
    chart,
    use_container_width=True,
    config={
        "displaylogo": False,
        "scrollZoom": True,
    },
)

with st.expander(
    "Voir toutes les performances de 1j à 21j",
    expanded=False,
):
    st.dataframe(
        style_performance_table(
            performance_table
        ),
        use_container_width=True,
    )

st.caption(
    "Calcul : dernière clôture Yahoo disponible contre la clôture "
    "située N séances plus tôt. Pendant la séance, la bougie journalière "
    "Yahoo peut encore évoluer."
)



class SimpleWikipediaTableParser(HTMLParser):
    """
    Minimal HTML table parser based only on Python's standard library.

    It is sufficient for the constituent tables used on the CAC 40 and
    S&P 500 Wikipedia pages and removes the lxml/html5lib dependency.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table_depth = 0
        self._current_table: list[list[str]] | None = None
        self._current_row: list[str] | None = None
        self._current_cell_parts: list[str] | None = None
        self._inside_cell = False

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        tag = tag.lower()

        if tag == "table":
            self._table_depth += 1

            if self._table_depth == 1:
                self._current_table = []

        elif tag == "tr" and self._table_depth == 1:
            self._current_row = []

        elif (
            tag in {"th", "td"}
            and self._table_depth == 1
            and self._current_row is not None
        ):
            self._inside_cell = True
            self._current_cell_parts = []

        elif (
            tag == "br"
            and self._inside_cell
            and self._current_cell_parts is not None
        ):
            self._current_cell_parts.append(" ")

    def handle_data(self, data: str) -> None:
        if (
            self._inside_cell
            and self._current_cell_parts is not None
        ):
            self._current_cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if (
            tag in {"th", "td"}
            and self._table_depth == 1
            and self._current_row is not None
            and self._current_cell_parts is not None
        ):
            text = " ".join(
                "".join(self._current_cell_parts).split()
            )

            text = re.sub(
                r"\[[^\]]*\]",
                "",
                text,
            ).strip()

            self._current_row.append(text)
            self._inside_cell = False
            self._current_cell_parts = None

        elif (
            tag == "tr"
            and self._table_depth == 1
            and self._current_table is not None
            and self._current_row is not None
        ):
            if any(cell.strip() for cell in self._current_row):
                self._current_table.append(self._current_row)

            self._current_row = None

        elif tag == "table":
            if (
                self._table_depth == 1
                and self._current_table is not None
                and self._current_table
            ):
                self.tables.append(self._current_table)

            self._table_depth = max(
                self._table_depth - 1,
                0,
            )

            if self._table_depth == 0:
                self._current_table = None
                self._current_row = None
                self._current_cell_parts = None
                self._inside_cell = False


def html_tables_to_dataframes(
    html_text: str,
) -> list[pd.DataFrame]:
    parser = SimpleWikipediaTableParser()
    parser.feed(html_text)

    dataframes: list[pd.DataFrame] = []

    for raw_table in parser.tables:
        if len(raw_table) < 2:
            continue

        header = raw_table[0]

        if not header:
            continue

        width = len(header)
        rows: list[list[str]] = []

        for row in raw_table[1:]:
            if len(row) < width:
                row = row + [""] * (width - len(row))
            elif len(row) > width:
                row = row[:width]

            rows.append(row)

        if not rows:
            continue

        # Make duplicated header names unique enough for lookup.
        seen: dict[str, int] = {}
        unique_header: list[str] = []

        for index, column in enumerate(header):
            base_name = column.strip() or f"Column {index + 1}"
            count = seen.get(base_name, 0)
            seen[base_name] = count + 1

            if count:
                unique_header.append(
                    f"{base_name}_{count + 1}"
                )
            else:
                unique_header.append(base_name)

        dataframes.append(
            pd.DataFrame(
                rows,
                columns=unique_header,
            )
        )

    return dataframes


# =============================================================================
# CONSTITUENTS + DAILY MOVERS
# =============================================================================

def normalized_column_name(value: Any) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "",
        str(value).lower(),
    )


def choose_column(
    dataframe: pd.DataFrame,
    candidates: list[str],
) -> Any | None:
    normalized = {
        normalized_column_name(column): column
        for column in dataframe.columns
    }

    for candidate in candidates:
        match = normalized.get(
            normalized_column_name(candidate)
        )
        if match is not None:
            return match

    return None


@st.cache_data(ttl=86400, show_spinner=False)
def load_constituents(
    universe: str,
) -> pd.DataFrame:
    url = WIKIPEDIA_URLS[universe]

    response = requests.get(
        url,
        headers=REQUEST_HEADERS,
        timeout=25,
    )
    response.raise_for_status()

    tables = html_tables_to_dataframes(
        response.text
    )

    if not tables:
        raise ValueError(
            "Aucun tableau HTML n'a été détecté sur Wikipédia."
        )

    symbol_candidates = (
        ["Ticker", "Symbol", "EPIC"]
        if universe == "CAC 40"
        else ["Symbol", "Ticker"]
    )

    name_candidates = [
        "Company",
        "Security",
        "Constituent",
        "Name",
    ]

    selected = None
    symbol_column = None
    name_column = None

    for table in tables:
        symbol_column = choose_column(
            table,
            symbol_candidates,
        )
        name_column = choose_column(
            table,
            name_candidates,
        )

        if (
            symbol_column is not None
            and name_column is not None
            and len(table) >= 30
        ):
            selected = table.copy()
            break

    if selected is None:
        raise ValueError(
            f"Impossible d’identifier la table des composants {universe}."
        )

    constituents = selected[
        [symbol_column, name_column]
    ].copy()

    constituents.columns = [
        "Ticker",
        "Nom",
    ]

    constituents["Ticker"] = (
        constituents["Ticker"]
        .astype(str)
        .str.replace(r"\[.*?\]", "", regex=True)
        .str.strip()
    )

    constituents["Nom"] = (
        constituents["Nom"]
        .astype(str)
        .str.replace(r"\[.*?\]", "", regex=True)
        .str.strip()
    )

    if universe == "S&P 500":
        constituents["Yahoo"] = (
            constituents["Ticker"]
            .str.replace(".", "-", regex=False)
        )
    else:
        def cac_yahoo_symbol(symbol: str) -> str:
            cleaned = symbol.replace(" ", "")
            if "." in cleaned:
                return cleaned
            return f"{cleaned}.PA"

        constituents["Yahoo"] = constituents[
            "Ticker"
        ].map(cac_yahoo_symbol)

    constituents = constituents.drop_duplicates(
        subset=["Yahoo"]
    )

    return constituents.reset_index(drop=True)


def download_close_chunks(
    symbols: list[str],
    chunk_size: int = 90,
) -> pd.DataFrame:
    close_frames: list[pd.DataFrame] = []

    for start in range(0, len(symbols), chunk_size):
        chunk = symbols[
            start:start + chunk_size
        ]

        downloaded = yf.download(
            tickers=chunk,
            period="5d",
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=True,
            group_by="column",
            timeout=25,
        )

        close = extract_close_frame(
            downloaded,
            chunk,
        )

        if not close.empty:
            close_frames.append(close)

    if not close_frames:
        return pd.DataFrame()

    return pd.concat(
        close_frames,
        axis=1,
    ).loc[
        :,
        lambda dataframe: ~dataframe.columns.duplicated()
    ]


@st.cache_data(ttl=900, show_spinner=False)
def load_daily_movers(
    universe: str,
) -> pd.DataFrame:
    constituents = load_constituents(
        universe
    )

    close = download_close_chunks(
        constituents["Yahoo"].tolist()
    )

    if close.empty:
        raise ValueError(
            f"Yahoo n’a retourné aucun prix pour les composants {universe}."
        )

    name_map = constituents.set_index(
        "Yahoo"
    )["Nom"].to_dict()

    original_ticker_map = constituents.set_index(
        "Yahoo"
    )["Ticker"].to_dict()

    rows = []

    for symbol in constituents["Yahoo"]:
        if symbol not in close.columns:
            continue

        series = close[symbol].dropna()

        if len(series) < 2:
            continue

        previous = float(series.iloc[-2])
        latest = float(series.iloc[-1])

        if previous == 0:
            continue

        rows.append(
            {
                "Ticker": original_ticker_map.get(
                    symbol,
                    symbol,
                ),
                "Nom": name_map.get(
                    symbol,
                    symbol,
                ),
                "Dernier": latest,
                "Performance": (
                    latest / previous - 1
                ) * 100,
                "Date": pd.Timestamp(
                    series.index[-1]
                ).date(),
            }
        )

    if not rows:
        raise ValueError(
            f"Aucune performance exploitable pour {universe}."
        )

    return (
        pd.DataFrame(rows)
        .sort_values(
            "Performance",
            ascending=False,
        )
        .reset_index(drop=True)
    )


st.divider()

st.markdown(
    '<div class="section-label">Top performers de la journée</div>',
    unsafe_allow_html=True,
)

control_one, control_two = st.columns(
    [2, 1]
)

with control_one:
    movers_universe = st.radio(
        "Univers",
        options=["CAC 40", "S&P 500"],
        horizontal=True,
    )

with control_two:
    mover_count = st.selectbox(
        "Nombre de valeurs",
        options=[5, 10, 15],
        index=0,
    )

if movers_universe == "S&P 500":
    st.caption(
        "Le premier chargement du S&P 500 peut prendre quelques secondes, "
        "car Yahoo doit traiter environ 500 valeurs. Le résultat est ensuite "
        "mis en cache pendant 15 minutes."
    )

try:
    with st.spinner(
        f"Chargement des composants {movers_universe}…"
    ):
        movers = load_daily_movers(
            movers_universe
        )

    top_movers = movers.head(
        mover_count
    ).copy()

    bottom_movers = (
        movers.tail(mover_count)
        .sort_values(
            "Performance",
            ascending=True,
        )
        .copy()
    )

    top_column, bottom_column = st.columns(2)

    display_columns = [
        "Ticker",
        "Nom",
        "Dernier",
        "Performance",
    ]

    with top_column:
        st.markdown("#### Top")
        st.dataframe(
            top_movers[display_columns],
            hide_index=True,
            use_container_width=True,
            column_config={
                "Dernier": st.column_config.NumberColumn(
                    "Dernier",
                    format="%.2f",
                ),
                "Performance": st.column_config.NumberColumn(
                    "Perf.",
                    format="%+.2f%%",
                ),
            },
        )

    with bottom_column:
        st.markdown("#### Flop")
        st.dataframe(
            bottom_movers[display_columns],
            hide_index=True,
            use_container_width=True,
            column_config={
                "Dernier": st.column_config.NumberColumn(
                    "Dernier",
                    format="%.2f",
                ),
                "Performance": st.column_config.NumberColumn(
                    "Perf.",
                    format="%+.2f%%",
                ),
            },
        )

except Exception as error:
    st.warning(
        f"Market movers indisponibles : {error}"
    )

st.caption(
    "Composants récupérés depuis Wikipédia, cours et performances "
    "calculés avec Yahoo Finance. Il s’agit de variations clôture à clôture "
    "sur la dernière séance disponible."
)


# =============================================================================
# ECONOMIC CALENDAR
# =============================================================================

st.divider()

st.markdown(
    '<div class="section-label">Calendrier économique</div>',
    unsafe_allow_html=True,
)

calendar_view = st.radio(
    "Période",
    options=["Aujourd’hui", "Semaine"],
    horizontal=True,
)

calendar_type = (
    "day"
    if calendar_view == "Aujourd’hui"
    else "week"
)

calendar_parameters = {
    "ecoDayBackground": "#0b0f15",
    "defaultFont": "#d1d4dc",
    "innerBorderColor": "#202938",
    "borderColor": "#202938",
    "ecoDayFontColor": "#f4f7fb",
    "columns": (
        "exc_flags,exc_currency,exc_importance,"
        "exc_actual,exc_forecast,exc_previous"
    ),
    "features": (
        "datepicker,timezone,timeselector,filters"
    ),
    # Principales économies et zones macro.
    "countries": (
        "25,32,6,37,72,22,17,39,14,10,"
        "35,43,56,36,110,11,26,12,4,5"
    ),
    "calType": calendar_type,
    "timeZone": "8",
    "lang": "1",
}

calendar_url = (
    "https://sslecal2.investing.com?"
    + urlencode(
        calendar_parameters,
        safe=",",
    )
)

calendar_html = f"""
<div style="
    width:100%;
    background:#0b0f15;
    border:1px solid #202938;
    border-radius:10px;
    overflow:hidden;
">
    <iframe
        src="{calendar_url}"
        width="100%"
        height="650"
        frameborder="0"
        allowtransparency="true"
        marginwidth="0"
        marginheight="0"
        style="display:block;"
    ></iframe>
</div>

<div style="
    margin-top:6px;
    color:#8490a3;
    font-family:Arial, Helvetica, sans-serif;
    font-size:11px;
">
    Real Time Economic Calendar provided by
    <a
        href="https://www.investing.com/"
        rel="nofollow"
        target="_blank"
        style="color:#94a3b8;font-weight:600;"
    >
        Investing.com
    </a>.
</div>
"""

components.html(
    calendar_html,
    height=690,
    scrolling=False,
)

st.caption(
    "Investing.com ne fournit pas ici une API publique structurée : "
    "cette section utilise son widget officiel, actualisé automatiquement. "
    "Les filtres et le fuseau horaire peuvent être modifiés directement "
    "dans le calendrier."
)

'''

KALMAN_LAB_SOURCE = r'''
from __future__ import annotations

import json
import os
import re
import unicodedata
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from lse import LSE


# =============================================================================
# PAGE
# =============================================================================

st.markdown(
    """
    <style>
        .stApp {
            background: #050708;
        }

        [data-testid="stSidebar"] {
            background: #0b1016;
            border-right: 1px solid #1d2632;
        }

        .block-container {
            max-width: 100%;
            padding-top: 0.75rem;
            padding-left: 1rem;
            padding-right: 1rem;
            padding-bottom: 1.4rem;
        }

        #MainMenu,
        footer {
            visibility: hidden;
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        .tick-kalman-title {
            color: #f2f5f8;
            font-size: 2rem;
            font-weight: 740;
            letter-spacing: -0.045em;
            margin: 0;
        }

        .tick-kalman-subtitle {
            color: #7f8b9c;
            font-size: 0.9rem;
            margin-top: 0.12rem;
            margin-bottom: 0.8rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="tick-kalman-title">Kalman Lab — Tick Engine</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="tick-kalman-subtitle">'
    'Replay LSE · Kalman filtering · HMM regimes · Dynamic beta · Relative value'
    '</div>',
    unsafe_allow_html=True,
)


# =============================================================================
# SYMBOLS
# =============================================================================

MARKETS = {
    "CAC 40": {
        "candidates": [
            "CAC40", "CAC40/EUR", "FR40", "FR40/EUR", "FRA40", "PX1"
        ],
        "search": ["cac 40", "france 40"],
    },
    "DAX": {
        "candidates": [
            "DAX", "DAX40", "DAX40/EUR", "DE40", "DE40/EUR", "GER40"
        ],
        "search": ["dax 40", "germany 40", "dax"],
    },
    "Euro Stoxx 50": {
        "candidates": [
            "SX5E", "EU50", "EU50/EUR", "STOXX50", "ESTX50"
        ],
        "search": ["euro stoxx 50", "stoxx 50"],
    },
    "Nasdaq 100": {
        "candidates": [
            "NAS100", "NAS100/USD", "NDX", "NASDAQ100", "US100"
        ],
        "search": ["nasdaq 100", "nasdaq-100"],
    },
    "S&P 500": {
        "candidates": [
            "SPX500", "SPX500/USD", "SPX", "US500", "SP500"
        ],
        "search": ["s&p 500", "sp 500", "standard and poor 500"],
    },
    "Gold": {
        "candidates": ["XAU/USD", "GOLD/USD", "GOLD", "GC"],
        "search": ["spot gold", "gold"],
    },
    "Brent": {
        "candidates": [
            "BRENT/USD", "BRENT", "BCO/USD", "UKOIL/USD", "BRN", "BZ"
        ],
        "search": ["brent crude oil", "brent crude", "brent"],
    },
    "EUR/USD": {
        "candidates": ["EUR/USD", "EURUSD"],
        "search": ["eur usd", "euro us dollar"],
    },
    "Bitcoin": {
        "candidates": ["BTC/USD", "BTCUSD"],
        "search": ["bitcoin", "btc usd"],
    },
}

REPLAY_OPTIONS = {
    "5 minutes": 5,
    "15 minutes": 15,
    "30 minutes": 30,
    "1 heure": 60,
    "2 heures": 120,
    "4 heures": 240,
    "8 heures": 480,
    "24 heures": 1440,
}

SYNC_OPTIONS = {
    "Chaque tick (dernier prix connu)": 0,
    "1 seconde": 1000,
    "5 secondes": 5000,
    "15 secondes": 15000,
    "1 minute": 60000,
}

MODE_DESCRIPTIONS = {
    "Lissage & prévision": (
        "Chaque tick met à jour directement le filtre local level + trend."
    ),
    "Bêta dynamique": (
        "Les ticks des deux actifs sont synchronisés, puis le bêta est mis à jour récursivement."
    ),
    "Relative value": (
        "Le Kalman estime un hedge ratio dynamique et le z-score du spread."
    ),
    "Kalman + HMM": (
        "Le Kalman nettoie les ticks ; un HMM estime les régimes bruit, hausse, baisse et choc."
    ),
}


def normalize(value: Any) -> str:
    value = unicodedata.normalize(
        "NFKD",
        str(value or ""),
    )

    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )

    value = value.lower().replace("&", " and ")

    return re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    ).strip()


def catalogue_score(
    row: dict[str, Any],
    queries: list[str],
) -> int:
    symbol = normalize(row.get("symbol"))
    name = normalize(row.get("name"))
    category = normalize(row.get("category"))
    text = f"{symbol} {name}"
    score = 0

    for query in queries:
        query = normalize(query)
        tokens = query.split()

        if query == symbol:
            score = max(score, 1200)
        elif query == name:
            score = max(score, 1100)
        elif query and query in name:
            score = max(score, 700)
        elif query and query in text:
            score = max(score, 500)
        elif tokens and all(token in text for token in tokens):
            score = max(score, 300)

    if any(
        word in category
        for word in ["index", "indice", "commodit", "forex", "crypto"]
    ):
        score += 100

    return score


@st.cache_data(ttl=3600, show_spinner=False)
def resolve_lse_symbols(
    api_key_value: str,
) -> tuple[dict[str, str], list[str]]:
    client = LSE(api_key=api_key_value)
    catalogue = client.catalog()

    rows = [
        row
        for row in catalogue
        if row.get("symbol")
    ]

    rows_by_symbol: dict[str, dict[str, Any]] = {}

    for row in rows:
        rows_by_symbol.setdefault(
            str(row["symbol"]).upper(),
            row,
        )

    resolved: dict[str, str] = {}
    unresolved: list[str] = []

    for market_name, settings in MARKETS.items():
        selected_row = None

        for candidate in settings["candidates"]:
            selected_row = rows_by_symbol.get(
                candidate.upper()
            )

            if selected_row is not None:
                break

        if selected_row is None:
            ranked = sorted(
                rows,
                key=lambda row: catalogue_score(
                    row,
                    settings["search"],
                ),
                reverse=True,
            )

            if ranked and catalogue_score(
                ranked[0],
                settings["search"],
            ) > 0:
                selected_row = ranked[0]

        if selected_row is None:
            unresolved.append(market_name)
        else:
            resolved[market_name] = str(
                selected_row["symbol"]
            )

    return resolved, unresolved


# =============================================================================
# CONTROLS
# =============================================================================

try:
    default_api_key = st.secrets["LSE_API_KEY"]
except Exception:
    default_api_key = os.getenv("LSE_API_KEY", "")

with st.sidebar:
    st.markdown("### Tick Kalman")

    if default_api_key:
        api_key = default_api_key
        st.caption("Clé LSE chargée depuis les secrets du serveur.")
    else:
        api_key = st.text_input(
            "Clé API LSE",
            value="",
            type="password",
            placeholder="lse_live_...",
            key="kalman_tick_api_key",
        )

if not api_key:
    st.info(
        "Entre ta clé API LSE dans la sidebar pour charger les ticks."
    )
    st.stop()

try:
    resolved_symbols, unresolved_markets = resolve_lse_symbols(
        api_key
    )
except Exception as error:
    st.error(
        f"Impossible de lire le catalogue LSE : {error}"
    )
    st.stop()

available_markets = [
    market
    for market in MARKETS
    if market in resolved_symbols
]

if not available_markets:
    st.error(
        "Aucun des marchés demandés n'a été trouvé dans le catalogue LSE."
    )
    st.stop()

with st.sidebar:
    mode = st.selectbox(
        "Modèle",
        options=list(MODE_DESCRIPTIONS),
        key="kalman_tick_mode",
    )

    st.caption(MODE_DESCRIPTIONS[mode])

    replay_label = st.selectbox(
        "Historique rejoué",
        options=list(REPLAY_OPTIONS),
        index=4,
        key="kalman_tick_replay",
    )

    replay_minutes = REPLAY_OPTIONS[replay_label]

    max_points = st.slider(
        "Points conservés",
        min_value=500,
        max_value=8000,
        value=3000,
        step=500,
        key="kalman_tick_max_points",
    )

    if mode in {"Lissage & prévision", "Kalman + HMM"}:
        asset_y = st.selectbox(
            "Actif",
            options=available_markets,
            index=(
                available_markets.index("Nasdaq 100")
                if "Nasdaq 100" in available_markets
                else 0
            ),
            key="kalman_tick_single_asset",
        )

        symbol_y = resolved_symbols[asset_y]
        asset_x = None
        symbol_x = None
        sync_ms = 0

        forecast_ticks = st.slider(
            "Horizon de prévision (ticks)",
            min_value=10,
            max_value=200,
            value=50,
            step=10,
            key="kalman_tick_forecast",
        )

        reactivity = st.slider(
            "Réactivité du filtre",
            min_value=1,
            max_value=10,
            value=5,
            key="kalman_tick_reactivity",
        )

        observation_trust = st.slider(
            "Confiance dans le tick observé",
            min_value=1,
            max_value=10,
            value=6,
            key="kalman_tick_trust",
        )

        if mode == "Kalman + HMM":
            hmm_persistence = st.slider(
                "Persistance des régimes HMM",
                min_value=70,
                max_value=99,
                value=92,
                step=1,
                help=(
                    "Plus la valeur est élevée, plus le HMM demande des preuves "
                    "avant de changer de régime."
                ),
                key="kalman_hmm_persistence",
            )

            hmm_signal_threshold = st.slider(
                "Confiance minimale du signal",
                min_value=50,
                max_value=95,
                value=65,
                step=5,
                help=(
                    "Probabilité minimale avant d'afficher LONG, SHORT "
                    "ou RISK OFF."
                ),
                key="kalman_hmm_threshold",
            )
        else:
            hmm_persistence = 92
            hmm_signal_threshold = 65

        z_window = 40

    else:
        first_default = (
            available_markets.index("Nasdaq 100")
            if "Nasdaq 100" in available_markets
            else 0
        )

        second_default = (
            available_markets.index("S&P 500")
            if "S&P 500" in available_markets
            else min(1, len(available_markets) - 1)
        )

        asset_y = st.selectbox(
            "Actif Y",
            options=available_markets,
            index=first_default,
            key="kalman_tick_asset_y",
        )

        asset_x = st.selectbox(
            "Actif X",
            options=available_markets,
            index=second_default,
            key="kalman_tick_asset_x",
        )

        if asset_y == asset_x:
            st.warning(
                "Choisis deux actifs différents."
            )
            st.stop()

        symbol_y = resolved_symbols[asset_y]
        symbol_x = resolved_symbols[asset_x]

        sync_label = st.selectbox(
            "Synchronisation des ticks",
            options=list(SYNC_OPTIONS),
            index=1,
            key="kalman_tick_sync",
        )

        sync_ms = SYNC_OPTIONS[sync_label]

        reactivity = st.slider(
            "Vitesse d'adaptation",
            min_value=1,
            max_value=10,
            value=5,
            key="kalman_tick_pair_reactivity",
        )

        observation_trust = st.slider(
            "Confiance dans les observations",
            min_value=1,
            max_value=10,
            value=6,
            key="kalman_tick_pair_trust",
        )

        z_window = st.slider(
            "Fenêtre du z-score",
            min_value=20,
            max_value=200,
            value=60,
            step=10,
            key="kalman_tick_z_window",
        )

        forecast_ticks = 0
        hmm_persistence = 92
        hmm_signal_threshold = 65

    full_height = st.toggle(
        "Vue haute",
        value=False,
        key="kalman_tick_tall_view",
    )

    st.divider()
    st.caption(
        f"Y : `{symbol_y}`"
    )

    if symbol_x:
        st.caption(
            f"X : `{symbol_x}`"
        )

    if unresolved_markets:
        with st.expander("Marchés non trouvés"):
            st.write(", ".join(unresolved_markets))


# =============================================================================
# TICK ENGINE
# =============================================================================

settings = {
    "apiKey": api_key,
    "mode": mode,
    "assetY": asset_y,
    "assetX": asset_x,
    "symbolY": symbol_y,
    "symbolX": symbol_x,
    "replayMinutes": replay_minutes,
    "maxPoints": max_points,
    "syncMs": sync_ms,
    "forecastTicks": forecast_ticks,
    "reactivity": reactivity,
    "observationTrust": observation_trust,
    "zWindow": z_window,
    "hmmPersistence": hmm_persistence,
    "hmmSignalThreshold": hmm_signal_threshold,
}

html_template = r"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>

    <style>
        :root { color-scheme: dark; }

        html, body {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: #050708;
            color: #d5dde7;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
        }

        * { box-sizing: border-box; }

        #shell {
            width: 100%;
            height: 100vh;
            display: flex;
            flex-direction: column;
            gap: 8px;
            padding: 2px;
            background: #050708;
        }

        #toolbar {
            min-height: 42px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 5px 8px;
            background: #0d131b;
            border: 1px solid #202a36;
            border-radius: 9px;
        }

        #titleBlock {
            min-width: 0;
        }

        #terminalTitle {
            color: #f2f5f8;
            font-size: 14px;
            font-weight: 700;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        #terminalStatus {
            color: #7f8b9c;
            font-size: 10px;
            margin-top: 2px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        #toolbarButtons {
            display: flex;
            gap: 6px;
            flex-shrink: 0;
        }

        button {
            border: 1px solid #2a3543;
            border-radius: 7px;
            background: #151d27;
            color: #cdd6e1;
            padding: 6px 9px;
            cursor: pointer;
            font-size: 11px;
        }

        button:hover {
            background: #1c2734;
        }

        #metrics {
            display: grid;
            grid-template-columns: repeat(5, minmax(110px, 1fr));
            gap: 7px;
        }

        .metric {
            min-width: 0;
            min-height: 61px;
            padding: 8px 10px;
            background: #0d131b;
            border: 1px solid #202a36;
            border-radius: 9px;
        }

        .metricLabel {
            color: #7f8b9c;
            font-size: 10px;
            margin-bottom: 4px;
        }

        .metricValue {
            color: #f2f5f8;
            font-size: 17px;
            font-weight: 690;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .metricSub {
            color: #7f8b9c;
            font-size: 9px;
            margin-top: 3px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        #singleCharts,
        #pairCharts {
            flex: 1;
            min-height: 0;
        }

        #singleCharts {
            display: none;
            grid-template-columns: 1fr;
        }

        #pairCharts {
            display: none;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: 1fr 1fr;
            gap: 8px;
        }

        .chartCard {
            min-height: 0;
            background: #050708;
            border: 1px solid #202a36;
            border-radius: 9px;
            overflow: hidden;
        }

        #pairPriceCard {
            grid-column: 1 / span 2;
        }

        #singleChart,
        #pairPriceChart,
        #pairBetaChart,
        #pairResidualChart {
            width: 100%;
            height: 100%;
        }

        @media (max-width: 1050px) {
            #metrics {
                grid-template-columns: repeat(3, minmax(105px, 1fr));
            }
        }
    </style>
</head>

<body>
<div id="shell">
    <div id="toolbar">
        <div id="titleBlock">
            <div id="terminalTitle">Kalman Tick Engine</div>
            <div id="terminalStatus">Initialisation…</div>
        </div>

        <div id="toolbarButtons">
            <button id="panButton">Déplacer</button>
            <button id="zoomButton">Zone</button>
            <button id="resetButton">Reset</button>
            <button id="fullscreenButton">Plein écran</button>
        </div>
    </div>

    <div id="metrics">
        <div class="metric">
            <div class="metricLabel" id="metricLabel1">Dernier Y</div>
            <div class="metricValue" id="metricValue1">—</div>
            <div class="metricSub" id="metricSub1">—</div>
        </div>

        <div class="metric">
            <div class="metricLabel" id="metricLabel2">Filtré / Bêta</div>
            <div class="metricValue" id="metricValue2">—</div>
            <div class="metricSub" id="metricSub2">—</div>
        </div>

        <div class="metric">
            <div class="metricLabel" id="metricLabel3">Tendance / Alpha</div>
            <div class="metricValue" id="metricValue3">—</div>
            <div class="metricSub" id="metricSub3">—</div>
        </div>

        <div class="metric">
            <div class="metricLabel" id="metricLabel4">Prévision / Résiduel</div>
            <div class="metricValue" id="metricValue4">—</div>
            <div class="metricSub" id="metricSub4">—</div>
        </div>

        <div class="metric">
            <div class="metricLabel" id="metricLabel5">Activité / Z-score</div>
            <div class="metricValue" id="metricValue5">—</div>
            <div class="metricSub" id="metricSub5">—</div>
        </div>
    </div>

    <div id="singleCharts">
        <div class="chartCard">
            <div id="singleChart"></div>
        </div>
    </div>

    <div id="pairCharts">
        <div class="chartCard" id="pairPriceCard">
            <div id="pairPriceChart"></div>
        </div>

        <div class="chartCard">
            <div id="pairBetaChart"></div>
        </div>

        <div class="chartCard">
            <div id="pairResidualChart"></div>
        </div>
    </div>
</div>

<script>
const SETTINGS = __SETTINGS__;

const MODE = SETTINGS.mode;
const API_KEY = SETTINGS.apiKey;
const SYMBOL_Y = SETTINGS.symbolY;
const SYMBOL_X = SETTINGS.symbolX;
const ASSET_Y = SETTINGS.assetY;
const ASSET_X = SETTINGS.assetX;
const REPLAY_MINUTES = Number(SETTINGS.replayMinutes);
const MAX_POINTS = Number(SETTINGS.maxPoints);
const SYNC_MS = Number(SETTINGS.syncMs);
const FORECAST_TICKS = Number(SETTINGS.forecastTicks);
const REACTIVITY = Number(SETTINGS.reactivity);
const OBSERVATION_TRUST = Number(SETTINGS.observationTrust);
const Z_WINDOW = Number(SETTINGS.zWindow);
const HMM_PERSISTENCE = Number(SETTINGS.hmmPersistence || 92) / 100;
const HMM_SIGNAL_THRESHOLD = Number(SETTINGS.hmmSignalThreshold || 65) / 100;
const MIN_PAIR_WARMUP = 20;

const IS_SMOOTH = MODE === "Lissage & prévision";
const IS_HYBRID = MODE === "Kalman + HMM";
const IS_SINGLE = IS_SMOOTH || IS_HYBRID;
const IS_BETA = MODE === "Bêta dynamique";
const IS_RV = MODE === "Relative value";

const COLORS = {
    raw: "#d9a36c",
    filter: "#78b4df",
    filterBand: "rgba(62,117,157,0.24)",
    forecast: "#d9b44a",
    forecastBand: "rgba(184,145,38,0.16)",
    secondary: "#9a7cf8",
    green: "#26a69a",
    red: "#ef5350",
    grid: "#1d252e",
    text: "#d5dde7",
    muted: "#7f8b9c",
    noise: "#7f8b9c",
    up: "#26a69a",
    down: "#ef5350",
    shock: "#d9b44a"
};

const HMM_STATES = [
    {
        key: "noise",
        label: "Bruit / range",
        color: COLORS.noise,
        fill: "rgba(127,139,156,0.08)"
    },
    {
        key: "up",
        label: "Tendance haussière",
        color: COLORS.up,
        fill: "rgba(38,166,154,0.10)"
    },
    {
        key: "down",
        label: "Tendance baissière",
        color: COLORS.down,
        fill: "rgba(239,83,80,0.10)"
    },
    {
        key: "shock",
        label: "Choc / transition",
        color: COLORS.shock,
        fill: "rgba(217,180,74,0.11)"
    }
];

const statusBox = document.getElementById("terminalStatus");
const titleBox = document.getElementById("terminalTitle");
const singleCharts = document.getElementById("singleCharts");
const pairCharts = document.getElementById("pairCharts");

const metricLabels = [1,2,3,4,5].map(i => document.getElementById("metricLabel" + i));
const metricValues = [1,2,3,4,5].map(i => document.getElementById("metricValue" + i));
const metricSubs = [1,2,3,4,5].map(i => document.getElementById("metricSub" + i));

let socket = null;
let reconnectTimer = null;
let connectedAt = null;
let liveTickArrivals = [];
let dirty = false;

const plotConfig = {
    responsive: true,
    displaylogo: false,
    scrollZoom: true,
    doubleClick: "reset+autosize",
    modeBarButtonsToAdd: [
        "pan2d",
        "zoomIn2d",
        "zoomOut2d",
        "autoScale2d",
        "resetScale2d"
    ],
    modeBarButtonsToRemove: ["lasso2d", "select2d"]
};

function commonLayout(title, uirevision) {
    return {
        template: "plotly_dark",
        paper_bgcolor: "#050708",
        plot_bgcolor: "#050708",
        margin: {l: 22, r: 74, t: 45, b: 30},
        title: {
            text: title,
            x: 0.01,
            font: {size: 14, color: COLORS.text}
        },
        hovermode: "x unified",
        dragmode: "pan",
        uirevision: uirevision,
        showlegend: true,
        legend: {
            orientation: "h",
            x: 0,
            y: 1.05,
            font: {size: 9, color: COLORS.muted},
            bgcolor: "rgba(0,0,0,0)"
        },
        xaxis: {
            gridcolor: COLORS.grid,
            zeroline: false,
            showspikes: true,
            spikecolor: COLORS.muted
        },
        yaxis: {
            gridcolor: COLORS.grid,
            zeroline: false,
            side: "right",
            automargin: true,
            showticklabels: true,
            separatethousands: true
        }
    };
}

function parseTimestamp(value) {
    if (typeof value === "number") {
        return new Date(value < 1e12 ? value * 1000 : value);
    }

    const numeric = Number(value);

    if (value !== null && value !== "" && Number.isFinite(numeric)) {
        return new Date(numeric < 1e12 ? numeric * 1000 : numeric);
    }

    return new Date(value);
}

function formatPrice(value) {
    if (!Number.isFinite(Number(value))) return "—";
    const number = Number(value);
    const absolute = Math.abs(number);

    if (absolute >= 1000) {
        return number.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    if (absolute >= 10) {
        return number.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 4
        });
    }

    return number.toLocaleString(undefined, {
        minimumFractionDigits: 4,
        maximumFractionDigits: 6
    });
}

function formatSigned(value, digits=2) {
    if (!Number.isFinite(Number(value))) return "—";
    const number = Number(value);
    return (number >= 0 ? "+" : "") + number.toFixed(digits);
}

function trimArray(array, maxLength=MAX_POINTS) {
    if (array.length > maxLength) {
        array.splice(0, array.length - maxLength);
    }
}

function variance(values) {
    if (!values || values.length < 2) return 1e-8;
    const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
    const result = values.reduce((sum, value) => {
        const diff = value - mean;
        return sum + diff * diff;
    }, 0) / values.length;
    return Math.max(result, 1e-12);
}

function mean(values) {
    if (!values.length) return NaN;
    return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function standardDeviation(values) {
    return Math.sqrt(variance(values));
}

function setMetric(index, label, value, sub="—", color=COLORS.text) {
    metricLabels[index].textContent = label;
    metricValues[index].textContent = value;
    metricValues[index].style.color = color;
    metricSubs[index].textContent = sub;
}

function registerLiveArrival(isReplay) {
    if (isReplay) return;
    const now = Date.now();
    liveTickArrivals.push(now);
    const cutoff = now - 60000;
    while (liveTickArrivals.length && liveTickArrivals[0] < cutoff) {
        liveTickArrivals.shift();
    }
}

function estimatedTickInterval(timestamps) {
    if (timestamps.length < 3) return 1000;
    const start = Math.max(1, timestamps.length - 100);
    const differences = [];

    for (let i = start; i < timestamps.length; i++) {
        const difference = timestamps[i].getTime() - timestamps[i - 1].getTime();
        if (difference > 0 && difference < 60000) differences.push(difference);
    }

    if (!differences.length) return 1000;
    differences.sort((a, b) => a - b);
    return differences[Math.floor(differences.length / 2)];
}

// -----------------------------------------------------------------------------
// SINGLE-ASSET LOCAL LINEAR TREND
// -----------------------------------------------------------------------------

const single = {
    timestamps: [],
    observed: [],
    filtered: [],
    trend: [],
    lower: [],
    upper: [],
    differences: [],
    innovationZ: [],
    slopeZ: [],
    uncertaintyRatio: [],
    hmmNoise: [],
    hmmUp: [],
    hmmDown: [],
    hmmShock: [],
    hmmRegime: [],
    hmmConfidence: [],
    hmmAction: [],
    hmmDuration: [],
    state: null,
    covariance: null,
    latestTick: null,
    hmmPosterior: [0.82, 0.06, 0.06, 0.06],
    hmmCandidate: 0,
    hmmCandidateCount: 0,
    hmmConfirmedState: 0,
    hmmConfirmedDuration: 0
};


function gaussianLogPdf(value, average, standardDeviationValue) {
    const sigma = Math.max(
        Number(standardDeviationValue),
        1e-6
    );

    const difference =
        (value - average)
        / sigma;

    return (
        -Math.log(
            sigma * Math.sqrt(2 * Math.PI)
        )
        - 0.5 * difference * difference
    );
}


function hmmTransitionMatrix() {
    const persistence = Math.min(
        Math.max(
            HMM_PERSISTENCE,
            0.5
        ),
        0.995
    );

    const movement = 1 - persistence;

    return [
        [
            persistence,
            movement * 0.40,
            movement * 0.40,
            movement * 0.20
        ],
        [
            movement * 0.43,
            persistence,
            movement * 0.05,
            movement * 0.52
        ],
        [
            movement * 0.43,
            movement * 0.05,
            persistence,
            movement * 0.52
        ],
        [
            movement * 0.55,
            movement * 0.225,
            movement * 0.225,
            persistence
        ]
    ];
}


function hmmEmissionLogLikelihoods(
    slopeZ,
    innovationZ
) {
    const absoluteInnovation =
        Math.abs(innovationZ);

    return [
        // Etat 0: faible pente et innovations ordinaires.
        gaussianLogPdf(
            slopeZ,
            0,
            0.48
        )
        + gaussianLogPdf(
            innovationZ,
            0,
            0.90
        ),

        // Etat 1: pente positive persistante.
        gaussianLogPdf(
            slopeZ,
            0.90,
            0.72
        )
        + gaussianLogPdf(
            innovationZ,
            0.10,
            1.25
        ),

        // Etat 2: pente négative persistante.
        gaussianLogPdf(
            slopeZ,
            -0.90,
            0.72
        )
        + gaussianLogPdf(
            innovationZ,
            -0.10,
            1.25
        ),

        // Etat 3: innovation anormalement grande / transition.
        gaussianLogPdf(
            slopeZ,
            0,
            1.80
        )
        + gaussianLogPdf(
            absoluteInnovation,
            2.60,
            1.35
        )
    ];
}


function normalizeLogProbabilities(
    logValues
) {
    const maximum =
        Math.max(...logValues);

    const exponentials =
        logValues.map(
            value =>
                Math.exp(
                    value - maximum
                )
        );

    const total =
        exponentials.reduce(
            (sum, value) =>
                sum + value,
            0
        );

    if (
        !Number.isFinite(total)
        || total <= 0
    ) {
        return [
            0.82,
            0.06,
            0.06,
            0.06
        ];
    }

    return exponentials.map(
        value => value / total
    );
}


function theoreticalActionForState(
    stateIndex,
    confidence
) {
    if (
        confidence
        < HMM_SIGNAL_THRESHOLD
    ) {
        return "ATTENTE / CONFIRMATION";
    }

    if (stateIndex === 1) {
        return "LONG / HOLD LONG";
    }

    if (stateIndex === 2) {
        return "SHORT / HOLD SHORT";
    }

    if (stateIndex === 3) {
        return "FLAT / RISK OFF";
    }

    return "ATTENTE / FLAT";
}


function updateOnlineHmm(
    slopeZ,
    innovationZ
) {
    const transition =
        hmmTransitionMatrix();

    const predicted =
        [0, 0, 0, 0];

    for (
        let destination = 0;
        destination < 4;
        destination++
    ) {
        for (
            let origin = 0;
            origin < 4;
            origin++
        ) {
            predicted[destination] +=
                single.hmmPosterior[origin]
                * transition[origin][destination];
        }
    }

    const emissions =
        hmmEmissionLogLikelihoods(
            slopeZ,
            innovationZ
        );

    const posterior =
        normalizeLogProbabilities(
            predicted.map(
                (probability, index) =>
                    Math.log(
                        Math.max(
                            probability,
                            1e-15
                        )
                    )
                    + emissions[index]
            )
        );

    single.hmmPosterior =
        posterior;

    let dominantState = 0;

    for (
        let index = 1;
        index < posterior.length;
        index++
    ) {
        if (
            posterior[index]
            > posterior[dominantState]
        ) {
            dominantState = index;
        }
    }

    const confidence =
        posterior[dominantState];

    if (
        dominantState
        === single.hmmCandidate
    ) {
        single.hmmCandidateCount += 1;
    } else {
        single.hmmCandidate =
            dominantState;

        single.hmmCandidateCount = 1;
    }

    const requiredConfirmations =
        dominantState === 3
            ? 1
            : 3;

    const shockThreshold =
        Math.max(
            0.50,
            HMM_SIGNAL_THRESHOLD - 0.10
        );

    const effectiveThreshold =
        dominantState === 3
            ? shockThreshold
            : HMM_SIGNAL_THRESHOLD;

    if (
        confidence >= effectiveThreshold
        && single.hmmCandidateCount
            >= requiredConfirmations
    ) {
        if (
            single.hmmConfirmedState
            === dominantState
        ) {
            single.hmmConfirmedDuration += 1;
        } else {
            single.hmmConfirmedState =
                dominantState;

            single.hmmConfirmedDuration = 1;
        }
    } else {
        single.hmmConfirmedDuration += 1;
    }

    const confirmedState =
        single.hmmConfirmedState;

    const confirmedConfidence =
        posterior[confirmedState];

    const action =
        theoreticalActionForState(
            confirmedState,
            confirmedConfidence
        );

    return {
        posterior,
        dominantState,
        confidence,
        confirmedState,
        confirmedConfidence,
        action,
        duration:
            single.hmmConfirmedDuration
    };
}


function singleKalmanUpdate(timestamp, price) {
    if (single.observed.length) {
        const difference =
            price
            - single.observed[
                single.observed.length - 1
            ];

        if (
            Number.isFinite(
                difference
            )
        ) {
            single.differences.push(
                difference
            );

            trimArray(
                single.differences,
                250
            );
        }
    }

    const baseVariance = Math.max(
        variance(single.differences),
        price * price * 1e-12,
        1e-10
    );

    const qMultiplier =
        Math.pow(
            10,
            (REACTIVITY - 5) / 2
        );

    const rMultiplier =
        Math.pow(
            10,
            (6 - OBSERVATION_TRUST) / 2
        );

    const qLevel =
        baseVariance
        * 0.035
        * qMultiplier;

    const qTrend =
        baseVariance
        * 0.0015
        * qMultiplier;

    const measurementVariance =
        baseVariance
        * Math.max(
            rMultiplier,
            1e-4
        );

    let innovation = 0;

    let innovationVariance =
        baseVariance
        + measurementVariance;

    if (single.state === null) {
        single.state = [
            price,
            0
        ];

        single.covariance = [
            [
                baseVariance * 10,
                0
            ],
            [
                0,
                baseVariance
            ]
        ];
    } else {
        let [
            level,
            trend
        ] = single.state;

        let [
            [
                p00,
                p01
            ],
            [
                p10,
                p11
            ]
        ] = single.covariance;

        const predictedLevel =
            level + trend;

        const predictedTrend =
            trend;

        const pp00 =
            p00
            + p01
            + p10
            + p11
            + qLevel;

        const pp01 =
            p01 + p11;

        const pp10 =
            p10 + p11;

        const pp11 =
            p11 + qTrend;

        innovation =
            price
            - predictedLevel;

        innovationVariance =
            pp00
            + measurementVariance;

        const k0 =
            pp00
            / innovationVariance;

        const k1 =
            pp10
            / innovationVariance;

        level =
            predictedLevel
            + k0 * innovation;

        trend =
            predictedTrend
            + k1 * innovation;

        const np00 =
            (1 - k0)
            * pp00;

        const np01 =
            (1 - k0)
            * pp01;

        const np10 =
            pp10
            - k1 * pp00;

        const np11 =
            pp11
            - k1 * pp01;

        const offDiagonal =
            (np01 + np10)
            / 2;

        single.state = [
            level,
            trend
        ];

        single.covariance = [
            [
                Math.max(
                    np00,
                    1e-14
                ),
                offDiagonal
            ],
            [
                offDiagonal,
                Math.max(
                    np11,
                    1e-14
                )
            ]
        ];
    }

    const level =
        single.state[0];

    const trend =
        single.state[1];

    const uncertainty =
        Math.sqrt(
            Math.max(
                single.covariance[0][0]
                + measurementVariance,
                0
            )
        );

    const innovationZ =
        innovation
        / Math.sqrt(
            Math.max(
                innovationVariance,
                1e-14
            )
        );

    const slopeZ =
        trend
        / Math.sqrt(
            Math.max(
                baseVariance,
                1e-14
            )
        );

    const uncertaintyRatio =
        uncertainty
        / Math.max(
            Math.abs(price),
            1e-12
        );

    single.timestamps.push(
        timestamp
    );

    single.observed.push(
        price
    );

    single.filtered.push(
        level
    );

    single.trend.push(
        trend
    );

    single.lower.push(
        level
        - 1.96 * uncertainty
    );

    single.upper.push(
        level
        + 1.96 * uncertainty
    );

    single.innovationZ.push(
        innovationZ
    );

    single.slopeZ.push(
        slopeZ
    );

    single.uncertaintyRatio.push(
        uncertaintyRatio
    );

    if (IS_HYBRID) {
        let hmmResult;

        if (
            single.observed.length < 12
        ) {
            hmmResult = {
                posterior: [
                    0.82,
                    0.06,
                    0.06,
                    0.06
                ],
                confirmedState: 0,
                confirmedConfidence: 0.82,
                action:
                    "WARM-UP / ATTENTE",
                duration:
                    single.observed.length
            };
        } else {
            hmmResult =
                updateOnlineHmm(
                    slopeZ,
                    innovationZ
                );
        }

        single.hmmNoise.push(
            hmmResult.posterior[0]
        );

        single.hmmUp.push(
            hmmResult.posterior[1]
        );

        single.hmmDown.push(
            hmmResult.posterior[2]
        );

        single.hmmShock.push(
            hmmResult.posterior[3]
        );

        single.hmmRegime.push(
            hmmResult.confirmedState
        );

        single.hmmConfidence.push(
            hmmResult.confirmedConfidence
        );

        single.hmmAction.push(
            hmmResult.action
        );

        single.hmmDuration.push(
            hmmResult.duration
        );
    }

    [
        single.timestamps,
        single.observed,
        single.filtered,
        single.trend,
        single.lower,
        single.upper,
        single.innovationZ,
        single.slopeZ,
        single.uncertaintyRatio,
        single.hmmNoise,
        single.hmmUp,
        single.hmmDown,
        single.hmmShock,
        single.hmmRegime,
        single.hmmConfidence,
        single.hmmAction,
        single.hmmDuration
    ].forEach(
        array =>
            trimArray(array)
    );

    dirty = true;
}


function singleForecast() {
    if (single.state === null || !single.timestamps.length) {
        return {x: [], level: [], lower: [], upper: []};
    }

    const interval = estimatedTickInterval(single.timestamps);
    const lastTimestamp = single.timestamps[single.timestamps.length - 1].getTime();

    let state = [...single.state];
    let covariance = [
        [...single.covariance[0]],
        [...single.covariance[1]]
    ];

    const price = single.observed[single.observed.length - 1];
    const baseVariance = Math.max(
        variance(single.differences),
        price * price * 1e-12,
        1e-10
    );

    const qMultiplier = Math.pow(10, (REACTIVITY - 5) / 2);
    const rMultiplier = Math.pow(10, (6 - OBSERVATION_TRUST) / 2);
    const qLevel = baseVariance * 0.035 * qMultiplier;
    const qTrend = baseVariance * 0.0015 * qMultiplier;
    const measurementVariance = baseVariance * Math.max(rMultiplier, 1e-4);

    const result = {
        x: [single.timestamps[single.timestamps.length - 1]],
        level: [state[0]],
        lower: [single.lower[single.lower.length - 1]],
        upper: [single.upper[single.upper.length - 1]]
    };

    for (let step = 1; step <= FORECAST_TICKS; step++) {
        state = [state[0] + state[1], state[1]];

        const [[p00, p01], [p10, p11]] = covariance;
        const pp00 = p00 + p01 + p10 + p11 + qLevel;
        const pp01 = p01 + p11;
        const pp10 = p10 + p11;
        const pp11 = p11 + qTrend;
        covariance = [[pp00, pp01], [pp10, pp11]];

        const uncertainty = Math.sqrt(
            Math.max(pp00 + measurementVariance, 0)
        );

        result.x.push(new Date(lastTimestamp + step * interval));
        result.level.push(state[0]);
        result.lower.push(state[0] - 1.96 * uncertainty);
        result.upper.push(state[0] + 1.96 * uncertainty);
    }

    return result;
}

function renderSingle() {
    const forecast = singleForecast();

    const traces = [
        {
            x: single.timestamps,
            y: single.upper,
            type: "scatter",
            mode: "lines",
            line: {width: 0},
            hoverinfo: "skip",
            showlegend: false
        },
        {
            x: single.timestamps,
            y: single.lower,
            type: "scatter",
            mode: "lines",
            line: {width: 0},
            fill: "tonexty",
            fillcolor: COLORS.filterBand,
            name: "Incertitude filtrée 95%",
            hoverinfo: "skip"
        },
        {
            x: single.timestamps,
            y: single.observed,
            type: "scattergl",
            mode: "markers",
            name: "Ticks observés",
            marker: {size: 4, color: COLORS.raw, opacity: 0.82},
            hovertemplate: "%{x|%H:%M:%S.%L}<br>Tick : %{y:,.5f}<extra></extra>"
        },
        {
            x: single.timestamps,
            y: single.filtered,
            type: "scattergl",
            mode: "lines",
            name: "Prix latent Kalman",
            line: {color: COLORS.filter, width: 2.3},
            hovertemplate: "%{x|%H:%M:%S.%L}<br>Filtré : %{y:,.5f}<extra></extra>"
        },
        {
            x: forecast.x,
            y: forecast.upper,
            type: "scatter",
            mode: "lines",
            line: {width: 0},
            hoverinfo: "skip",
            showlegend: false
        },
        {
            x: forecast.x,
            y: forecast.lower,
            type: "scatter",
            mode: "lines",
            line: {width: 0},
            fill: "tonexty",
            fillcolor: COLORS.forecastBand,
            name: "Cône de prévision 95%",
            hoverinfo: "skip"
        },
        {
            x: forecast.x,
            y: forecast.level,
            type: "scattergl",
            mode: "lines",
            name: "Prévision ticks",
            line: {color: COLORS.forecast, width: 2, dash: "dash"},
            hovertemplate: "%{x|%H:%M:%S.%L}<br>Prévision : %{y:,.5f}<extra></extra>"
        }
    ];

    const layout = commonLayout(
        `${ASSET_Y} · ${SYMBOL_Y} · tick-by-tick Kalman`,
        `tick-single-${SYMBOL_Y}`
    );

    if (single.timestamps.length) {
        const lastTimestamp = single.timestamps[single.timestamps.length - 1];
        layout.shapes = [{
            type: "line",
            x0: lastTimestamp,
            x1: lastTimestamp,
            yref: "paper",
            y0: 0,
            y1: 1,
            line: {color: "#34404e", width: 1, dash: "dot"}
        }];
    }

    Plotly.react("singleChart", traces, layout, plotConfig);

    if (single.observed.length) {
        const last = single.observed[single.observed.length - 1];
        const filtered = single.filtered[single.filtered.length - 1];
        const trend = single.trend[single.trend.length - 1];
        const forecastLast = forecast.level.length
            ? forecast.level[forecast.level.length - 1]
            : NaN;
        const forecastChange = Number.isFinite(forecastLast)
            ? (forecastLast / last - 1) * 100
            : NaN;
        const estimatedMs = estimatedTickInterval(single.timestamps) * FORECAST_TICKS;

        setMetric(0, "Dernier tick", formatPrice(last), SYMBOL_Y);
        setMetric(
            1,
            "Prix filtré",
            formatPrice(filtered),
            `${formatSigned((filtered / last - 1) * 100)}% vs tick`,
            filtered >= last ? COLORS.green : COLORS.red
        );
        setMetric(2, "Tendance / tick", formatSigned(trend, 5), "local linear trend");
        setMetric(
            3,
            `Prévision ${FORECAST_TICKS} ticks`,
            formatPrice(forecastLast),
            `${formatSigned(forecastChange)}% · ~${Math.max(1, Math.round(estimatedMs / 1000))} sec`,
            forecastChange >= 0 ? COLORS.green : COLORS.red
        );
        setMetric(4, "Activité live", `${liveTickArrivals.length} ticks/min`, `${single.observed.length} points conservés`);
    }
}

function regimeBackgroundShapes() {
    if (
        single.timestamps.length < 2
        || !single.hmmRegime.length
    ) {
        return [];
    }

    const shapes = [];
    let startIndex = 0;

    for (
        let index = 1;
        index <= single.hmmRegime.length;
        index++
    ) {
        const currentState =
            single.hmmRegime[
                startIndex
            ];

        const regimeChanged =
            index
            === single.hmmRegime.length
            || single.hmmRegime[index]
                !== currentState;

        if (!regimeChanged) {
            continue;
        }

        const startTimestamp =
            single.timestamps[
                startIndex
            ];

        const endTimestamp =
            index
            < single.timestamps.length
                ? single.timestamps[index]
                : single.timestamps[
                    single.timestamps.length - 1
                ];

        shapes.push({
            type: "rect",
            xref: "x",
            yref: "paper",
            x0: startTimestamp,
            x1: endTimestamp,
            y0: 0,
            y1: 1,
            fillcolor:
                HMM_STATES[
                    currentState
                ].fill,
            line: {
                width: 0
            },
            layer: "below"
        });

        startIndex = index;
    }

    return shapes.slice(-100);
}


function renderHybrid() {
    const forecast =
        singleForecast();

    const priceTraces = [
        {
            x: single.timestamps,
            y: single.upper,
            type: "scatter",
            mode: "lines",
            line: {
                width: 0
            },
            hoverinfo: "skip",
            showlegend: false
        },
        {
            x: single.timestamps,
            y: single.lower,
            type: "scatter",
            mode: "lines",
            line: {
                width: 0
            },
            fill: "tonexty",
            fillcolor:
                COLORS.filterBand,
            name:
                "Incertitude Kalman 95%",
            hoverinfo: "skip"
        },
        {
            x: single.timestamps,
            y: single.observed,
            type: "scattergl",
            mode: "markers",
            name: "Ticks observés",
            marker: {
                size: 3.5,
                color: COLORS.raw,
                opacity: 0.62
            },
            hovertemplate:
                "%{x|%H:%M:%S.%L}"
                + "<br>Tick : %{y:,.5f}"
                + "<extra></extra>"
        },
        {
            x: single.timestamps,
            y: single.filtered,
            type: "scattergl",
            mode: "lines",
            name: "Prix latent Kalman",
            line: {
                color: COLORS.filter,
                width: 2.4
            },
            hovertemplate:
                "%{x|%H:%M:%S.%L}"
                + "<br>Filtré : %{y:,.5f}"
                + "<extra></extra>"
        }
    ];

    if (
        forecast.x.length > 1
    ) {
        priceTraces.push(
            {
                x: forecast.x,
                y: forecast.upper,
                type: "scatter",
                mode: "lines",
                line: {
                    width: 0
                },
                hoverinfo: "skip",
                showlegend: false
            },
            {
                x: forecast.x,
                y: forecast.lower,
                type: "scatter",
                mode: "lines",
                line: {
                    width: 0
                },
                fill: "tonexty",
                fillcolor:
                    COLORS.forecastBand,
                name:
                    "Prévision 95%",
                hoverinfo: "skip"
            },
            {
                x: forecast.x,
                y: forecast.level,
                type: "scattergl",
                mode: "lines",
                name:
                    "Projection Kalman",
                line: {
                    color: COLORS.forecast,
                    width: 1.8,
                    dash: "dash"
                }
            }
        );
    }

    const priceLayout =
        commonLayout(
            `${ASSET_Y} · Prix latent et régimes HMM`,
            `hybrid-price-${SYMBOL_Y}`
        );

    priceLayout.shapes =
        regimeBackgroundShapes();

    Plotly.react(
        "pairPriceChart",
        priceTraces,
        priceLayout,
        plotConfig
    );

    const probabilityTraces = [
        {
            x: single.timestamps,
            y: single.hmmNoise.map(
                value => value * 100
            ),
            type: "scattergl",
            mode: "lines",
            name: "Bruit / range",
            line: {
                color: COLORS.noise,
                width: 1.7
            }
        },
        {
            x: single.timestamps,
            y: single.hmmUp.map(
                value => value * 100
            ),
            type: "scattergl",
            mode: "lines",
            name: "Hausse",
            line: {
                color: COLORS.up,
                width: 2
            }
        },
        {
            x: single.timestamps,
            y: single.hmmDown.map(
                value => value * 100
            ),
            type: "scattergl",
            mode: "lines",
            name: "Baisse",
            line: {
                color: COLORS.down,
                width: 2
            }
        },
        {
            x: single.timestamps,
            y: single.hmmShock.map(
                value => value * 100
            ),
            type: "scattergl",
            mode: "lines",
            name: "Choc",
            line: {
                color: COLORS.shock,
                width: 1.8
            }
        }
    ];

    const probabilityLayout =
        commonLayout(
            "Probabilités des régimes HMM",
            `hybrid-probabilities-${SYMBOL_Y}`
        );

    probabilityLayout.yaxis.range =
        [0, 100];

    probabilityLayout.yaxis.ticksuffix =
        "%";

    probabilityLayout.shapes = [
        {
            type: "line",
            xref: "paper",
            x0: 0,
            x1: 1,
            y0:
                HMM_SIGNAL_THRESHOLD
                * 100,
            y1:
                HMM_SIGNAL_THRESHOLD
                * 100,
            line: {
                color:
                    COLORS.forecast,
                width: 1,
                dash: "dot"
            }
        }
    ];

    Plotly.react(
        "pairBetaChart",
        probabilityTraces,
        probabilityLayout,
        plotConfig
    );

    const featureTraces = [
        {
            x: single.timestamps,
            y: single.slopeZ,
            type: "scattergl",
            mode: "lines",
            name: "Pente normalisée",
            line: {
                color: COLORS.filter,
                width: 1.9
            }
        },
        {
            x: single.timestamps,
            y: single.innovationZ,
            type: "scattergl",
            mode: "lines",
            name: "Innovation normalisée",
            line: {
                color: COLORS.raw,
                width: 1.5
            }
        }
    ];

    const featureLayout =
        commonLayout(
            "Variables transmises au HMM",
            `hybrid-features-${SYMBOL_Y}`
        );

    featureLayout.shapes = [];

    for (
        const level of [
            -2,
            -1,
            0,
            1,
            2
        ]
    ) {
        featureLayout.shapes.push({
            type: "line",
            xref: "paper",
            x0: 0,
            x1: 1,
            y0: level,
            y1: level,
            line: {
                color:
                    level === 0
                        ? COLORS.muted
                        : (
                            Math.abs(level) === 2
                                ? COLORS.red
                                : COLORS.forecast
                        ),
                width:
                    level === 0
                        ? 1
                        : 0.7,
                dash:
                    level === 0
                        ? "solid"
                        : "dot"
            },
            opacity: 0.55
        });
    }

    Plotly.react(
        "pairResidualChart",
        featureTraces,
        featureLayout,
        plotConfig
    );

    if (
        single.observed.length
        && single.hmmRegime.length
    ) {
        const lastIndex =
            single.observed.length - 1;

        const price =
            single.observed[lastIndex];

        const filtered =
            single.filtered[lastIndex];

        const stateIndex =
            single.hmmRegime[
                single.hmmRegime.length - 1
            ];

        const confidence =
            single.hmmConfidence[
                single.hmmConfidence.length - 1
            ];

        const action =
            single.hmmAction[
                single.hmmAction.length - 1
            ];

        const duration =
            single.hmmDuration[
                single.hmmDuration.length - 1
            ];

        const state =
            HMM_STATES[stateIndex];

        const slope =
            single.slopeZ[
                single.slopeZ.length - 1
            ];

        const innovation =
            single.innovationZ[
                single.innovationZ.length - 1
            ];

        setMetric(
            0,
            "Dernier tick",
            formatPrice(price),
            SYMBOL_Y
        );

        setMetric(
            1,
            "Prix latent",
            formatPrice(filtered),
            `${formatSigned(
                (
                    filtered / price
                    - 1
                ) * 100
            )}% vs tick`,
            filtered >= price
                ? COLORS.green
                : COLORS.red
        );

        setMetric(
            2,
            "Régime HMM",
            state.label,
            `${(
                confidence * 100
            ).toFixed(1)}% de probabilité`,
            state.color
        );

        setMetric(
            3,
            "Pente / innovation",
            `${formatSigned(
                slope,
                2
            )} / ${formatSigned(
                innovation,
                2
            )}`,
            "unités d'écart-type"
        );

        setMetric(
            4,
            "Signal théorique",
            action,
            `${duration} ticks dans le régime`,
            state.color
        );
    }
}


// -----------------------------------------------------------------------------
// PAIR ENGINE
// -----------------------------------------------------------------------------

const pair = {
    replayTicks: {},
    latest: {},
    received: {},
    replayDone: new Set(),
    replayCompleteCount: 0,
    initialized: false,
    initializing: false,
    firstPairTickAt: null,
    lastProcessedSignature: null,
    previousY: null,
    previousX: null,
    warmup: [],
    regression: null,
    rawTimestamps: [],
    rawNormalizedY: [],
    rawNormalizedX: [],
    timestamps: [],
    normalizedY: [],
    normalizedX: [],
    beta: [],
    betaLower: [],
    betaUpper: [],
    residual: [],
    zscore: [],
    baseY: null,
    baseX: null,
    liveTimer: null,
    initTimer: null
};

pair.replayTicks[SYMBOL_Y] = [];
pair.received[SYMBOL_Y] = 0;

if (SYMBOL_X) {
    pair.replayTicks[SYMBOL_X] = [];
    pair.received[SYMBOL_X] = 0;
}

function ols(observations) {
    const n = observations.length;
    let sumX = 0;
    let sumY = 0;
    let sumXX = 0;
    let sumXY = 0;

    for (const observation of observations) {
        sumX += observation.x;
        sumY += observation.y;
        sumXX += observation.x * observation.x;
        sumXY += observation.x * observation.y;
    }

    const denominator = n * sumXX - sumX * sumX;
    const beta = Math.abs(denominator) > 1e-16
        ? (n * sumXY - sumX * sumY) / denominator
        : 1;
    const alpha = (sumY - beta * sumX) / n;

    const residuals = observations.map(observation =>
        observation.y - alpha - beta * observation.x
    );

    return {
        alpha,
        beta,
        residualVariance: Math.max(variance(residuals), 1e-12)
    };
}

function initializeRegression() {
    const estimate = ols(pair.warmup);
    const qMultiplier = Math.pow(10, (REACTIVITY - 5) / 2);
    const rMultiplier = Math.pow(10, (6 - OBSERVATION_TRUST) / 2);

    const levelModel = IS_RV;
    const qAlpha = levelModel
        ? estimate.residualVariance * 0.0008 * qMultiplier
        : estimate.residualVariance * 0.01 * qMultiplier;
    const qBeta = levelModel
        ? Math.max(estimate.residualVariance * 0.00015, 1e-9) * qMultiplier
        : 1e-5 * qMultiplier;

    pair.regression = {
        alpha: estimate.alpha,
        beta: estimate.beta,
        p00: 0.1,
        p01: 0,
        p10: 0,
        p11: 0.1,
        qAlpha: Math.max(qAlpha, 1e-12),
        qBeta: Math.max(qBeta, 1e-12),
        r: estimate.residualVariance * Math.max(rMultiplier, 1e-4)
    };
}

function regressionUpdate(y, x) {
    if (!pair.regression) return null;

    const model = pair.regression;
    const pp00 = model.p00 + model.qAlpha;
    const pp01 = model.p01;
    const pp10 = model.p10;
    const pp11 = model.p11 + model.qBeta;

    const predicted = model.alpha + model.beta * x;
    const innovation = y - predicted;
    const innovationVariance = pp00 + x * (pp01 + pp10) + x * x * pp11 + model.r;

    const k0 = (pp00 + pp01 * x) / innovationVariance;
    const k1 = (pp10 + pp11 * x) / innovationVariance;

    model.alpha += k0 * innovation;
    model.beta += k1 * innovation;

    const np00 = (1 - k0) * pp00 - k0 * x * pp10;
    const np01 = (1 - k0) * pp01 - k0 * x * pp11;
    const np10 = -k1 * pp00 + (1 - k1 * x) * pp10;
    const np11 = -k1 * pp01 + (1 - k1 * x) * pp11;
    const offDiagonal = (np01 + np10) / 2;

    model.p00 = Math.max(np00, 1e-14);
    model.p01 = offDiagonal;
    model.p10 = offDiagonal;
    model.p11 = Math.max(np11, 1e-14);

    const residual = y - model.alpha - model.beta * x;
    const betaError = Math.sqrt(model.p11);

    return {
        alpha: model.alpha,
        beta: model.beta,
        betaLower: model.beta - 1.96 * betaError,
        betaUpper: model.beta + 1.96 * betaError,
        residual
    };
}

function currentZscore() {
    if (pair.residual.length < 10) return NaN;
    const windowValues = pair.residual.slice(-Z_WINDOW);
    const average = mean(windowValues);
    const std = standardDeviation(windowValues);
    if (!Number.isFinite(std) || std <= 1e-12) return NaN;
    return (windowValues[windowValues.length - 1] - average) / std;
}

function pairObservation(timestamp, priceY, priceX) {
    if (
        !Number.isFinite(priceY)
        || !Number.isFinite(priceX)
        || priceY <= 0
        || priceX <= 0
    ) {
        return;
    }

    if (pair.baseY === null) {
        pair.baseY = priceY;
        pair.baseX = priceX;
    }

    // The raw synchronized-price chart is independent from the Kalman warm-up.
    // This makes the first chart visible immediately.
    pair.rawTimestamps.push(timestamp);
    pair.rawNormalizedY.push(
        priceY / pair.baseY * 100
    );
    pair.rawNormalizedX.push(
        priceX / pair.baseX * 100
    );

    [
        pair.rawTimestamps,
        pair.rawNormalizedY,
        pair.rawNormalizedX
    ].forEach(array => trimArray(array));

    dirty = true;

    let y;
    let x;

    if (IS_BETA) {
        if (
            pair.previousY === null
            || pair.previousX === null
        ) {
            pair.previousY = priceY;
            pair.previousX = priceX;

            statusBox.textContent =
                "Premier couple synchronisé reçu"
                + " · initialisation des rendements";

            return;
        }

        y = Math.log(
            priceY / pair.previousY
        );

        x = Math.log(
            priceX / pair.previousX
        );

        pair.previousY = priceY;
        pair.previousX = priceX;

        // A duplicated pair adds no information to a return regression.
        if (
            Math.abs(y) < 1e-14
            && Math.abs(x) < 1e-14
        ) {
            return;
        }
    } else {
        y = Math.log(priceY);
        x = Math.log(priceX);
    }

    if (
        !Number.isFinite(y)
        || !Number.isFinite(x)
    ) {
        return;
    }

    if (!pair.regression) {
        pair.warmup.push({y, x});

        statusBox.textContent =
            `Warm-up Kalman : `
            + `${pair.warmup.length}/${MIN_PAIR_WARMUP} observations`
            + ` · Y ${pair.received[SYMBOL_Y] || 0} ticks`
            + ` · X ${pair.received[SYMBOL_X] || 0} ticks`;

        if (
            pair.warmup.length
            < MIN_PAIR_WARMUP
        ) {
            return;
        }

        initializeRegression();
    }

    const update = regressionUpdate(
        y,
        x
    );

    if (!update) {
        return;
    }

    const displayedResidual =
        IS_RV
            ? update.residual * 100
            : update.residual * 10000;

    pair.timestamps.push(timestamp);
    pair.normalizedY.push(
        priceY / pair.baseY * 100
    );
    pair.normalizedX.push(
        priceX / pair.baseX * 100
    );
    pair.beta.push(update.beta);
    pair.betaLower.push(update.betaLower);
    pair.betaUpper.push(update.betaUpper);
    pair.residual.push(displayedResidual);
    pair.zscore.push(currentZscore());

    [
        pair.timestamps,
        pair.normalizedY,
        pair.normalizedX,
        pair.beta,
        pair.betaLower,
        pair.betaUpper,
        pair.residual,
        pair.zscore
    ].forEach(array => trimArray(array));

    dirty = true;
}

function canonicalPairSymbol(incomingSymbol) {
    const normalized = String(incomingSymbol || "").toUpperCase();

    if (normalized === String(SYMBOL_Y).toUpperCase()) {
        return SYMBOL_Y;
    }

    if (
        SYMBOL_X
        && normalized === String(SYMBOL_X).toUpperCase()
    ) {
        return SYMBOL_X;
    }

    return null;
}


function buildSynchronizedObservations() {
    const ticksY = pair.replayTicks[SYMBOL_Y] || [];
    const ticksX = pair.replayTicks[SYMBOL_X] || [];

    if (!ticksY.length || !ticksX.length) {
        return [];
    }

    let observations = [];

    if (SYNC_MS === 0) {
        const events = [];

        for (const tick of ticksY) {
            events.push({
                ...tick,
                symbol: SYMBOL_Y
            });
        }

        for (const tick of ticksX) {
            events.push({
                ...tick,
                symbol: SYMBOL_X
            });
        }

        events.sort(
            (a, b) =>
                a.timestamp.getTime()
                - b.timestamp.getTime()
        );

        let latestY = null;
        let latestX = null;
        let lastSignature = null;

        for (const event of events) {
            if (event.symbol === SYMBOL_Y) {
                latestY = event.price;
            }

            if (event.symbol === SYMBOL_X) {
                latestX = event.price;
            }

            if (latestY === null || latestX === null) {
                continue;
            }

            const signature =
                `${event.timestamp.getTime()}|${latestY}|${latestX}`;

            if (signature === lastSignature) {
                continue;
            }

            lastSignature = signature;

            observations.push({
                timestamp: event.timestamp,
                priceY: latestY,
                priceX: latestX
            });
        }
    } else {
        const bucketsY = new Map();
        const bucketsX = new Map();

        for (const tick of ticksY) {
            const bucket =
                Math.floor(
                    tick.timestamp.getTime()
                    / SYNC_MS
                ) * SYNC_MS;

            bucketsY.set(
                bucket,
                tick.price
            );
        }

        for (const tick of ticksX) {
            const bucket =
                Math.floor(
                    tick.timestamp.getTime()
                    / SYNC_MS
                ) * SYNC_MS;

            bucketsX.set(
                bucket,
                tick.price
            );
        }

        const buckets = Array.from(
            new Set([
                ...bucketsY.keys(),
                ...bucketsX.keys()
            ])
        ).sort(
            (a, b) => a - b
        );

        let latestY = null;
        let latestX = null;
        let previousPair = null;

        for (const bucket of buckets) {
            if (bucketsY.has(bucket)) {
                latestY = bucketsY.get(bucket);
            }

            if (bucketsX.has(bucket)) {
                latestX = bucketsX.get(bucket);
            }

            if (latestY === null || latestX === null) {
                continue;
            }

            const pairSignature =
                `${latestY}|${latestX}`;

            // Keep a new observation only when at least one market moved.
            if (pairSignature === previousPair) {
                continue;
            }

            previousPair = pairSignature;

            observations.push({
                timestamp: new Date(bucket),
                priceY: latestY,
                priceX: latestX
            });
        }
    }

    if (observations.length > MAX_POINTS * 2) {
        observations = observations.slice(
            -(MAX_POINTS * 2)
        );
    }

    return observations;
}


function synchronizeReplay(force=false) {
    if (
        pair.initialized
        || pair.initializing
        || IS_SINGLE
    ) {
        return;
    }

    const ticksY =
        pair.replayTicks[SYMBOL_Y]
        || [];

    const ticksX =
        pair.replayTicks[SYMBOL_X]
        || [];

    if (!ticksY.length || !ticksX.length) {
        statusBox.textContent =
            `Attente des deux flux`
            + ` · Y ${ticksY.length} ticks`
            + ` · X ${ticksX.length} ticks`;

        return;
    }

    const observations =
        buildSynchronizedObservations();

    const requiredObservations =
        IS_BETA
            ? MIN_PAIR_WARMUP + 2
            : MIN_PAIR_WARMUP + 1;

    if (
        observations.length
        < requiredObservations
        && !force
    ) {
        statusBox.textContent =
            `Synchronisation`
            + ` · ${observations.length}/${requiredObservations} observations`
            + ` · Y ${ticksY.length} ticks`
            + ` · X ${ticksX.length} ticks`;

        return;
    }

    if (observations.length < 3) {
        statusBox.textContent =
            "Pas assez de ticks communs entre les deux actifs.";
        return;
    }

    pair.initializing = true;

    // Reset the pair model before consuming the replay.
    pair.previousY = null;
    pair.previousX = null;
    pair.warmup = [];
    pair.regression = null;
    pair.rawTimestamps = [];
    pair.rawNormalizedY = [];
    pair.rawNormalizedX = [];
    pair.timestamps = [];
    pair.normalizedY = [];
    pair.normalizedX = [];
    pair.beta = [];
    pair.betaLower = [];
    pair.betaUpper = [];
    pair.residual = [];
    pair.zscore = [];
    pair.baseY = null;
    pair.baseX = null;

    for (const observation of observations) {
        pairObservation(
            observation.timestamp,
            observation.priceY,
            observation.priceX
        );
    }

    pair.initialized = true;
    pair.initializing = false;

    // Keep the last observed pair as the live starting point.
    const finalObservation =
        observations[
            observations.length - 1
        ];

    pair.latest[SYMBOL_Y] = {
        timestamp: finalObservation.timestamp,
        price: finalObservation.priceY
    };

    pair.latest[SYMBOL_X] = {
        timestamp: finalObservation.timestamp,
        price: finalObservation.priceX
    };

    pair.replayTicks[SYMBOL_Y] = [];
    pair.replayTicks[SYMBOL_X] = [];

    startLivePairTimer();

    if (pair.beta.length) {
        statusBox.textContent =
            `Moteur initialisé`
            + ` · ${observations.length} observations synchronisées`
            + ` · ${pair.beta.length} estimations Kalman`;
    } else {
        statusBox.textContent =
            `Initialisation partielle`
            + ` · ${observations.length} observations`
            + ` · attente de nouveaux ticks live`;
    }

    dirty = true;
}


function maybeInitializePair(force=false) {
    if (
        IS_SINGLE
        || pair.initialized
        || pair.initializing
    ) {
        return;
    }

    const countY =
        (pair.replayTicks[SYMBOL_Y] || []).length;

    const countX =
        (pair.replayTicks[SYMBOL_X] || []).length;

    if (!countY || !countX) {
        statusBox.textContent =
            `Réception des ticks`
            + ` · Y ${countY}`
            + ` · X ${countX}`;

        return;
    }

    const elapsedMs =
        pair.firstPairTickAt === null
            ? 0
            : Date.now() - pair.firstPairTickAt;

    const bothReplayDone =
        pair.replayDone.has(SYMBOL_Y)
        && pair.replayDone.has(SYMBOL_X);

    const enoughRawTicks =
        countY >= 25
        && countX >= 25;

    if (
        force
        || bothReplayDone
        || enoughRawTicks
        || elapsedMs >= 8000
    ) {
        synchronizeReplay(
            force || elapsedMs >= 15000
        );
    }
}


function processLatestPair(timestamp=null) {
    const latestY = pair.latest[SYMBOL_Y];
    const latestX = pair.latest[SYMBOL_X];
    if (!latestY || !latestX) return;

    const effectiveTimestamp = timestamp || new Date(Math.max(
        latestY.timestamp.getTime(),
        latestX.timestamp.getTime()
    ));

    const signature = `${effectiveTimestamp.getTime()}|${latestY.price}|${latestX.price}`;
    if (signature === pair.lastProcessedSignature) return;
    pair.lastProcessedSignature = signature;

    pairObservation(
        effectiveTimestamp,
        latestY.price,
        latestX.price
    );
}

function startLivePairTimer() {
    if (pair.liveTimer !== null || SYNC_MS === 0) return;

    pair.liveTimer = setInterval(() => {
        const now = new Date();
        const bucket = Math.floor(now.getTime() / SYNC_MS) * SYNC_MS;
        processLatestPair(new Date(bucket));
    }, Math.max(250, Math.min(SYNC_MS, 1000)));
}

function renderPair() {
    const priceTraces = [
        {
            x: pair.rawTimestamps,
            y: pair.rawNormalizedY,
            type: "scattergl",
            mode: "lines",
            name: ASSET_Y,
            line: {color: COLORS.filter, width: 2}
        },
        {
            x: pair.rawTimestamps,
            y: pair.rawNormalizedX,
            type: "scattergl",
            mode: "lines",
            name: ASSET_X,
            line: {color: COLORS.secondary, width: 2}
        }
    ];

    Plotly.react(
        "pairPriceChart",
        priceTraces,
        commonLayout(
            `${ASSET_Y} / ${ASSET_X} · ticks synchronisés · base 100`,
            `tick-pair-price-${SYMBOL_Y}-${SYMBOL_X}`
        ),
        plotConfig
    );

    const betaTraces = [
        {
            x: pair.timestamps,
            y: pair.betaUpper,
            type: "scatter",
            mode: "lines",
            line: {width: 0},
            hoverinfo: "skip",
            showlegend: false
        },
        {
            x: pair.timestamps,
            y: pair.betaLower,
            type: "scatter",
            mode: "lines",
            line: {width: 0},
            fill: "tonexty",
            fillcolor: COLORS.filterBand,
            name: "Intervalle 95%",
            hoverinfo: "skip"
        },
        {
            x: pair.timestamps,
            y: pair.beta,
            type: "scattergl",
            mode: "lines",
            name: IS_BETA ? "Bêta Kalman" : "Hedge ratio Kalman",
            line: {color: COLORS.filter, width: 2.2}
        }
    ];

    const betaLayout = commonLayout(
        IS_BETA ? "Bêta dynamique" : "Hedge ratio dynamique",
        `tick-pair-beta-${SYMBOL_Y}-${SYMBOL_X}-${MODE}`
    );

    if (!pair.beta.length) {
        betaLayout.annotations = [{
            xref: "paper",
            yref: "paper",
            x: 0.5,
            y: 0.5,
            text:
                `Warm-up du Kalman`
                + `<br>${pair.warmup.length}/${MIN_PAIR_WARMUP} observations exploitables`,
            showarrow: false,
            align: "center",
            font: {
                color: COLORS.muted,
                size: 13
            }
        }];
    }

    Plotly.react(
        "pairBetaChart",
        betaTraces,
        betaLayout,
        plotConfig
    );

    const residualLayout = commonLayout(
        IS_BETA ? "Z-score du résiduel" : "Z-score du spread relative value",
        `tick-pair-z-${SYMBOL_Y}-${SYMBOL_X}-${MODE}`
    );

    residualLayout.shapes = [-2, -1, 0, 1, 2].map(level => ({
        type: "line",
        xref: "paper",
        x0: 0,
        x1: 1,
        y0: level,
        y1: level,
        line: {
            color: level === 0 ? COLORS.muted : (Math.abs(level) === 2 ? COLORS.red : COLORS.forecast),
            width: 1,
            dash: level === 0 ? "solid" : "dot"
        },
        opacity: 0.65
    }));

    const residualTraces = [{
        x: pair.timestamps,
        y: pair.zscore,
        type: "scattergl",
        mode: "lines",
        name: "Z-score",
        line: {color: COLORS.raw, width: 2}
    }];

    if (!pair.zscore.some(value => Number.isFinite(value))) {
        residualLayout.annotations = [{
            xref: "paper",
            yref: "paper",
            x: 0.5,
            y: 0.5,
            text:
                pair.beta.length
                    ? "Le z-score nécessite encore plusieurs résiduels"
                    : "Le z-score apparaîtra après le warm-up du Kalman",
            showarrow: false,
            align: "center",
            font: {
                color: COLORS.muted,
                size: 13
            }
        }];
    }

    Plotly.react(
        "pairResidualChart",
        residualTraces,
        residualLayout,
        plotConfig
    );

    if (pair.beta.length) {
        const lastIndex = pair.beta.length - 1;
        const beta = pair.beta[lastIndex];
        const residual = pair.residual[lastIndex];
        const z = pair.zscore[lastIndex];
        const latestY = pair.latest[SYMBOL_Y];
        const latestX = pair.latest[SYMBOL_X];

        const zColor = Number.isFinite(z)
            ? (Math.abs(z) >= 2 ? COLORS.red : (Math.abs(z) >= 1 ? COLORS.forecast : COLORS.green))
            : COLORS.text;

        setMetric(0, "Dernier Y", latestY ? formatPrice(latestY.price) : "—", SYMBOL_Y);
        setMetric(
            1,
            IS_BETA ? "Bêta dynamique" : "Hedge ratio",
            beta.toFixed(4),
            `${pair.timestamps.length} estimations · ${pair.rawTimestamps.length} couples`
        );
        setMetric(2, "Dernier X", latestX ? formatPrice(latestX.price) : "—", SYMBOL_X);
        setMetric(3, IS_BETA ? "Résiduel" : "Spread", formatSigned(residual, 3), IS_BETA ? "bps" : "% log");
        setMetric(4, "Z-score", Number.isFinite(z) ? formatSigned(z, 2) : "—", `${liveTickArrivals.length} ticks/min`, zColor);
    }
}

// -----------------------------------------------------------------------------
// PLOT CONTROL
// -----------------------------------------------------------------------------

function activeCharts() {
    if (IS_SMOOTH) {
        return [
            document.getElementById(
                "singleChart"
            )
        ];
    }

    return [
        document.getElementById(
            "pairPriceChart"
        ),
        document.getElementById(
            "pairBetaChart"
        ),
        document.getElementById(
            "pairResidualChart"
        )
    ];
}

function setDragMode(mode) {
    activeCharts().forEach(chart => Plotly.relayout(chart, {dragmode: mode}));
}

document.getElementById("panButton").onclick = () => setDragMode("pan");
document.getElementById("zoomButton").onclick = () => setDragMode("zoom");
document.getElementById("resetButton").onclick = () => {
    activeCharts().forEach(chart => Plotly.relayout(chart, {
        "xaxis.autorange": true,
        "yaxis.autorange": true,
        dragmode: "pan"
    }));
};
document.getElementById("fullscreenButton").onclick = async () => {
    const shell = document.getElementById("shell");
    if (!document.fullscreenElement) {
        await shell.requestFullscreen();
    } else {
        await document.exitFullscreen();
    }
};

function render() {
    if (!dirty) {
        return;
    }

    dirty = false;

    if (IS_SMOOTH) {
        renderSingle();
    } else if (IS_HYBRID) {
        renderHybrid();
    } else {
        renderPair();
    }
}

setInterval(render, 300);

// -----------------------------------------------------------------------------
// WEBSOCKET
// -----------------------------------------------------------------------------

function recordReplayCompletion(message) {
    const rawSymbol =
        message.symbol
        || (
            message.data
            && message.data.symbol
        );

    const symbol =
        canonicalPairSymbol(rawSymbol);

    if (symbol) {
        pair.replayDone.add(symbol);
    } else {
        pair.replayCompleteCount += 1;
    }

    const completeByCount =
        pair.replayCompleteCount >= 2;

    const completeBySymbols =
        pair.replayDone.has(SYMBOL_Y)
        && pair.replayDone.has(SYMBOL_X);

    if (
        !IS_SINGLE
        && (
            completeByCount
            || completeBySymbols
        )
    ) {
        maybeInitializePair(true);
    }
}


function handleTick(message) {
    const timestamp = parseTimestamp(
        message.ts
        ?? message.timestamp
    );

    const price = Number(
        message.price
    );

    if (
        Number.isNaN(
            timestamp.getTime()
        )
        || !Number.isFinite(price)
    ) {
        return;
    }

    registerLiveArrival(
        Boolean(message.replay)
    );

    if (IS_SINGLE) {
        single.latestTick = message;
        singleKalmanUpdate(
            timestamp,
            price
        );

        if (
            IS_HYBRID
            && single.hmmRegime.length
        ) {
            const currentState =
                single.hmmRegime[
                    single.hmmRegime.length - 1
                ];

            const currentConfidence =
                single.hmmConfidence[
                    single.hmmConfidence.length - 1
                ];

            statusBox.textContent =
                `${message.replay ? "Replay" : "Live"}`
                + ` · ${timestamp.toLocaleTimeString([], {hour12:false})}`
                + ` · ${single.observed.length} ticks`
                + ` · ${HMM_STATES[currentState].label}`
                + ` ${(
                    currentConfidence * 100
                ).toFixed(0)}%`;
        } else {
            statusBox.textContent =
                `${message.replay ? "Replay" : "Live"}`
                + ` · ${timestamp.toLocaleTimeString([], {hour12:false})}`
                + ` · ${single.observed.length} ticks`;
        }

        return;
    }

    const canonicalSymbol =
        canonicalPairSymbol(
            message.symbol
        );

    if (!canonicalSymbol) {
        return;
    }

    const tick = {
        timestamp,
        price
    };

    pair.latest[
        canonicalSymbol
    ] = tick;

    pair.received[
        canonicalSymbol
    ] = (
        pair.received[
            canonicalSymbol
        ]
        || 0
    ) + 1;

    if (pair.firstPairTickAt === null) {
        pair.firstPairTickAt =
            Date.now();
    }

    if (!pair.initialized) {
        const replayBuffer =
            pair.replayTicks[
                canonicalSymbol
            ];

        replayBuffer.push(tick);

        const replayLimit = Math.max(
            MAX_POINTS * 4,
            4000
        );

        if (
            replayBuffer.length
            > replayLimit
        ) {
            replayBuffer.splice(
                0,
                replayBuffer.length
                - replayLimit
            );
        }

        maybeInitializePair(false);

        statusBox.textContent =
            `${message.replay ? "Replay" : "Warm-up live"}`
            + ` · Y ${pair.received[SYMBOL_Y] || 0} ticks`
            + ` · X ${pair.received[SYMBOL_X] || 0} ticks`;

        return;
    }

    if (SYNC_MS === 0) {
        processLatestPair(
            timestamp
        );
    }

    statusBox.textContent =
        `${message.replay ? "Replay" : "Live"}`
        + ` · ${timestamp.toLocaleTimeString([], {hour12:false})}`
        + ` · Y ${pair.received[SYMBOL_Y] || 0}`
        + ` · X ${pair.received[SYMBOL_X] || 0}`
        + ` · sync ${SYNC_MS === 0 ? "tick" : (SYNC_MS / 1000) + "s"}`;
}


function connect() {
    clearTimeout(reconnectTimer);
    statusBox.textContent = "Connexion au WebSocket LSE…";

    socket = new WebSocket("wss://data-ws.londonstrategicedge.com");

    socket.onmessage = event => {
        const message = JSON.parse(event.data);

        if (message.type === "welcome") {
            socket.send(JSON.stringify({action: "auth", api_key: API_KEY}));
            return;
        }

        if (message.type === "authenticated") {
            connectedAt = new Date();
            const start = new Date(Date.now() - REPLAY_MINUTES * 60000).toISOString();
            const symbols = IS_SINGLE ? [SYMBOL_Y] : [SYMBOL_Y, SYMBOL_X];

            for (const symbol of symbols) {
                socket.send(JSON.stringify({action: "subscribe", symbol, start}));
            }

            statusBox.textContent = `Authentifié · replay ${REPLAY_MINUTES} min…`;
            return;
        }

        if (message.type === "replay_started") {
            statusBox.textContent = "Replay ticks en cours…";
            return;
        }

        if (message.type === "replay_complete") {
            if (IS_SINGLE) {
                statusBox.textContent = "Replay terminé · passage en live";
            } else {
                recordReplayCompletion(message);
            }
            return;
        }

        if (message.type === "tick") {
            handleTick(message);
            return;
        }

        if (message.type === "error") {
            statusBox.textContent = `Erreur : ${message.message || message.code || "inconnue"}`;

            if (!IS_SINGLE && ["REPLAY_NO_DATA", "REPLAY_UNAVAILABLE", "REPLAY_ERROR"].includes(message.code)) {
                pair.replayCompleteCount += 1;
                if (pair.replayCompleteCount >= 2 && !pair.initialized) synchronizeReplay();
            }
        }
    };

    socket.onerror = () => {
        statusBox.textContent = "Erreur de connexion WebSocket";
    };

    socket.onclose = () => {
        statusBox.textContent = "Connexion perdue · reconnexion…";
        reconnectTimer = setTimeout(connect, 2500);
    };
}

if (IS_SMOOTH) {
    singleCharts.style.display =
        "grid";

    pairCharts.style.display =
        "none";

    titleBox.textContent =
        `${MODE} · ${ASSET_Y} · ${SYMBOL_Y}`;

    Plotly.newPlot(
        "singleChart",
        [],
        commonLayout(
            "En attente des ticks…",
            `empty-${SYMBOL_Y}`
        ),
        plotConfig
    );
} else if (IS_HYBRID) {
    singleCharts.style.display =
        "none";

    pairCharts.style.display =
        "grid";

    titleBox.textContent =
        `${MODE} · ${ASSET_Y} · ${SYMBOL_Y}`;

    Plotly.newPlot(
        "pairPriceChart",
        [],
        commonLayout(
            "En attente des ticks Kalman…",
            "empty-hybrid-price"
        ),
        plotConfig
    );

    Plotly.newPlot(
        "pairBetaChart",
        [],
        commonLayout(
            "Warm-up des probabilités HMM…",
            "empty-hybrid-probabilities"
        ),
        plotConfig
    );

    Plotly.newPlot(
        "pairResidualChart",
        [],
        commonLayout(
            "Warm-up des variables de régime…",
            "empty-hybrid-features"
        ),
        plotConfig
    );
} else {
    singleCharts.style.display =
        "none";

    pairCharts.style.display =
        "grid";

    titleBox.textContent =
        `${MODE} · ${ASSET_Y} / ${ASSET_X}`;

    Plotly.newPlot(
        "pairPriceChart",
        [],
        commonLayout(
            "En attente des ticks synchronisés…",
            "empty-pair-price"
        ),
        plotConfig
    );

    Plotly.newPlot(
        "pairBetaChart",
        [],
        commonLayout(
            "Warm-up du Kalman…",
            "empty-pair-beta"
        ),
        plotConfig
    );

    Plotly.newPlot(
        "pairResidualChart",
        [],
        commonLayout(
            "Warm-up du z-score…",
            "empty-pair-z"
        ),
        plotConfig
    );
}

connect();

// Robust initialization: do not rely only on replay_complete payloads.
if (!IS_SINGLE) {
    pair.initTimer = setInterval(() => {
        if (pair.initialized) {
            clearInterval(pair.initTimer);
            pair.initTimer = null;
            return;
        }

        maybeInitializePair(false);
    }, 1000);

    setTimeout(() => {
        if (!pair.initialized) {
            maybeInitializePair(true);
        }
    }, 18000);
}

window.addEventListener("beforeunload", () => {
    if (socket) socket.close();
    if (pair.liveTimer !== null) clearInterval(pair.liveTimer);
    if (pair.initTimer !== null) clearInterval(pair.initTimer);
});

window.addEventListener("resize", () => {
    activeCharts().forEach(chart => Plotly.Plots.resize(chart));
});
</script>
</body>
</html>
"""

html = html_template.replace(
    "__SETTINGS__",
    json.dumps(settings),
)

component_height = 1080 if full_height else 820

components.html(
    html,
    height=component_height,
    scrolling=False,
)

st.caption(
    "Lissage : chaque tick est une observation. "
    "Bêta et relative value : les ticks bruts sont synchronisés avant calcul, "
    "car deux actifs ne publient pas exactement au même instant. "
    "Le mode ‘Chaque tick’ utilise le dernier prix connu de l’autre actif."
)
'''


if selected_page == "Workspace":
    execute_embedded_page(
        WORKSPACE_SOURCE,
        "flavio_monitor_workspace",
        "embedded_workspace.py",
    )

elif selected_page == "Bureau Larbou":
    execute_embedded_page(
        BUREAU_LARBOU_SOURCE,
        "flavio_monitor_bureau_larbou",
        "embedded_bureau_larbou.py",
    )

else:
    execute_embedded_page(
        KALMAN_LAB_SOURCE,
        "flavio_monitor_kalman_lab",
        "embedded_kalman_lab.py",
    )
