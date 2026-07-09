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

st.set_page_config(
    page_title="Flavio Monitor",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

SETUPS = {
    "Contexte": [
        "Ouverture",
        "Clôture veille",
    ],
    "VWAP": [
        "Ouverture",
        "Clôture veille",
        "VWAP séance",
        "Bandes VWAP",
        "VWAP glissante",
    ],
    "Microstructure": [
        "Mid-price",
        "VWAP séance",
    ],
}

ALL_OVERLAYS = [
    "Ouverture",
    "Clôture veille",
    "VWAP séance",
    "Bandes VWAP",
    "VWAP glissante",
    "Mid-price",
]


# =============================================================================
# STYLE
# =============================================================================

st.markdown(
    """
    <style>
        .stApp {
            background: #0e1117;
        }

        [data-testid="stSidebar"] {
            background: #111722;
            border-right: 1px solid #202938;
        }

        .block-container {
            max-width: 100%;
            padding-top: 1.05rem;
            padding-bottom: 1.5rem;
        }

        #MainMenu,
        footer {
            visibility: hidden;
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        .flavio-title {
            color: #f4f7fb;
            font-size: 2rem;
            font-weight: 720;
            letter-spacing: -0.04em;
            margin-bottom: 0;
        }

        .flavio-subtitle {
            color: #8490a3;
            font-size: 0.93rem;
            margin-top: 0.15rem;
            margin-bottom: 1.05rem;
        }

        .sidebar-brand {
            color: #f4f7fb;
            font-size: 1.35rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            margin-bottom: 1rem;
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

    api_key = st.text_input(
        "Clé API LSE",
        value=DEFAULT_API_KEY,
        type="password",
        placeholder="lse_live_...",
    )

if not api_key:
    st.markdown(
        '<div class="flavio-title">Flavio Monitor</div>',
        unsafe_allow_html=True,
    )
    st.info("Entre ta clé API LSE dans la barre latérale.")
    st.stop()


# =============================================================================
# LSE CATALOGUE
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
def resolve_lse_symbols(api_key_value: str) -> tuple[dict[str, str], list[str]]:
    client = LSE(api_key=api_key_value)
    catalogue = client.catalog()

    rows = [row for row in catalogue if row.get("symbol")]
    rows_by_symbol = {}

    for row in rows:
        rows_by_symbol.setdefault(str(row["symbol"]).upper(), row)

    resolved = {}
    unresolved = []

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
    st.error("Aucun des marchés demandés n’a été trouvé dans le catalogue LSE.")
    st.stop()


# =============================================================================
# SIDEBAR CONTROLS
# =============================================================================

with st.sidebar:
    selected_market = st.selectbox(
        "Marché",
        options=AVAILABLE_MARKETS,
    )

    selected_interval_label = st.selectbox(
        "Bougies Yahoo",
        options=list(YAHOO_INTERVALS.keys()),
        index=2,
    )

    selected_setup = st.selectbox(
        "Mode d’analyse",
        options=["Contexte", "VWAP", "Microstructure", "Personnalisé"],
        index=0,
    )

    if selected_setup == "Personnalisé":
        selected_overlays = st.multiselect(
            "Indicateurs",
            options=ALL_OVERLAYS,
            default=[
                "Ouverture",
                "Clôture veille",
                "VWAP séance",
            ],
        )
    else:
        selected_overlays = SETUPS[selected_setup]

    rolling_vwap_minutes = st.select_slider(
        "Fenêtre VWAP glissante",
        options=[5, 10, 15, 30, 60],
        value=15,
        disabled="VWAP glissante" not in selected_overlays,
    )

    focus_mode = st.toggle(
        "Mode focus live",
        value=False,
        help="Agrandit le graphique live et place le contexte en dessous.",
    )

    st.divider()

    selected_lse_symbol = LSE_SYMBOLS[selected_market]
    selected_yahoo_symbol = MARKETS[selected_market]["yahoo"]

    interval_settings = YAHOO_INTERVALS[selected_interval_label]
    selected_yahoo_interval = interval_settings["interval"]
    selected_yahoo_period = interval_settings["period"]

    st.caption(f"Flux live : `{selected_lse_symbol}`")
    st.caption(f"Historique : `{selected_yahoo_symbol}`")
    st.caption(f"Timeframe : {selected_interval_label}")

    with st.expander("Symboles LSE détectés"):
        for market_name, symbol in LSE_SYMBOLS.items():
            st.write(f"**{market_name}** — `{symbol}`")


# =============================================================================
# YAHOO CONTEXT
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
        raise ValueError("Aucune donnée intraday reçue de Yahoo.")

    intraday = intraday.rename(columns=str.title)
    intraday = intraday.dropna(subset=["Open", "High", "Low", "Close"])

    if intraday.empty:
        raise ValueError("Les bougies Yahoo reçues sont vides.")

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
    replay_floor = now_utc - timedelta(
        hours=MAX_REPLAY_HOURS,
        minutes=-1,
    )

    replay_is_partial = original_start < replay_floor
    effective_start = max(original_start, replay_floor)

    def numeric_list(column: str) -> list[float | None]:
        values = []
        for value in session[column].tolist():
            if pd.isna(value):
                values.append(None)
            else:
                values.append(float(value))
        return values

    return {
        "x": [
            pd.Timestamp(timestamp).isoformat()
            for timestamp in session.index
        ],
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


try:
    yahoo_context = load_yahoo_context(
        selected_yahoo_symbol,
        selected_yahoo_interval,
        selected_yahoo_period,
    )
except Exception as error:
    st.error(f"Yahoo Finance : {error}")
    st.stop()


# =============================================================================
# UNIFIED LIVE TERMINAL
# =============================================================================

def render_terminal(
    api_key_value: str,
    symbol: str,
    market_name: str,
    interval_label: str,
    context: dict[str, Any],
    overlays: list[str],
    rolling_minutes: int,
    focus: bool,
) -> None:
    payload = {
        "apiKey": api_key_value,
        "symbol": symbol,
        "marketName": market_name,
        "intervalLabel": interval_label,
        "context": context,
        "overlays": overlays,
        "rollingMinutes": rolling_minutes,
        "focus": focus,
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
            height: 100%;
            overflow: hidden;
            background: #0e1117;
            color: #d1d4dc;
            font-family:
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                Roboto,
                Arial,
                sans-serif;
        }

        * {
            box-sizing: border-box;
        }

        #shell {
            height: 100vh;
            display: flex;
            flex-direction: column;
            gap: 9px;
            background: #0e1117;
        }

        #metricGrid {
            display: grid;
            grid-template-columns: repeat(6, minmax(105px, 1fr));
            gap: 8px;
        }

        .metric {
            min-width: 0;
            min-height: 68px;
            padding: 9px 11px;
            background: #151b26;
            border: 1px solid #273142;
            border-radius: 9px;
        }

        .metricLabel {
            color: #8490a3;
            font-size: 11px;
            margin-bottom: 4px;
        }

        .metricValue {
            color: #f4f7fb;
            font-size: 18px;
            font-weight: 680;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .metricSub {
            min-height: 15px;
            margin-top: 3px;
            color: #8490a3;
            font-size: 10px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        #statusBar {
            min-height: 22px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 0 5px;
            color: #8490a3;
            font-size: 11px;
        }

        #statusLeft,
        #statusRight {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        #charts {
            flex: 1;
            min-height: 0;
            display: grid;
            grid-template-columns: __GRID_COLUMNS__;
            gap: 10px;
        }

        .chartCard {
            min-height: 0;
            display: flex;
            flex-direction: column;
            border: 1px solid #202938;
            border-radius: 10px;
            overflow: hidden;
            background: #0e1117;
        }

        .chartToolbar {
            min-height: 38px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            padding: 5px 8px;
            background: #111722;
            border-bottom: 1px solid #202938;
        }

        .chartToolbarTitle {
            color: #aab4c3;
            font-size: 11px;
            font-weight: 650;
            white-space: nowrap;
        }

        .chartToolbarActions {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 4px;
            flex-wrap: wrap;
        }

        .chartButton {
            appearance: none;
            border: 1px solid #334155;
            border-radius: 6px;
            background: #151b26;
            color: #cbd5e1;
            padding: 4px 7px;
            font-size: 10px;
            line-height: 1.1;
            cursor: pointer;
        }

        .chartButton:hover {
            background: #202938;
            border-color: #475569;
            color: #ffffff;
        }

        .chartButton.active {
            background: #263449;
            border-color: #60a5fa;
            color: #ffffff;
        }

        #liveChart,
        #contextChart {
            width: 100%;
            flex: 1;
            min-height: 0;
        }

        @media (max-width: 1100px) {
            #metricGrid {
                grid-template-columns: repeat(3, minmax(110px, 1fr));
            }

            #charts {
                grid-template-columns: 1fr;
                grid-template-rows: 1.3fr 1fr;
            }
        }
    </style>
</head>

<body>

<div id="shell">

    <div id="metricGrid">
        <div class="metric">
            <div class="metricLabel">Dernier</div>
            <div class="metricValue" id="lastPrice">—</div>
            <div class="metricSub" id="marketLabel">—</div>
        </div>

        <div class="metric">
            <div class="metricLabel">Jour</div>
            <div class="metricValue" id="dayPerformance">—</div>
            <div class="metricSub">vs clôture veille</div>
        </div>

        <div class="metric">
            <div class="metricLabel">Depuis l’ouverture</div>
            <div class="metricValue" id="openPerformance">—</div>
            <div class="metricSub" id="openReference">—</div>
        </div>

        <div class="metric">
            <div class="metricLabel">VWAP séance</div>
            <div class="metricValue" id="sessionVwap">—</div>
            <div class="metricSub" id="vwapQuality">En attente du volume</div>
        </div>

        <div class="metric">
            <div class="metricLabel">Spread</div>
            <div class="metricValue" id="spreadValue">—</div>
            <div class="metricSub" id="spreadBps">—</div>
        </div>

        <div class="metric">
            <div class="metricLabel">Activité</div>
            <div class="metricValue" id="tickVelocity">—</div>
            <div class="metricSub" id="realizedVol">Vol 1 min : —</div>
        </div>
    </div>

    <div id="statusBar">
        <div id="statusLeft">Connexion au flux…</div>
        <div id="statusRight">—</div>
    </div>

    <div id="charts">
        <div class="chartCard">
            <div class="chartToolbar">
                <div class="chartToolbarTitle">Flux live</div>
                <div class="chartToolbarActions">
                    <button class="chartButton active" id="liveZoomMode" onclick="setDragMode(liveChart, 'zoom', 'live')">Zone</button>
                    <button class="chartButton" id="livePanMode" onclick="setDragMode(liveChart, 'pan', 'live')">Déplacer</button>
                    <button class="chartButton" onclick="zoomAxis(liveChart, 'x', 0.65)">Temps +</button>
                    <button class="chartButton" onclick="zoomAxis(liveChart, 'x', 1.55)">Temps −</button>
                    <button class="chartButton" onclick="zoomAxis(liveChart, 'y', 0.65)">Prix +</button>
                    <button class="chartButton" onclick="zoomAxis(liveChart, 'y', 1.55)">Prix −</button>
                    <button class="chartButton" onclick="resetChart(liveChart)">Réinitialiser</button>
                </div>
            </div>
            <div id="liveChart"></div>
        </div>

        <div class="chartCard">
            <div class="chartToolbar">
                <div class="chartToolbarTitle">Contexte Yahoo</div>
                <div class="chartToolbarActions">
                    <button class="chartButton active" id="contextZoomMode" onclick="setDragMode(contextChart, 'zoom', 'context')">Zone</button>
                    <button class="chartButton" id="contextPanMode" onclick="setDragMode(contextChart, 'pan', 'context')">Déplacer</button>
                    <button class="chartButton" onclick="zoomAxis(contextChart, 'x', 0.65)">Temps +</button>
                    <button class="chartButton" onclick="zoomAxis(contextChart, 'x', 1.55)">Temps −</button>
                    <button class="chartButton" onclick="zoomAxis(contextChart, 'y', 0.65)">Prix +</button>
                    <button class="chartButton" onclick="zoomAxis(contextChart, 'y', 1.55)">Prix −</button>
                    <button class="chartButton" onclick="resetChart(contextChart)">Réinitialiser</button>
                </div>
            </div>
            <div id="contextChart"></div>
        </div>
    </div>

</div>

<script>
const SETTINGS = __SETTINGS__;

const API_KEY = SETTINGS.apiKey;
const SYMBOL = SETTINGS.symbol;
const MARKET_NAME = SETTINGS.marketName;
const INTERVAL_LABEL = SETTINGS.intervalLabel;
const CONTEXT = SETTINGS.context;
const OVERLAYS = new Set(SETTINGS.overlays);
const ROLLING_MINUTES = Number(SETTINGS.rollingMinutes);

const MAX_PLOT_POINTS = 5000;
const FLUSH_INTERVAL_MS = 200;
const ROLLING_WINDOW_MS = ROLLING_MINUTES * 60 * 1000;

const liveChart = document.getElementById("liveChart");
const contextChart = document.getElementById("contextChart");

const lastPriceBox = document.getElementById("lastPrice");
const dayPerformanceBox = document.getElementById("dayPerformance");
const openPerformanceBox = document.getElementById("openPerformance");
const sessionVwapBox = document.getElementById("sessionVwap");
const vwapQualityBox = document.getElementById("vwapQuality");
const spreadValueBox = document.getElementById("spreadValue");
const spreadBpsBox = document.getElementById("spreadBps");
const tickVelocityBox = document.getElementById("tickVelocity");
const realizedVolBox = document.getElementById("realizedVol");
const marketLabelBox = document.getElementById("marketLabel");
const openReferenceBox = document.getElementById("openReference");
const statusLeftBox = document.getElementById("statusLeft");
const statusRightBox = document.getElementById("statusRight");

marketLabelBox.textContent = MARKET_NAME + " · " + SYMBOL;
openReferenceBox.textContent = "Référence Yahoo : " + formatPrice(CONTEXT.session_open);

let socket = null;
let reconnectTimer = null;
let replayComplete = false;
let seenReplayTicks = new Set();

let totalTicks = 0;
let positiveVolumeTicks = 0;
let cumulativeVolume = 0;
let cumulativePriceVolume = 0;
let cumulativePriceSquaredVolume = 0;

let firstLsePrice = null;
let latestTick = null;
let latestPrice = null;

let rollingTicks = [];
let liveArrivalTimes = [];
let shortReturns = [];
let previousLivePrice = null;

let sourceAligned = null;
let referenceRatio = null;

let pending = {
    x: [],
    price: [],
    mid: [],
    sessionVwap: [],
    rollingVwap: [],
    upperBand: [],
    lowerBand: []
};


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
        return number.toLocaleString(
            undefined,
            {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }
        );
    }

    if (absolute >= 10) {
        return number.toLocaleString(
            undefined,
            {
                minimumFractionDigits: 2,
                maximumFractionDigits: 3
            }
        );
    }

    return number.toLocaleString(
        undefined,
        {
            minimumFractionDigits: 4,
            maximumFractionDigits: 5
        }
    );
}


function formatSignedPercent(value) {
    if (!isFiniteNumber(value)) {
        return "—";
    }

    const number = Number(value);
    return (number >= 0 ? "+" : "")
        + number.toFixed(2)
        + "%";
}


function setDirectionalValue(element, value, formattedText) {
    element.textContent = formattedText;

    if (!isFiniteNumber(value)) {
        element.style.color = "#f4f7fb";
    } else if (Number(value) > 0) {
        element.style.color = "#26a69a";
    } else if (Number(value) < 0) {
        element.style.color = "#ef5350";
    } else {
        element.style.color = "#f4f7fb";
    }
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
        return new Date(
            numericValue < 1e12
                ? numericValue * 1000
                : numericValue
        );
    }

    return new Date(value);
}


function overlayVisible(name) {
    return OVERLAYS.has(name);
}


function traceVisibility(name) {
    return overlayVisible(name) ? true : "legendonly";
}


const liveTraces = [
    {
        x: [],
        y: [],
        type: "scattergl",
        mode: "lines",
        name: "Prix",
        line: {
            color: "#f4f7fb",
            width: 2
        },
        hovertemplate:
            "%{x|%H:%M:%S.%L}<br>"
            + "Prix : %{y:,.5f}"
            + "<extra></extra>"
    },
    {
        x: [],
        y: [],
        type: "scattergl",
        mode: "lines",
        name: "Mid-price",
        visible: traceVisibility("Mid-price"),
        line: {
            color: "#8b5cf6",
            width: 1.3,
            dash: "dot"
        },
        hovertemplate:
            "%{x|%H:%M:%S.%L}<br>"
            + "Mid : %{y:,.5f}"
            + "<extra></extra>"
    },
    {
        x: [],
        y: [],
        type: "scattergl",
        mode: "lines",
        name: "VWAP séance",
        visible: traceVisibility("VWAP séance"),
        line: {
            color: "#f59e0b",
            width: 2
        },
        hovertemplate:
            "%{x|%H:%M:%S.%L}<br>"
            + "VWAP séance : %{y:,.5f}"
            + "<extra></extra>"
    },
    {
        x: [],
        y: [],
        type: "scattergl",
        mode: "lines",
        name: "VWAP " + ROLLING_MINUTES + " min",
        visible: traceVisibility("VWAP glissante"),
        line: {
            color: "#22d3ee",
            width: 1.6
        },
        hovertemplate:
            "%{x|%H:%M:%S.%L}<br>"
            + "VWAP glissante : %{y:,.5f}"
            + "<extra></extra>"
    },
    {
        x: [],
        y: [],
        type: "scattergl",
        mode: "lines",
        name: "VWAP +1σ",
        visible: traceVisibility("Bandes VWAP"),
        line: {
            color: "#f59e0b",
            width: 1,
            dash: "dash"
        },
        hoverinfo: "skip"
    },
    {
        x: [],
        y: [],
        type: "scattergl",
        mode: "lines",
        name: "VWAP -1σ",
        visible: traceVisibility("Bandes VWAP"),
        fill: overlayVisible("Bandes VWAP") ? "tonexty" : "none",
        fillcolor: "rgba(245, 158, 11, 0.08)",
        line: {
            color: "#f59e0b",
            width: 1,
            dash: "dash"
        },
        hoverinfo: "skip"
    }
];


const liveLayout = {
    template: "plotly_dark",
    paper_bgcolor: "#0e1117",
    plot_bgcolor: "#0e1117",

    margin: {
        l: 12,
        r: 102,
        t: 46,
        b: 31
    },

    title: {
        text: SYMBOL + " · flux live",
        x: 0.015,
        font: {
            size: 16,
            color: "#f4f7fb"
        }
    },

    showlegend: true,
    legend: {
        orientation: "h",
        x: 0,
        y: 1.04,
        xanchor: "left",
        yanchor: "bottom",
        font: {
            size: 10,
            color: "#aab4c3"
        },
        bgcolor: "rgba(0,0,0,0)"
    },

    hovermode: "x unified",
    dragmode: "zoom",
    uirevision: "live-" + SYMBOL,

    xaxis: {
        fixedrange: false,
        gridcolor: "#202938",
        zeroline: false,
        showspikes: true,
        spikecolor: "#8490a3",
        rangeslider: {
            visible: false
        },
        tickfont: {
            color: "#d1d4dc",
            size: 11
        }
    },

    yaxis: {
        gridcolor: "#202938",
        zeroline: false,
        side: "right",
        automargin: true,
        fixedrange: false,
        showticklabels: true,
        separatethousands: true,
        ticks: "outside",
        ticklen: 5,
        tickcolor: "#8490a3",
        showline: true,
        linecolor: "#3a4556",
        tickfont: {
            color: "#d1d4dc",
            size: 12
        }
    }
};


const contextTrace = {
    x: CONTEXT.x,
    open: CONTEXT.open,
    high: CONTEXT.high,
    low: CONTEXT.low,
    close: CONTEXT.close,
    type: "candlestick",
    name: MARKET_NAME,
    increasing: {
        line: {color: "#26a69a"},
        fillcolor: "#26a69a"
    },
    decreasing: {
        line: {color: "#ef5350"},
        fillcolor: "#ef5350"
    },
    hovertemplate:
        "%{x}<br>"
        + "O : %{open:,.4f}<br>"
        + "H : %{high:,.4f}<br>"
        + "L : %{low:,.4f}<br>"
        + "C : %{close:,.4f}"
        + "<extra></extra>"
};


const contextLayout = {
    template: "plotly_dark",
    paper_bgcolor: "#0e1117",
    plot_bgcolor: "#0e1117",

    margin: {
        l: 8,
        r: 78,
        t: 46,
        b: 31
    },

    title: {
        text:
            MARKET_NAME
            + " · "
            + INTERVAL_LABEL
            + " · "
            + CONTEXT.session_date,
        x: 0.015,
        font: {
            size: 15,
            color: "#f4f7fb"
        }
    },

    showlegend: false,
    hovermode: "x unified",
    dragmode: "zoom",
    uirevision: "context-" + SYMBOL + "-" + INTERVAL_LABEL,

    xaxis: {
        fixedrange: false,
        rangeslider: {
            visible: false
        },
        gridcolor: "#202938",
        zeroline: false,
        showspikes: true,
        spikecolor: "#8490a3",
        tickfont: {
            color: "#d1d4dc",
            size: 10
        }
    },

    yaxis: {
        fixedrange: false,
        gridcolor: "#202938",
        zeroline: false,
        side: "right",
        automargin: true,
        showticklabels: true,
        separatethousands: true,
        ticks: "outside",
        tickcolor: "#8490a3",
        showline: true,
        linecolor: "#3a4556",
        tickfont: {
            color: "#d1d4dc",
            size: 11
        }
    }
};


const plotConfig = {
    responsive: true,
    displaylogo: false,
    displayModeBar: true,
    scrollZoom: true,
    doubleClick: "reset+autosize",
    showAxisDragHandles: true,
    showAxisRangeEntryBoxes: true,
    modeBarButtonsToRemove: [
        "lasso2d",
        "select2d"
    ]
};



function setDragMode(chart, mode, prefix) {
    Plotly.relayout(chart, {dragmode: mode});

    const zoomButton = document.getElementById(
        prefix + "ZoomMode"
    );

    const panButton = document.getElementById(
        prefix + "PanMode"
    );

    if (zoomButton && panButton) {
        zoomButton.classList.toggle(
            "active",
            mode === "zoom"
        );

        panButton.classList.toggle(
            "active",
            mode === "pan"
        );
    }
}


function axisRangeAsNumbers(axis) {
    if (!axis || !axis.range || axis.range.length !== 2) {
        return null;
    }

    if (axis.type === "date") {
        const start = new Date(axis.range[0]).getTime();
        const end = new Date(axis.range[1]).getTime();

        if (!Number.isFinite(start) || !Number.isFinite(end)) {
            return null;
        }

        return {
            start: start,
            end: end,
            isDate: true
        };
    }

    const start = Number(axis.range[0]);
    const end = Number(axis.range[1]);

    if (!Number.isFinite(start) || !Number.isFinite(end)) {
        return null;
    }

    return {
        start: start,
        end: end,
        isDate: false
    };
}


function zoomAxis(chart, axisName, factor) {
    const axisKey = axisName + "axis";
    const axis = chart._fullLayout
        ? chart._fullLayout[axisKey]
        : null;

    const currentRange = axisRangeAsNumbers(axis);

    if (!currentRange) {
        return;
    }

    const center = (
        currentRange.start + currentRange.end
    ) / 2;

    const halfRange = (
        currentRange.end - currentRange.start
    ) * factor / 2;

    let newStart = center - halfRange;
    let newEnd = center + halfRange;

    if (currentRange.isDate) {
        newStart = new Date(newStart).toISOString();
        newEnd = new Date(newEnd).toISOString();
    }

    const update = {};
    update[axisKey + ".autorange"] = false;
    update[axisKey + ".range"] = [newStart, newEnd];

    Plotly.relayout(chart, update);
}


function resetChart(chart) {
    Plotly.relayout(
        chart,
        {
            "xaxis.autorange": true,
            "yaxis.autorange": true
        }
    );
}

Plotly.newPlot(
    liveChart,
    liveTraces,
    liveLayout,
    plotConfig
);

Plotly.newPlot(
    contextChart,
    [contextTrace],
    contextLayout,
    plotConfig
);


function calculateSessionVwap() {
    if (cumulativeVolume <= 0) {
        return null;
    }

    return cumulativePriceVolume / cumulativeVolume;
}


function calculateSessionSigma(vwap) {
    if (!isFiniteNumber(vwap) || cumulativeVolume <= 0) {
        return null;
    }

    const variance = Math.max(
        0,
        cumulativePriceSquaredVolume / cumulativeVolume
        - Number(vwap) * Number(vwap)
    );

    return Math.sqrt(variance);
}


function purgeRollingTicks(currentTimestampMs) {
    const cutoff = currentTimestampMs - ROLLING_WINDOW_MS;

    while (
        rollingTicks.length > 0
        && rollingTicks[0].timestampMs < cutoff
    ) {
        rollingTicks.shift();
    }
}


function calculateRollingVwap() {
    let volume = 0;
    let priceVolume = 0;

    for (const tick of rollingTicks) {
        if (tick.volume > 0) {
            volume += tick.volume;
            priceVolume += tick.price * tick.volume;
        }
    }

    return volume > 0
        ? priceVolume / volume
        : null;
}


function updateVolumeQuality() {
    if (totalTicks < 5) {
        vwapQualityBox.textContent = "Reconstruction en cours";
        return;
    }

    if (positiveVolumeTicks === 0 || cumulativeVolume <= 0) {
        vwapQualityBox.textContent = "Indisponible · aucun volume";
        vwapQualityBox.style.color = "#ef5350";
        return;
    }

    const coverage = positiveVolumeTicks / totalTicks;

    let qualityLabel;
    let qualityColor;

    if (coverage >= 0.8) {
        qualityLabel = "Volume complet";
        qualityColor = "#26a69a";
    } else if (coverage >= 0.25) {
        qualityLabel = "Volume partiel";
        qualityColor = "#f0b90b";
    } else {
        qualityLabel = "Volume rare";
        qualityColor = "#ef5350";
    }

    vwapQualityBox.textContent =
        qualityLabel
        + " · "
        + Math.round(coverage * 100)
        + "% des ticks";

    vwapQualityBox.style.color = qualityColor;
}


function updateSourceAlignment(currentPrice) {
    if (
        sourceAligned !== null
        || !isFiniteNumber(CONTEXT.yahoo_last)
        || !isFiniteNumber(currentPrice)
    ) {
        return;
    }

    referenceRatio =
        Number(currentPrice)
        / Number(CONTEXT.session_open);

    sourceAligned =
        Math.abs(referenceRatio - 1) <= 0.03;

    if (!sourceAligned) {
        statusRightBox.textContent =
            "Yahoo et LSE semblent utiliser des instruments différents";
        statusRightBox.style.color = "#f0b90b";
    }
}


function liveReferencePrice(yahooReference) {
    if (!isFiniteNumber(yahooReference)) {
        return null;
    }

    if (sourceAligned === false) {
        return null;
    }

    return Number(yahooReference);
}


function updatePerformance(currentPrice) {
    updateSourceAlignment(currentPrice);

    const previousClose = liveReferencePrice(
        CONTEXT.previous_close
    );

    const openReference =
        firstLsePrice !== null
            ? firstLsePrice
            : liveReferencePrice(CONTEXT.session_open);

    const dayPerformance =
        previousClose
            ? (currentPrice / previousClose - 1) * 100
            : null;

    const openPerformance =
        openReference
            ? (currentPrice / openReference - 1) * 100
            : null;

    setDirectionalValue(
        dayPerformanceBox,
        dayPerformance,
        formatSignedPercent(dayPerformance)
    );

    setDirectionalValue(
        openPerformanceBox,
        openPerformance,
        formatSignedPercent(openPerformance)
    );

    if (firstLsePrice !== null) {
        openReferenceBox.textContent =
            "Premier tick séance : "
            + formatPrice(firstLsePrice);
    }
}


function updateMicrostructure(tick, tickDate) {
    const bid = isFiniteNumber(tick.bid)
        ? Number(tick.bid)
        : null;

    const ask = isFiniteNumber(tick.ask)
        ? Number(tick.ask)
        : null;

    if (bid !== null && ask !== null && ask >= bid) {
        const spread = ask - bid;
        const midpoint = (ask + bid) / 2;
        const spreadBps = midpoint !== 0
            ? spread / midpoint * 10000
            : null;

        spreadValueBox.textContent = formatPrice(spread);
        spreadBpsBox.textContent =
            isFiniteNumber(spreadBps)
                ? spreadBps.toFixed(2) + " bps"
                : "—";
    } else {
        spreadValueBox.textContent = "—";
        spreadBpsBox.textContent = "Bid/ask indisponible";
    }

    if (!tick.replay) {
        const arrival = Date.now();
        liveArrivalTimes.push(arrival);

        const velocityCutoff = arrival - 60000;
        while (
            liveArrivalTimes.length > 0
            && liveArrivalTimes[0] < velocityCutoff
        ) {
            liveArrivalTimes.shift();
        }

        tickVelocityBox.textContent =
            liveArrivalTimes.length + " ticks/min";

        if (
            previousLivePrice !== null
            && Number(tick.price) > 0
            && previousLivePrice > 0
        ) {
            const logReturn = Math.log(
                Number(tick.price) / previousLivePrice
            );

            shortReturns.push({
                timestampMs: tickDate.getTime(),
                value: logReturn
            });
        }

        previousLivePrice = Number(tick.price);

        const returnCutoff = tickDate.getTime() - 60000;
        while (
            shortReturns.length > 0
            && shortReturns[0].timestampMs < returnCutoff
        ) {
            shortReturns.shift();
        }

        const realizedVariance = shortReturns.reduce(
            (sum, item) => sum + item.value * item.value,
            0
        );

        const realizedVolBps =
            Math.sqrt(realizedVariance) * 10000;

        realizedVolBox.textContent =
            "Vol 1 min : "
            + realizedVolBps.toFixed(2)
            + " bps";
    }
}


function buildLiveShapes(currentPrice, currentVwap, lineColor) {
    const shapes = [];
    const annotations = [];

    if (overlayVisible("Clôture veille") && sourceAligned !== false) {
        if (isFiniteNumber(CONTEXT.previous_close)) {
            shapes.push({
                type: "line",
                xref: "paper",
                x0: 0,
                x1: 1,
                yref: "y",
                y0: Number(CONTEXT.previous_close),
                y1: Number(CONTEXT.previous_close),
                line: {
                    color: "#64748b",
                    width: 1,
                    dash: "dash"
                }
            });

            annotations.push({
                xref: "paper",
                x: 0.01,
                yref: "y",
                y: Number(CONTEXT.previous_close),
                text: "Clôture veille",
                showarrow: false,
                xanchor: "left",
                yanchor: "bottom",
                font: {
                    color: "#94a3b8",
                    size: 10
                },
                bgcolor: "rgba(14,17,23,0.7)"
            });
        }
    }

    if (overlayVisible("Ouverture")) {
        const openingValue =
            firstLsePrice !== null
                ? firstLsePrice
                : (
                    sourceAligned !== false
                    && isFiniteNumber(CONTEXT.session_open)
                        ? Number(CONTEXT.session_open)
                        : null
                );

        if (openingValue !== null) {
            shapes.push({
                type: "line",
                xref: "paper",
                x0: 0,
                x1: 1,
                yref: "y",
                y0: openingValue,
                y1: openingValue,
                line: {
                    color: "#38bdf8",
                    width: 1,
                    dash: "dash"
                }
            });

            annotations.push({
                xref: "paper",
                x: 0.01,
                yref: "y",
                y: openingValue,
                text: "Ouverture",
                showarrow: false,
                xanchor: "left",
                yanchor: "bottom",
                font: {
                    color: "#38bdf8",
                    size: 10
                },
                bgcolor: "rgba(14,17,23,0.7)"
            });
        }
    }

    shapes.push({
        type: "line",
        xref: "paper",
        x0: 0,
        x1: 1,
        yref: "y",
        y0: currentPrice,
        y1: currentPrice,
        line: {
            color: lineColor,
            width: 1,
            dash: "dot"
        }
    });

    annotations.push({
        xref: "paper",
        x: 1.008,
        xanchor: "left",
        yref: "y",
        y: currentPrice,
        yanchor: "middle",
        text: formatPrice(currentPrice),
        showarrow: false,
        bgcolor: lineColor,
        bordercolor: lineColor,
        borderpad: 4,
        font: {
            color: "#ffffff",
            size: 11
        }
    });

    if (
        overlayVisible("VWAP séance")
        && isFiniteNumber(currentVwap)
    ) {
        annotations.push({
            xref: "paper",
            x: 0.01,
            xanchor: "left",
            yref: "y",
            y: Number(currentVwap),
            yanchor: "bottom",
            text: "VWAP",
            showarrow: false,
            bgcolor: "rgba(14,17,23,0.75)",
            font: {
                color: "#f59e0b",
                size: 10
            }
        });
    }

    return {
        shapes: shapes,
        annotations: annotations
    };
}


function updateContextReferences(currentPrice) {
    const shapes = [];
    const annotations = [];

    if (overlayVisible("Clôture veille") && isFiniteNumber(CONTEXT.previous_close)) {
        shapes.push({
            type: "line",
            xref: "paper",
            x0: 0,
            x1: 1,
            yref: "y",
            y0: Number(CONTEXT.previous_close),
            y1: Number(CONTEXT.previous_close),
            line: {
                color: "#64748b",
                width: 1,
                dash: "dash"
            }
        });
    }

    if (overlayVisible("Ouverture") && isFiniteNumber(CONTEXT.session_open)) {
        shapes.push({
            type: "line",
            xref: "paper",
            x0: 0,
            x1: 1,
            yref: "y",
            y0: Number(CONTEXT.session_open),
            y1: Number(CONTEXT.session_open),
            line: {
                color: "#38bdf8",
                width: 1,
                dash: "dash"
            }
        });
    }

    if (sourceAligned !== false && isFiniteNumber(currentPrice)) {
        const dayPerformance =
            isFiniteNumber(CONTEXT.previous_close)
                ? (
                    currentPrice / Number(CONTEXT.previous_close) - 1
                ) * 100
                : null;

        const openPerformance =
            isFiniteNumber(CONTEXT.session_open)
                ? (
                    currentPrice / Number(CONTEXT.session_open) - 1
                ) * 100
                : null;

        shapes.push({
            type: "line",
            xref: "paper",
            x0: 0,
            x1: 1,
            yref: "y",
            y0: currentPrice,
            y1: currentPrice,
            line: {
                color: "#f4f7fb",
                width: 1,
                dash: "dot"
            }
        });

        annotations.push({
            xref: "paper",
            x: 1.005,
            xanchor: "left",
            yref: "y",
            y: currentPrice,
            text: formatPrice(currentPrice),
            showarrow: false,
            bgcolor: "#f4f7fb",
            bordercolor: "#f4f7fb",
            borderpad: 3,
            font: {
                color: "#0e1117",
                size: 10
            }
        });

        annotations.push({
            xref: "paper",
            x: 0.01,
            xanchor: "left",
            yref: "paper",
            y: 0.99,
            yanchor: "top",
            text:
                "Jour "
                + formatSignedPercent(dayPerformance)
                + " · Open "
                + formatSignedPercent(openPerformance),
            showarrow: false,
            bgcolor: "rgba(14,17,23,0.78)",
            bordercolor: "#273142",
            borderwidth: 1,
            borderpad: 5,
            font: {
                color: "#f4f7fb",
                size: 11
            }
        });
    }

    Plotly.relayout(
        contextChart,
        {
            shapes: shapes,
            annotations: annotations
        }
    );
}


function flushTicks() {
    if (pending.x.length === 0) {
        return;
    }

    const batch = pending;

    pending = {
        x: [],
        price: [],
        mid: [],
        sessionVwap: [],
        rollingVwap: [],
        upperBand: [],
        lowerBand: []
    };

    Plotly.extendTraces(
        liveChart,
        {
            x: [
                batch.x,
                batch.x,
                batch.x,
                batch.x,
                batch.x,
                batch.x
            ],
            y: [
                batch.price,
                batch.mid,
                batch.sessionVwap,
                batch.rollingVwap,
                batch.upperBand,
                batch.lowerBand
            ]
        },
        [0, 1, 2, 3, 4, 5],
        MAX_PLOT_POINTS
    );

    if (latestTick === null || latestPrice === null) {
        return;
    }

    const currentVwap = calculateSessionVwap();
    const lineColor =
        firstLsePrice !== null
        && latestPrice >= firstLsePrice
            ? "#26a69a"
            : "#ef5350";

    lastPriceBox.textContent = formatPrice(latestPrice);
    lastPriceBox.style.color = lineColor;

    updatePerformance(latestPrice);
    updateVolumeQuality();

    if (isFiniteNumber(currentVwap)) {
        sessionVwapBox.textContent = formatPrice(currentVwap);

        const distanceBps =
            currentVwap !== 0
                ? (latestPrice / currentVwap - 1) * 10000
                : null;

        sessionVwapBox.style.color =
            latestPrice >= currentVwap
                ? "#26a69a"
                : "#ef5350";

        if (isFiniteNumber(distanceBps)) {
            vwapQualityBox.title =
                "Écart prix-VWAP : "
                + distanceBps.toFixed(2)
                + " bps";
        }
    } else {
        sessionVwapBox.textContent = "—";
    }

    const markers = buildLiveShapes(
        latestPrice,
        currentVwap,
        lineColor
    );

    Plotly.relayout(
        liveChart,
        {
            shapes: markers.shapes,
            annotations: markers.annotations
        }
    );

    updateContextReferences(latestPrice);
}


setInterval(flushTicks, FLUSH_INTERVAL_MS);


function processTick(message) {
    const rawTimestamp = message.ts ?? message.timestamp;

    if (message.replay) {
        const replayKey = [
            rawTimestamp,
            message.price,
            message.volume,
            message.bid,
            message.ask
        ].join("|");

        if (seenReplayTicks.has(replayKey)) {
            return;
        }

        seenReplayTicks.add(replayKey);
    }

    const tickDate = parseTimestamp(rawTimestamp);

    if (Number.isNaN(tickDate.getTime())) {
        return;
    }

    const price = Number(message.price);

    if (!Number.isFinite(price)) {
        return;
    }

    totalTicks += 1;
    latestTick = message;
    latestPrice = price;

    if (firstLsePrice === null) {
        firstLsePrice = price;
    }

    const bid = isFiniteNumber(message.bid)
        ? Number(message.bid)
        : null;

    const ask = isFiniteNumber(message.ask)
        ? Number(message.ask)
        : null;

    const mid =
        bid !== null
        && ask !== null
        && ask >= bid
            ? (bid + ask) / 2
            : null;

    const volume =
        isFiniteNumber(message.volume)
        && Number(message.volume) > 0
            ? Number(message.volume)
            : 0;

    if (volume > 0) {
        positiveVolumeTicks += 1;
        cumulativeVolume += volume;
        cumulativePriceVolume += price * volume;
        cumulativePriceSquaredVolume += price * price * volume;
    }

    rollingTicks.push({
        timestampMs: tickDate.getTime(),
        price: price,
        volume: volume
    });

    purgeRollingTicks(tickDate.getTime());

    const sessionVwap = calculateSessionVwap();
    const sigma = calculateSessionSigma(sessionVwap);
    const rollingVwap = calculateRollingVwap();

    pending.x.push(tickDate);
    pending.price.push(price);
    pending.mid.push(mid);
    pending.sessionVwap.push(sessionVwap);
    pending.rollingVwap.push(rollingVwap);
    pending.upperBand.push(
        sessionVwap !== null && sigma !== null
            ? sessionVwap + sigma
            : null
    );
    pending.lowerBand.push(
        sessionVwap !== null && sigma !== null
            ? sessionVwap - sigma
            : null
    );

    updateMicrostructure(message, tickDate);

    const mode = message.replay ? "Replay" : "Live";

    statusLeftBox.textContent =
        mode
        + " · dernier tick "
        + tickDate.toLocaleTimeString(
            [],
            {
                hour12: false
            }
        );

    statusLeftBox.style.color =
        message.replay
            ? "#f0b90b"
            : "#26a69a";
}


function connect() {
    clearTimeout(reconnectTimer);

    statusLeftBox.textContent = "Connexion au flux…";
    statusLeftBox.style.color = "#f0b90b";

    socket = new WebSocket(
        "wss://data-ws.londonstrategicedge.com"
    );

    socket.onmessage = function(event) {
        const message = JSON.parse(event.data);

        if (message.type === "welcome") {
            socket.send(
                JSON.stringify({
                    action: "auth",
                    api_key: API_KEY
                })
            );
            return;
        }

        if (message.type === "authenticated") {
            socket.send(
                JSON.stringify({
                    action: "subscribe",
                    symbol: SYMBOL,
                    start: CONTEXT.replay_start_iso
                })
            );

            statusLeftBox.textContent =
                CONTEXT.replay_is_partial
                    ? "Replay limité aux dernières 24 heures…"
                    : "Reconstruction de la séance…";

            if (CONTEXT.replay_is_partial) {
                statusRightBox.textContent =
                    "VWAP séance complète indisponible : limite de replay 24 h";
                statusRightBox.style.color = "#f0b90b";
            }

            return;
        }

        if (message.type === "subscribed") {
            statusLeftBox.textContent = "Abonné au flux · attente des ticks…";
            return;
        }

        if (message.type === "replay_started") {
            statusLeftBox.textContent = "Reconstruction de la séance…";
            statusLeftBox.style.color = "#f0b90b";
            return;
        }

        if (message.type === "replay_complete") {
            replayComplete = true;
            statusLeftBox.textContent = "Replay terminé · flux live";
            statusLeftBox.style.color = "#26a69a";
            updateVolumeQuality();
            return;
        }

        if (
            message.type === "tick"
            && message.symbol === SYMBOL
        ) {
            processTick(message);
            return;
        }

        if (message.type === "error") {
            statusLeftBox.textContent =
                "Erreur : "
                + (
                    message.message
                    || message.code
                    || "erreur inconnue"
                );
            statusLeftBox.style.color = "#ef5350";
        }
    };

    socket.onerror = function() {
        statusLeftBox.textContent = "Erreur de connexion";
        statusLeftBox.style.color = "#ef5350";
    };

    socket.onclose = function() {
        statusLeftBox.textContent = "Connexion perdue · reconnexion…";
        statusLeftBox.style.color = "#f0b90b";

        reconnectTimer = setTimeout(connect, 2500);
    };
}


connect();


window.addEventListener(
    "beforeunload",
    function() {
        if (socket) {
            socket.close();
        }
    }
);


window.addEventListener(
    "resize",
    function() {
        Plotly.Plots.resize(liveChart);
        Plotly.Plots.resize(contextChart);
    }
);
</script>

</body>
</html>
"""

    grid_columns = "1fr" if focus else "2.15fr 1fr"

    html = (
        html_template
        .replace("__SETTINGS__", json.dumps(payload))
        .replace("__GRID_COLUMNS__", grid_columns)
    )

    component_height = 1010 if focus else 790

    components.html(
        html,
        height=component_height,
        scrolling=False,
    )


# =============================================================================
# PAGE
# =============================================================================

st.markdown(
    '<div class="flavio-title">Flavio Monitor</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="flavio-subtitle">'
    'Live markets · Context · VWAP · Microstructure · Zoom X/Y'
    '</div>',
    unsafe_allow_html=True,
)

if UNRESOLVED_MARKETS:
    st.warning(
        "Marchés non trouvés dans le catalogue LSE : "
        + ", ".join(UNRESOLVED_MARKETS)
    )

render_terminal(
    api_key_value=api_key,
    symbol=selected_lse_symbol,
    market_name=selected_market,
    interval_label=selected_interval_label,
    context=yahoo_context,
    overlays=selected_overlays,
    rolling_minutes=rolling_vwap_minutes,
    focus=focus_mode,
)
