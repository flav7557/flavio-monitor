"""
FLAVIO MONITOR ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ALL-IN-ONE AVEC KALMAN SUR TICKS LSE

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
        'Trading workspace ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Morning desk ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Quant lab ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Shadow trader'
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
            "Shadow Trader",
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
    "1 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â Plein ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©cran": {
        "count": 1,
        "columns": "1fr",
        "rows": "1fr",
        "areas": ["p0"],
        "css_areas": '"p0"',
        "height": 820,
    },
    "2 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â CÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â´te ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  cÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â´te": {
        "count": 2,
        "columns": "1fr 1fr",
        "rows": "1fr",
        "areas": ["p0", "p1"],
        "css_areas": '"p0 p1"',
        "height": 820,
    },
    "2 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â EmpilÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s": {
        "count": 2,
        "columns": "1fr",
        "rows": "1fr 1fr",
        "areas": ["p0", "p1"],
        "css_areas": '"p0" "p1"',
        "height": 1060,
    },
    "3 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â Principal + 2": {
        "count": 3,
        "columns": "2fr 1fr",
        "rows": "1fr 1fr",
        "areas": ["p0", "p1", "p2"],
        "css_areas": '"p0 p1" "p0 p2"',
        "height": 920,
    },
    "4 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â Grille 2 ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2": {
        "count": 4,
        "columns": "1fr 1fr",
        "rows": "1fr 1fr",
        "areas": ["p0", "p1", "p2", "p3"],
        "css_areas": '"p0 p1" "p2 p3"',
        "height": 940,
    },
    "5 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â Principal + 4": {
        "count": 5,
        "columns": "2fr 1fr 1fr",
        "rows": "1fr 1fr",
        "areas": ["p0", "p1", "p2", "p3", "p4"],
        "css_areas": '"p0 p1 p2" "p0 p3 p4"',
        "height": 940,
    },
    "6 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â Grille 3 ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2": {
        "count": 6,
        "columns": "1fr 1fr 1fr",
        "rows": "1fr 1fr",
        "areas": ["p0", "p1", "p2", "p3", "p4", "p5"],
        "css_areas": '"p0 p1 p2" "p3 p4 p5"',
        "height": 940,
    },
}

SETUPS = {
    "Contexte": ["Ouverture", "ClÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â´ture veille"],
    "VWAP": ["Ouverture", "ClÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â´ture veille", "VWAP sÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©ance", "Bandes VWAP"],
    "Microstructure": ["Mid-price", "VWAP sÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©ance"],
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
        st.caption("ClÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© LSE chargÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e depuis les secrets du serveur.")
    else:
        api_key = st.text_input(
            "ClÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© API LSE",
            value="",
            type="password",
            placeholder="lse_live_...",
        )

if not api_key:
    st.markdown(
        '<div class="workspace-title">Flavio Monitor</div>',
        unsafe_allow_html=True,
    )
    st.info("Entre ta clÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© API LSE dans la barre latÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©rale.")
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
    st.error("Aucun marchÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© demandÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© nÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢a ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©tÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© trouvÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© dans le catalogue LSE.")
    st.stop()


# =============================================================================
# DONNÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â°ES YAHOO
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
        raise ValueError(f"Aucune donnÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e intraday pour {yahoo_symbol}.")

    intraday = intraday.rename(columns=str.title)
    intraday = intraday.dropna(subset=["Open", "High", "Low", "Close"])

    if intraday.empty:
        raise ValueError(f"Les bougies reÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§ues pour {yahoo_symbol} sont vides.")

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
        "Chaque fenÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªtre choisit sa source et son timeframe. "
        "LSE : ticks ou bougies live. Yahoo : bougies intraday. "
        "DÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©placer reste le mode par dÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©faut."
    )

    panel_settings: list[dict[str, Any]] = []

    for panel_index in range(panel_count):
        default_market = DEFAULT_MARKETS[panel_index % len(DEFAULT_MARKETS)]
        if default_market not in AVAILABLE_MARKETS:
            default_market = AVAILABLE_MARKETS[0]

        with st.expander(
            f"FenÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªtre {panel_index + 1}",
            expanded=panel_index < min(panel_count, 2),
        ):
            market = st.selectbox(
                "MarchÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©",
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
        'Clique sur <b>Mode ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©cran</b> pour masquer toute lÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢interface et ne garder que les graphiques. '
        'DÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©place ensuite la fenÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªtre sur ton deuxiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¨me ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©cran. ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â°chap permet de quitter.'
        '</div>',
        unsafe_allow_html=True,
    )


# Charge une seule fois chaque combinaison marchÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© / timeframe.
context_cache: dict[tuple[str, str], dict[str, Any]] = {}
loading_errors: list[str] = []

with st.spinner("Chargement du workspaceÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦"):
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
                f"{market} ({panel['source']} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· {panel['timeframe_label']}) : {error}"
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
                "session_date": "ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â",
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
            <div id="connectionStatus">ConnexionÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦</div>
            <button class="topButton" onclick="enterScreenMode()">Mode ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©cran</button>
        </div>
    </div>

    <div id="grid"></div>

    <div id="exitHotZone">
        <button id="exitScreenButton" onclick="exitScreenMode()" title="Quitter le mode ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©cran (ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â°chap)">ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â</button>
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

workspaceMeta.textContent = SETTINGS.layoutLabel + " ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· " + PANELS.length + " fenÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªtre(s)";

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
        return "ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â";
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
        return "ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â";
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
                    <span class="panelPrice" id="price-${panel.id}">ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</span>
                </div>
                <div class="panelSubtitle">${panel.source === "LSE" ? panel.symbol : panel.yahoo_symbol} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${panel.source} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${panel.timeframe_label} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${panel.setup}</div>
            </div>

            <div class="panelControls">
                <button class="chartButton active" id="pan-${panel.id}" onclick="setDragMode('${panel.id}', 'pan')">DÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©placer</button>
                <button class="chartButton" id="zoom-${panel.id}" onclick="setDragMode('${panel.id}', 'zoom')">Zone</button>
                <button class="chartButton axisButton" onclick="zoomAxis('${panel.id}', 'x', 0.66)">Temps +</button>
                <button class="chartButton axisButton" onclick="zoomAxis('${panel.id}', 'x', 1.52)">Temps ÃƒÆ’Ã‚Â¢Ãƒâ€¹Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢</button>
                <button class="chartButton axisButton" onclick="zoomAxis('${panel.id}', 'y', 0.66)">Prix +</button>
                <button class="chartButton axisButton" onclick="zoomAxis('${panel.id}', 'y', 1.52)">Prix ÃƒÆ’Ã‚Â¢Ãƒâ€¹Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢</button>
                <button class="chartButton" onclick="resetChart('${panel.id}')">Reset</button>
                <button class="chartButton" onclick="togglePanelMaximize('${panel.id}')">Agrandir</button>
            </div>
        </div>

        <div class="panelMetrics">
            <span>Jour <span class="metricValue" id="day-${panel.id}">ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</span></span>
            <span>Open <span class="metricValue" id="open-${panel.id}">ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</span></span>
            <span>VWAP <span class="metricValue" id="vwap-${panel.id}">ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</span></span>
            <span>Spread <span class="metricValue" id="spread-${panel.id}">ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</span></span>
            <span id="status-${panel.id}">En attenteÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦</span>
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
    const showVwap = panel.overlays.includes("VWAP sÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©ance");
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
            name: "VWAP +1ÃƒÆ’Ã‚ÂÃƒâ€ Ã¢â‚¬â„¢",
            visible: showBands ? true : "legendonly",
            line: {color: "#f59e0b", width: 0.8, dash: "dash"},
            hoverinfo: "skip"
        },
        {
            x: [],
            y: [],
            type: "scattergl",
            mode: "lines",
            name: "VWAP -1ÃƒÆ’Ã‚ÂÃƒâ€ Ã¢â‚¬â„¢",
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
    const showVwap = panel.overlays.includes("VWAP sÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©ance");
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
            name: "VWAP +1ÃƒÆ’Ã‚ÂÃƒâ€ Ã¢â‚¬â„¢",
            visible: showBands ? true : "legendonly",
            line: {color: "#f59e0b", width: 0.8, dash: "dash"},
            hoverinfo: "skip"
        },
        {
            x: [],
            y: [],
            type: "scattergl",
            mode: "lines",
            name: "VWAP -1ÃƒÆ’Ã‚ÂÃƒâ€ Ã¢â‚¬â„¢",
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

    vwapElement.textContent = "ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â";
    spreadElement.textContent = "ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â";
    statusElement.textContent = "Yahoo ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· " + context.session_date;
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
                + " ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· "
                + panel.source
                + " ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· "
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
        connectionStatus.textContent = "Mode ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©cran actif dans la page ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· F11 pour masquer le navigateur";
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
        spreadElement.textContent = "ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â";
    }

    if (tick) {
        const tickDate = parseTimestamp(tick.ts ?? tick.timestamp);
        statusElement.textContent = (tick.replay ? "Replay" : "Live")
            + " ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· "
            + tickDate.toLocaleTimeString([], {hour12: false});
        statusElement.style.color = tick.replay ? "#f0b90b" : "#26a69a";
    }
}


function buildReferenceShapes(panel, state) {
    const shapes = [];
    const annotations = [];
    const context = panel.context;

    if (panel.overlays.includes("ClÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â´ture veille") && isFiniteNumber(context.previous_close)) {
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

    connectionStatus.textContent = "ConnexionÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦";
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

            connectionStatus.textContent = "Reconstruction des sÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©ancesÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦";
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
        connectionStatus.textContent = "ReconnexionÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦";
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
    '<div class="workspace-title">Flavio Monitor ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â Workspace V5.1</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="workspace-subtitle">'
    'Sources indÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©pendantes LSE / Yahoo ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Timeframes adaptÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Mode ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©cran immersif'
    '</div>',
    unsafe_allow_html=True,
)

if UNRESOLVED_MARKETS:
    st.warning(
        "MarchÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s non trouvÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s dans le catalogue LSE : "
        + ", ".join(UNRESOLVED_MARKETS)
    )

if loading_errors:
    with st.expander("Certaines donnÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©es Yahoo nÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ont pas pu ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªtre chargÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©es"):
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
    'Performance multi-horizons ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Market movers ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Calendrier macro'
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
        return "ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â"
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
        .format(lambda value: "ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â" if pd.isna(value) else f"{value:+.2f}%")
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
            "Yahoo nÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢a retournÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© aucune clÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â´ture pour le CAC 40 et le S&P 500."
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
        "Actualiser les donnÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©es",
        use_container_width=True,
    ):
        st.cache_data.clear()
        st.rerun()

    st.caption(
        "Les horizons sont calculÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s en sÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©ances de bourse : "
        "21j correspond approximativement ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  un mois."
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
                + "<br>%{x} sÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©ance(s)"
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
        title="Nombre de sÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©ances",
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
    "Voir toutes les performances de 1j ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  21j",
    expanded=False,
):
    st.dataframe(
        style_performance_table(
            performance_table
        ),
        use_container_width=True,
    )

st.caption(
    "Calcul : derniÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¨re clÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â´ture Yahoo disponible contre la clÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â´ture "
    "situÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e N sÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©ances plus tÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â´t. Pendant la sÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©ance, la bougie journaliÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¨re "
    "Yahoo peut encore ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©voluer."
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
            "Aucun tableau HTML n'a ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©tÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© dÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©tectÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© sur WikipÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©dia."
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
            f"Impossible dÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢identifier la table des composants {universe}."
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
            f"Yahoo nÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢a retournÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© aucun prix pour les composants {universe}."
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
    '<div class="section-label">Top performers de la journÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e</div>',
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
        "car Yahoo doit traiter environ 500 valeurs. Le rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©sultat est ensuite "
        "mis en cache pendant 15 minutes."
    )

try:
    with st.spinner(
        f"Chargement des composants {movers_universe}ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦"
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
    "Composants rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©cupÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s depuis WikipÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©dia, cours et performances "
    "calculÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s avec Yahoo Finance. Il sÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢agit de variations clÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â´ture ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  clÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â´ture "
    "sur la derniÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¨re sÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©ance disponible."
)


# =============================================================================
# ECONOMIC CALENDAR
# =============================================================================

st.divider()

st.markdown(
    '<div class="section-label">Calendrier ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©conomique</div>',
    unsafe_allow_html=True,
)

calendar_view = st.radio(
    "PÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©riode",
    options=["AujourdÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢hui", "Semaine"],
    horizontal=True,
)

calendar_type = (
    "day"
    if calendar_view == "AujourdÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢hui"
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
    # Principales ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©conomies et zones macro.
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
    "Investing.com ne fournit pas ici une API publique structurÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e : "
    "cette section utilise son widget officiel, actualisÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© automatiquement. "
    "Les filtres et le fuseau horaire peuvent ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªtre modifiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s directement "
    "dans le calendrier."
)

'''

KALMAN_LAB_SOURCE = r'''
from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

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
    '<div class="tick-kalman-title">Kalman Lab ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â Tick Engine</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="tick-kalman-subtitle">'
    'Replay LSE ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Kalman filtering ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· HMM regimes ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Dynamic beta ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Relative value'
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
    "Lissage & prÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©vision": (
        "Chaque tick met ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  jour directement le filtre local level + trend."
    ),
    "BÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªta dynamique": (
        "Les ticks des deux actifs sont synchronisÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s, puis le bÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªta est mis ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  jour rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©cursivement."
    ),
    "Relative value": (
        "Le Kalman estime un hedge ratio dynamique et le z-score du spread."
    ),
    "Kalman + HMM": (
        "Le Kalman nettoie les ticks ; un HMM estime les rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©gimes bruit, hausse, baisse et choc."
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
        st.caption("ClÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© LSE chargÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e depuis les secrets du serveur.")
    else:
        api_key = st.text_input(
            "ClÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© API LSE",
            value="",
            type="password",
            placeholder="lse_live_...",
            key="kalman_tick_api_key",
        )

if not api_key:
    st.info(
        "Entre ta clÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© API LSE dans la sidebar pour charger les ticks."
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
        "Aucun des marchÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s demandÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s n'a ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©tÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© trouvÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© dans le catalogue LSE."
    )
    st.stop()

with st.sidebar:
    mode = st.selectbox(
        "ModÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¨le",
        options=list(MODE_DESCRIPTIONS),
        key="kalman_tick_mode",
    )

    st.caption(MODE_DESCRIPTIONS[mode])

    replay_label = st.selectbox(
        "Historique rejouÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©",
        options=list(REPLAY_OPTIONS),
        index=4,
        key="kalman_tick_replay",
    )

    replay_minutes = REPLAY_OPTIONS[replay_label]

    max_points = st.slider(
        "Points conservÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s",
        min_value=500,
        max_value=8000,
        value=3000,
        step=500,
        key="kalman_tick_max_points",
    )

    if mode in {"Lissage & prÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©vision", "Kalman + HMM"}:
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
            "Horizon de prÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©vision (ticks)",
            min_value=10,
            max_value=200,
            value=50,
            step=10,
            key="kalman_tick_forecast",
        )

        reactivity = st.slider(
            "RÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©activitÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© du filtre",
            min_value=1,
            max_value=10,
            value=5,
            key="kalman_tick_reactivity",
        )

        observation_trust = st.slider(
            "Confiance dans le tick observÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©",
            min_value=1,
            max_value=10,
            value=6,
            key="kalman_tick_trust",
        )

        if mode == "Kalman + HMM":
            hmm_persistence = st.slider(
                "Persistance des rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©gimes HMM",
                min_value=70,
                max_value=99,
                value=92,
                step=1,
                help=(
                    "Plus la valeur est ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©levÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e, plus le HMM demande des preuves "
                    "avant de changer de rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©gime."
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
                    "ProbabilitÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© minimale avant d'afficher LONG, SHORT "
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
                "Choisis deux actifs diffÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©rents."
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
            "FenÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªtre du z-score",
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
        with st.expander("MarchÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s non trouvÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s"):
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
            <div id="terminalStatus">InitialisationÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦</div>
        </div>

        <div id="toolbarButtons">
            <button id="panButton">DÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©placer</button>
            <button id="zoomButton">Zone</button>
            <button id="resetButton">Reset</button>
            <button id="fullscreenButton">Plein ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©cran</button>
        </div>
    </div>

    <div id="metrics">
        <div class="metric">
            <div class="metricLabel" id="metricLabel1">Dernier Y</div>
            <div class="metricValue" id="metricValue1">ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</div>
            <div class="metricSub" id="metricSub1">ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</div>
        </div>

        <div class="metric">
            <div class="metricLabel" id="metricLabel2">FiltrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© / BÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªta</div>
            <div class="metricValue" id="metricValue2">ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</div>
            <div class="metricSub" id="metricSub2">ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</div>
        </div>

        <div class="metric">
            <div class="metricLabel" id="metricLabel3">Tendance / Alpha</div>
            <div class="metricValue" id="metricValue3">ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</div>
            <div class="metricSub" id="metricSub3">ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</div>
        </div>

        <div class="metric">
            <div class="metricLabel" id="metricLabel4">PrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©vision / RÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©siduel</div>
            <div class="metricValue" id="metricValue4">ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</div>
            <div class="metricSub" id="metricSub4">ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</div>
        </div>

        <div class="metric">
            <div class="metricLabel" id="metricLabel5">ActivitÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© / Z-score</div>
            <div class="metricValue" id="metricValue5">ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</div>
            <div class="metricSub" id="metricSub5">ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</div>
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

const IS_SMOOTH = MODE === "Lissage & prÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©vision";
const IS_HYBRID = MODE === "Kalman + HMM";
const IS_SINGLE = IS_SMOOTH || IS_HYBRID;
const IS_BETA = MODE === "BÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªta dynamique";
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
        label: "Tendance haussiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¨re",
        color: COLORS.up,
        fill: "rgba(38,166,154,0.10)"
    },
    {
        key: "down",
        label: "Tendance baissiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¨re",
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
    if (!Number.isFinite(Number(value))) return "ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â";
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
    if (!Number.isFinite(Number(value))) return "ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â";
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

function setMetric(index, label, value, sub="ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â", color=COLORS.text) {
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

        // Etat 2: pente nÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©gative persistante.
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
            name: "Incertitude filtrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e 95%",
            hoverinfo: "skip"
        },
        {
            x: single.timestamps,
            y: single.observed,
            type: "scattergl",
            mode: "markers",
            name: "Ticks observÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s",
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
            hovertemplate: "%{x|%H:%M:%S.%L}<br>FiltrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© : %{y:,.5f}<extra></extra>"
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
            name: "CÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â´ne de prÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©vision 95%",
            hoverinfo: "skip"
        },
        {
            x: forecast.x,
            y: forecast.level,
            type: "scattergl",
            mode: "lines",
            name: "PrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©vision ticks",
            line: {color: COLORS.forecast, width: 2, dash: "dash"},
            hovertemplate: "%{x|%H:%M:%S.%L}<br>PrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©vision : %{y:,.5f}<extra></extra>"
        }
    ];

    const layout = commonLayout(
        `${ASSET_Y} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${SYMBOL_Y} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· tick-by-tick Kalman`,
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
            "Prix filtrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©",
            formatPrice(filtered),
            `${formatSigned((filtered / last - 1) * 100)}% vs tick`,
            filtered >= last ? COLORS.green : COLORS.red
        );
        setMetric(2, "Tendance / tick", formatSigned(trend, 5), "local linear trend");
        setMetric(
            3,
            `PrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©vision ${FORECAST_TICKS} ticks`,
            formatPrice(forecastLast),
            `${formatSigned(forecastChange)}% ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ~${Math.max(1, Math.round(estimatedMs / 1000))} sec`,
            forecastChange >= 0 ? COLORS.green : COLORS.red
        );
        setMetric(4, "ActivitÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© live", `${liveTickArrivals.length} ticks/min`, `${single.observed.length} points conservÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s`);
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
            name: "Ticks observÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s",
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
                + "<br>FiltrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© : %{y:,.5f}"
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
                    "PrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©vision 95%",
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
            `${ASSET_Y} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Prix latent et rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©gimes HMM`,
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
            "ProbabilitÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s des rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©gimes HMM",
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
            name: "Pente normalisÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e",
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
            name: "Innovation normalisÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e",
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
            "RÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©gime HMM",
            state.label,
            `${(
                confidence * 100
            ).toFixed(1)}% de probabilitÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©`,
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
            "unitÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s d'ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©cart-type"
        );

        setMetric(
            4,
            "Signal thÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©orique",
            action,
            `${duration} ticks dans le rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©gime`,
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
                "Premier couple synchronisÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© reÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§u"
                + " ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· initialisation des rendements";

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
            + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Y ${pair.received[SYMBOL_Y] || 0} ticks`
            + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· X ${pair.received[SYMBOL_X] || 0} ticks`;

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
            + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Y ${ticksY.length} ticks`
            + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· X ${ticksX.length} ticks`;

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
            + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${observations.length}/${requiredObservations} observations`
            + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Y ${ticksY.length} ticks`
            + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· X ${ticksX.length} ticks`;

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
            `Moteur initialisÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©`
            + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${observations.length} observations synchronisÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©es`
            + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${pair.beta.length} estimations Kalman`;
    } else {
        statusBox.textContent =
            `Initialisation partielle`
            + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${observations.length} observations`
            + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· attente de nouveaux ticks live`;
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
            `RÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©ception des ticks`
            + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Y ${countY}`
            + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· X ${countX}`;

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
            `${ASSET_Y} / ${ASSET_X} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ticks synchronisÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· base 100`,
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
            name: IS_BETA ? "BÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªta Kalman" : "Hedge ratio Kalman",
            line: {color: COLORS.filter, width: 2.2}
        }
    ];

    const betaLayout = commonLayout(
        IS_BETA ? "BÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªta dynamique" : "Hedge ratio dynamique",
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
        IS_BETA ? "Z-score du rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©siduel" : "Z-score du spread relative value",
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
                    ? "Le z-score nÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©cessite encore plusieurs rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©siduels"
                    : "Le z-score apparaÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â®tra aprÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¨s le warm-up du Kalman",
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

        setMetric(0, "Dernier Y", latestY ? formatPrice(latestY.price) : "ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â", SYMBOL_Y);
        setMetric(
            1,
            IS_BETA ? "BÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªta dynamique" : "Hedge ratio",
            beta.toFixed(4),
            `${pair.timestamps.length} estimations ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${pair.rawTimestamps.length} couples`
        );
        setMetric(2, "Dernier X", latestX ? formatPrice(latestX.price) : "ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â", SYMBOL_X);
        setMetric(3, IS_BETA ? "RÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©siduel" : "Spread", formatSigned(residual, 3), IS_BETA ? "bps" : "% log");
        setMetric(4, "Z-score", Number.isFinite(z) ? formatSigned(z, 2) : "ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â", `${liveTickArrivals.length} ticks/min`, zColor);
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
                + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${timestamp.toLocaleTimeString([], {hour12:false})}`
                + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${single.observed.length} ticks`
                + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${HMM_STATES[currentState].label}`
                + ` ${(
                    currentConfidence * 100
                ).toFixed(0)}%`;
        } else {
            statusBox.textContent =
                `${message.replay ? "Replay" : "Live"}`
                + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${timestamp.toLocaleTimeString([], {hour12:false})}`
                + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${single.observed.length} ticks`;
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
            + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Y ${pair.received[SYMBOL_Y] || 0} ticks`
            + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· X ${pair.received[SYMBOL_X] || 0} ticks`;

        return;
    }

    if (SYNC_MS === 0) {
        processLatestPair(
            timestamp
        );
    }

    statusBox.textContent =
        `${message.replay ? "Replay" : "Live"}`
        + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${timestamp.toLocaleTimeString([], {hour12:false})}`
        + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Y ${pair.received[SYMBOL_Y] || 0}`
        + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· X ${pair.received[SYMBOL_X] || 0}`
        + ` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· sync ${SYNC_MS === 0 ? "tick" : (SYNC_MS / 1000) + "s"}`;
}


function connect() {
    clearTimeout(reconnectTimer);
    statusBox.textContent = "Connexion au WebSocket LSEÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦";

    socket = new WebSocket("wss://data-ws.londonstrategicedge.com");

    socket.onmessage = event => {
        const message = JSON.parse(event.data);

        if (message.type === "welcome") {
            socket.send(JSON.stringify({action: "auth", api_key: API_KEY}));
            return;
        }

        if (message.type === "authenticated") {
            connectedAt = new Date();
            const start = (Date.now() - REPLAY_MINUTES * 60000) / 1000;
            const symbols = IS_SINGLE ? [SYMBOL_Y] : [SYMBOL_Y, SYMBOL_X];

            for (const symbol of symbols) {
                socket.send(JSON.stringify({action: "subscribe", symbol, start}));
            }

            statusBox.textContent = `AuthentifiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· replay ${REPLAY_MINUTES} minÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦`;
            return;
        }

        if (message.type === "replay_started") {
            statusBox.textContent = "Replay ticks en coursÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦";
            return;
        }

        if (message.type === "replay_complete") {
            if (IS_SINGLE) {
                statusBox.textContent = "Replay terminÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· passage en live";
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
        statusBox.textContent = "Connexion perdue ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· reconnexionÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦";
        reconnectTimer = setTimeout(connect, 2500);
    };
}

if (IS_SMOOTH) {
    singleCharts.style.display =
        "grid";

    pairCharts.style.display =
        "none";

    titleBox.textContent =
        `${MODE} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${ASSET_Y} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${SYMBOL_Y}`;

    Plotly.newPlot(
        "singleChart",
        [],
        commonLayout(
            "En attente des ticksÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦",
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
        `${MODE} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${ASSET_Y} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${SYMBOL_Y}`;

    Plotly.newPlot(
        "pairPriceChart",
        [],
        commonLayout(
            "En attente des ticks KalmanÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦",
            "empty-hybrid-price"
        ),
        plotConfig
    );

    Plotly.newPlot(
        "pairBetaChart",
        [],
        commonLayout(
            "Warm-up des probabilitÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s HMMÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦",
            "empty-hybrid-probabilities"
        ),
        plotConfig
    );

    Plotly.newPlot(
        "pairResidualChart",
        [],
        commonLayout(
            "Warm-up des variables de rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©gimeÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦",
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
        `${MODE} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${ASSET_Y} / ${ASSET_X}`;

    Plotly.newPlot(
        "pairPriceChart",
        [],
        commonLayout(
            "En attente des ticks synchronisÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©sÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦",
            "empty-pair-price"
        ),
        plotConfig
    );

    Plotly.newPlot(
        "pairBetaChart",
        [],
        commonLayout(
            "Warm-up du KalmanÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦",
            "empty-pair-beta"
        ),
        plotConfig
    );

    Plotly.newPlot(
        "pairResidualChart",
        [],
        commonLayout(
            "Warm-up du z-scoreÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦",
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
    "BÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªta et relative value : les ticks bruts sont synchronisÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s avant calcul, "
    "car deux actifs ne publient pas exactement au mÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªme instant. "
    "Le mode ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¹Ã…â€œChaque tickÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ utilise le dernier prix connu de lÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢autre actif."
)
'''


PAPER_TRADING_SOURCE = r'''
from __future__ import annotations

import json
import os
import re
import unicodedata
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from lse import LSE


st.markdown(
    """
    <style>
        .shadow-title {
            color: #f4f7fb;
            font-size: 2rem;
            font-weight: 760;
            letter-spacing: -0.045em;
            margin: 0;
        }
        .shadow-subtitle {
            color: #7f8b9c;
            font-size: 0.9rem;
            margin: 0.12rem 0 0.8rem 0;
        }
        .shadow-warning {
            border: 1px solid #58461d;
            background: rgba(217, 180, 74, 0.08);
            color: #d7c694;
            border-radius: 9px;
            padding: 9px 12px;
            margin-bottom: 0.8rem;
            font-size: 0.84rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="shadow-title">Shadow Trader</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="shadow-subtitle">'
    'Paper execution ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Microstructure costs ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Live P&L ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Trade blotter'
    '</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="shadow-warning">'
    '<strong>Simulation uniquement.</strong> Aucun ordre rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©el nÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢est envoyÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©. '
    'Le P&L dÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©pend des ticks LSE et des paramÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¨tres de contrat configurÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s.'
    '</div>',
    unsafe_allow_html=True,
)


MARKETS = {
    "CAC 40": {
        "candidates": ["CAC40", "CAC40/EUR", "FR40", "FR40/EUR", "FRA40", "PX1"],
        "search": ["cac 40", "france 40"],
        "tick_size": 0.1,
        "point_value": 1.0,
    },
    "DAX": {
        "candidates": ["DAX", "DAX40", "DAX40/EUR", "DE40", "DE40/EUR", "GER40"],
        "search": ["dax 40", "germany 40", "dax"],
        "tick_size": 0.1,
        "point_value": 1.0,
    },
    "Euro Stoxx 50": {
        "candidates": ["SX5E", "EU50", "EU50/EUR", "STOXX50", "ESTX50"],
        "search": ["euro stoxx 50", "stoxx 50"],
        "tick_size": 0.1,
        "point_value": 1.0,
    },
    "Nasdaq 100": {
        "candidates": ["NAS100", "NAS100/USD", "NDX", "NASDAQ100", "US100"],
        "search": ["nasdaq 100", "nasdaq-100"],
        "tick_size": 0.1,
        "point_value": 1.0,
    },
    "S&P 500": {
        "candidates": ["SPX500", "SPX500/USD", "SPX", "US500", "SP500"],
        "search": ["s&p 500", "sp 500", "standard and poor 500"],
        "tick_size": 0.1,
        "point_value": 1.0,
    },
    "Gold": {
        "candidates": ["XAU/USD", "GOLD/USD", "GOLD", "GC"],
        "search": ["spot gold", "gold"],
        "tick_size": 0.01,
        "point_value": 1.0,
    },
    "Brent": {
        "candidates": ["BRENT/USD", "BRENT", "BCO/USD", "UKOIL/USD", "BRN", "BZ"],
        "search": ["brent crude oil", "brent crude", "brent"],
        "tick_size": 0.01,
        "point_value": 1.0,
    },
    "EUR/USD": {
        "candidates": ["EUR/USD", "EURUSD"],
        "search": ["eur usd", "euro us dollar"],
        "tick_size": 0.00001,
        "point_value": 1.0,
    },
    "Bitcoin": {
        "candidates": ["BTC/USD", "BTCUSD"],
        "search": ["bitcoin", "btc usd"],
        "tick_size": 0.1,
        "point_value": 1.0,
    },
}

STRATEGY_DEFAULTS = {
    "replay_minutes": 60,
    "reactivity": 5,
    "observation_trust": 6,
    "confirmation": 3,
    "norm_window": 750,
    "entry_threshold": 1.25,
    "exit_threshold": 0.35,
    "shock_threshold": 2.75,
    "secondary_threshold": 0.50,
    "hmm_persistence": 0.92,
    "z_window": 60,
    "max_holding_seconds": 600,
    "cooldown_observations": 3,
    "sync_ms": 1000,
}


def strategy_config(
    description: str,
    engine: str,
    signal_model: str,
    **overrides: Any,
) -> dict[str, Any]:
    params = dict(STRATEGY_DEFAULTS)
    params.update(overrides)
    return {
        "description": description,
        "engine": engine,
        "signal_model": signal_model,
        "params": params,
    }


STRATEGIES = {
    "Trend momentum": strategy_config(
        "Mono-actif. Suit une pente Kalman robuste, coupe sur choc.",
        "single",
        "single_trend",
        entry_threshold=1.20,
        exit_threshold=0.30,
    ),
    "Mean reversion intraday": strategy_config(
        "Mono-actif. Fade des ecarts d'innovation quand le prix s'eloigne trop du latent.",
        "single",
        "single_mean_reversion",
        entry_threshold=1.80,
        exit_threshold=0.35,
        shock_threshold=4.50,
        max_holding_seconds=420,
    ),
    "Breakout impulse": strategy_config(
        "Mono-actif. Entre quand pente et surprise de prix vont dans le meme sens.",
        "single",
        "single_breakout",
        entry_threshold=1.15,
        secondary_threshold=0.65,
        exit_threshold=0.25,
    ),
    "Pullback continuation": strategy_config(
        "Mono-actif. Cherche un repli court dans une tendance Kalman deja installee.",
        "single",
        "single_pullback",
        entry_threshold=1.00,
        secondary_threshold=0.75,
        exit_threshold=0.20,
    ),
    "Shock fade": strategy_config(
        "Mono-actif. Fade prudent des innovations extremes avec sortie rapide.",
        "single",
        "single_shock_fade",
        entry_threshold=2.80,
        exit_threshold=0.45,
        shock_threshold=2.80,
        confirmation=2,
        max_holding_seconds=240,
    ),
    "Volatility breakout": strategy_config(
        "Mono-actif. Momentum court quand l'innovation est forte et confirmee par la pente.",
        "single",
        "single_vol_breakout",
        entry_threshold=1.55,
        secondary_threshold=0.35,
        exit_threshold=0.35,
        confirmation=2,
    ),
    "HMM directional": strategy_config(
        "Mono-actif. Le HMM choisit hausse, baisse, bruit ou choc.",
        "single",
        "hmm_directional",
        entry_threshold=0.70,
        exit_threshold=0.48,
        secondary_threshold=0.50,
    ),
    "HMM risk-off momentum": strategy_config(
        "Mono-actif. Momentum seulement si le regime est clair et sans choc.",
        "single",
        "hmm_risk_off",
        entry_threshold=0.76,
        exit_threshold=0.55,
        secondary_threshold=0.35,
        confirmation=2,
    ),
    "Relative value mean reversion": strategy_config(
        "Paire Y/X. Vend les exces du spread et cherche le retour a la moyenne.",
        "pair",
        "pair_mean_reversion",
        pair_input="level",
        replay_minutes=120,
        entry_threshold=2.00,
        exit_threshold=0.25,
        shock_threshold=5.00,
        z_window=70,
        sync_ms=1000,
    ),
    "Dynamic beta residual momentum": strategy_config(
        "Paire Y/X. Suit la continuation du residuel apres hedge beta dynamique.",
        "pair",
        "pair_residual_momentum",
        pair_input="returns",
        replay_minutes=60,
        entry_threshold=1.25,
        exit_threshold=0.35,
        z_window=60,
    ),
    "Pair breakout": strategy_config(
        "Paire Y/X. Cherche une cassure du spread avec continuation.",
        "pair",
        "pair_breakout",
        pair_input="level",
        replay_minutes=120,
        entry_threshold=2.25,
        exit_threshold=0.90,
        z_window=80,
    ),
    "Dispersion widening": strategy_config(
        "Paire Y/X. Suit un ecartement statistique quand la dispersion s'ouvre.",
        "pair",
        "pair_dispersion_widen",
        pair_input="returns",
        entry_threshold=1.65,
        exit_threshold=0.55,
        z_window=50,
    ),
    "Dispersion convergence": strategy_config(
        "Paire Y/X. Cherche la compression d'une dispersion devenue excessive.",
        "pair",
        "pair_convergence",
        pair_input="level",
        replay_minutes=120,
        entry_threshold=2.40,
        exit_threshold=0.45,
        z_window=90,
    ),
    "Beta-neutral trend": strategy_config(
        "Paire Y/X. Garde une exposition beta-neutre et suit la tendance residuelle.",
        "pair",
        "pair_beta_trend",
        pair_input="returns",
        entry_threshold=1.45,
        exit_threshold=0.40,
        z_window=70,
    ),
    "Stat arb conservative": strategy_config(
        "Paire Y/X. Version conservatrice : peu de trades, seuils plus stricts.",
        "pair",
        "pair_stat_arb",
        pair_input="level",
        replay_minutes=240,
        entry_threshold=2.80,
        exit_threshold=0.35,
        confirmation=4,
        z_window=100,
    ),
    "Residual shock fade": strategy_config(
        "Paire Y/X. Fade les chocs de spread apres hedge dynamique.",
        "pair",
        "pair_residual_shock_fade",
        pair_input="level",
        replay_minutes=120,
        entry_threshold=3.00,
        exit_threshold=0.60,
        confirmation=2,
        max_holding_seconds=360,
    ),
}

RISK_PROFILES = {
    "Prudent": {
        "target_leverage": 0.75,
        "max_session_loss_pct": 0.006,
        "max_trade_loss_pct": 0.0025,
        "max_trades": 25,
        "cooldown_observations": 8,
    },
    "Standard": {
        "target_leverage": 1.50,
        "max_session_loss_pct": 0.012,
        "max_trade_loss_pct": 0.005,
        "max_trades": 60,
        "cooldown_observations": 4,
    },
    "Agressif": {
        "target_leverage": 3.00,
        "max_session_loss_pct": 0.025,
        "max_trade_loss_pct": 0.010,
        "max_trades": 120,
        "cooldown_observations": 2,
    },
}

FRICTION_PROFILES = {
    "Faible": {"commission_bps": 0.25, "min_commission": 0.0, "slippage_ticks": 0.10},
    "Standard": {"commission_bps": 0.75, "min_commission": 0.0, "slippage_ticks": 0.25},
    "Stress test": {"commission_bps": 2.50, "min_commission": 1.0, "slippage_ticks": 1.00},
}

MARKET_SESSIONS = {
    "europe_index": {
        "label": "Indices Europe",
        "kind": "regular",
        "timezone": "Europe/Paris",
        "open": "09:00",
        "close": "17:35",
    },
    "us_index": {
        "label": "Indices US",
        "kind": "regular",
        "timezone": "America/New_York",
        "open": "09:30",
        "close": "16:15",
    },
    "commodity_24_5": {
        "label": "Matieres premieres 24/5",
        "kind": "weekday",
        "timezone": "UTC",
    },
    "fx_24_5": {
        "label": "FX 24/5",
        "kind": "weekday",
        "timezone": "UTC",
    },
    "crypto_24_7": {
        "label": "Crypto 24/7",
        "kind": "always",
        "timezone": "UTC",
    },
}

MARKET_SESSION_BY_ASSET = {
    "CAC 40": "europe_index",
    "DAX": "europe_index",
    "Euro Stoxx 50": "europe_index",
    "Nasdaq 100": "us_index",
    "S&P 500": "us_index",
    "Gold": "commodity_24_5",
    "Brent": "commodity_24_5",
    "EUR/USD": "fx_24_5",
    "Bitcoin": "crypto_24_7",
}


def _hhmm_to_minutes(value: str) -> int:
    hours, minutes = value.split(":", 1)
    return int(hours) * 60 + int(minutes)


def market_session_status(asset_name: str) -> dict[str, Any]:
    session_key = MARKET_SESSION_BY_ASSET.get(asset_name, "weekday")
    session = MARKET_SESSIONS.get(session_key, MARKET_SESSIONS["fx_24_5"])
    kind = session["kind"]

    if kind == "always":
        return {"open": True, "label": session["label"], "detail": "Ouvert 24/7"}

    now = datetime.now(ZoneInfo(session.get("timezone", "UTC")))
    weekday = now.weekday()

    if kind == "weekday":
        is_open = weekday < 5
        return {
            "open": is_open,
            "label": session["label"],
            "detail": "Ouvert 24/5" if is_open else "Ferme le week-end",
        }

    minutes = now.hour * 60 + now.minute
    open_minutes = _hhmm_to_minutes(session["open"])
    close_minutes = _hhmm_to_minutes(session["close"])
    is_open = weekday < 5 and open_minutes <= minutes <= close_minutes
    return {
        "open": is_open,
        "label": session["label"],
        "detail": (
            f"{session['open']} - {session['close']} "
            f"{session.get('timezone', 'UTC')}"
        ),
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
    "Chaque tick ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â dernier prix connu": 0,
    "1 seconde": 1000,
    "5 secondes": 5000,
    "15 secondes": 15000,
    "1 minute": 60000,
}


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
    rows = [row for row in catalogue if row.get("symbol")]
    rows_by_symbol: dict[str, dict[str, Any]] = {}

    for row in rows:
        rows_by_symbol.setdefault(str(row["symbol"]).upper(), row)

    resolved: dict[str, str] = {}
    unresolved: list[str] = []

    for market_name, market_settings in MARKETS.items():
        selected_row = None

        for candidate in market_settings["candidates"]:
            selected_row = rows_by_symbol.get(candidate.upper())
            if selected_row is not None:
                break

        if selected_row is None:
            ranked = sorted(
                rows,
                key=lambda row: catalogue_score(row, market_settings["search"]),
                reverse=True,
            )
            if ranked and catalogue_score(ranked[0], market_settings["search"]) > 0:
                selected_row = ranked[0]

        if selected_row is None:
            unresolved.append(market_name)
        else:
            resolved[market_name] = str(selected_row["symbol"])

    return resolved, unresolved


try:
    default_api_key = st.secrets["LSE_API_KEY"]
except Exception:
    default_api_key = os.getenv("LSE_API_KEY", "")

with st.sidebar:
    strategy = st.selectbox(
        "Strategie",
        options=list(STRATEGIES),
        key="paper_strategy",
    )
    strategy_meta = STRATEGIES[strategy]
    strategy_params = strategy_meta["params"]
    is_pair = strategy_meta["engine"] == "pair"
    st.caption(strategy_meta["description"])

    default_y = (
        available_markets.index("Nasdaq 100")
        if "Nasdaq 100" in available_markets
        else 0
    )

    asset_y = st.selectbox(
        "Actif trade",
        options=available_markets,
        index=default_y,
        key="paper_asset_y",
    )
    symbol_y = resolved_symbols[asset_y]

    if is_pair:
        x_options = [market for market in available_markets if market != asset_y]
        if not x_options:
            st.error("Cette strategie a besoin de deux actifs disponibles.")
            st.stop()
        preferred_x = "S&P 500" if asset_y != "S&P 500" else "Nasdaq 100"
        default_x = x_options.index(preferred_x) if preferred_x in x_options else 0
        asset_x = st.selectbox(
            "Actif hedge",
            options=x_options,
            index=default_x,
            key="paper_asset_x",
        )
        symbol_x = resolved_symbols[asset_x]
        st.caption("Mode paire : Y est la jambe active, X est le hedge.")
    else:
        asset_x = None
        symbol_x = None
        st.caption("Mode mono-actif : le signal et le P&L utilisent uniquement Y.")

    y_status = market_session_status(asset_y)
    x_status = market_session_status(asset_x) if asset_x else None
    market_open = y_status["open"] and (x_status["open"] if x_status else True)
    status_text = f"{asset_y} : {y_status['detail']}"
    if x_status:
        status_text += f" | {asset_x} : {x_status['detail']}"
    if market_open:
        st.success(f"Marche ouvert - {status_text}")
    else:
        st.warning(f"Marche ferme - {status_text}")

    st.divider()
    st.markdown("#### Execution papier")

    account_currency = st.selectbox(
        "Devise",
        ["EUR", "USD", "GBP", "CHF"],
        index=0,
        key="paper_currency",
    )
    account_equity = st.number_input(
        "Capital de reference",
        min_value=100.0,
        max_value=100_000_000.0,
        value=100_000.0,
        step=10_000.0,
        key="paper_equity",
    )
    risk_label = st.selectbox(
        "Profil de risque",
        options=list(RISK_PROFILES),
        index=1,
        key="paper_risk_profile",
    )
    friction_label = st.selectbox(
        "Friction",
        options=list(FRICTION_PROFILES),
        index=1,
        key="paper_friction_profile",
    )
    allow_short = st.toggle(
        "Autoriser les shorts",
        value=True,
        key="paper_allow_short",
    )
    cockpit_height = st.slider(
        "Hauteur cockpit",
        620,
        1400,
        820,
        20,
        key="paper_cockpit_height",
    )

    risk = RISK_PROFILES[risk_label]
    friction = FRICTION_PROFILES[friction_label]

    replay_minutes = int(strategy_params["replay_minutes"])
    trade_replay = False
    terminal_verbose = False
    sync_ms = int(strategy_params["sync_ms"]) if is_pair else 0
    reactivity = int(strategy_params["reactivity"])
    observation_trust = int(strategy_params["observation_trust"])
    confirmation = int(strategy_params["confirmation"])
    norm_window = int(strategy_params["norm_window"])
    entry_threshold = float(strategy_params["entry_threshold"])
    exit_threshold = float(strategy_params["exit_threshold"])
    shock_threshold = float(strategy_params["shock_threshold"])
    secondary_threshold = float(strategy_params["secondary_threshold"])
    hmm_persistence = float(strategy_params["hmm_persistence"])
    z_window = int(strategy_params["z_window"])

    target_leverage = float(risk["target_leverage"])
    max_session_loss = float(account_equity) * float(risk["max_session_loss_pct"])
    max_trade_loss = float(account_equity) * float(risk["max_trade_loss_pct"])
    max_holding_seconds = int(strategy_params["max_holding_seconds"])
    max_trades = int(risk["max_trades"])
    cooldown_observations = int(risk["cooldown_observations"])

    point_value_y = float(MARKETS[asset_y]["point_value"])
    tick_size_y = float(MARKETS[asset_y]["tick_size"])
    fx_y = 1.0
    point_value_x = float(MARKETS[asset_x]["point_value"]) if asset_x else 1.0
    tick_size_x = float(MARKETS[asset_x]["tick_size"]) if asset_x else 0.1
    fx_x = 1.0
    quantity_step = 0.01
    commission_bps = float(friction["commission_bps"])
    min_commission = float(friction["min_commission"])
    extra_slippage_ticks = float(friction["slippage_ticks"])

    st.caption(
        f"Preset : replay {replay_minutes} min, levier {target_leverage:.2f}x, "
        f"stop trade {max_trade_loss:.0f} {account_currency}, "
        f"kill session {max_session_loss:.0f} {account_currency}."
    )

    st.caption(f"Y : `{symbol_y}`")
    if symbol_x:
        st.caption(f"X : `{symbol_x}`")

    if unresolved_markets:
        with st.expander("Marches non trouves"):
            st.write(", ".join(unresolved_markets))

settings = {
    "apiKey": api_key,
    "strategy": strategy,
    "strategyEngine": strategy_meta["engine"],
    "signalModel": strategy_meta["signal_model"],
    "pairInput": strategy_params.get("pair_input", "level"),
    "assetY": asset_y,
    "assetX": asset_x,
    "symbolY": symbol_y,
    "symbolX": symbol_x,
    "isPair": is_pair,
    "marketOpen": market_open,
    "marketStatus": status_text,
    "marketSessionY": MARKET_SESSIONS[MARKET_SESSION_BY_ASSET.get(asset_y, "fx_24_5")],
    "marketSessionX": (
        MARKET_SESSIONS[MARKET_SESSION_BY_ASSET.get(asset_x, "fx_24_5")]
        if asset_x
        else None
    ),
    "replayMinutes": replay_minutes,
    "tradeReplay": trade_replay,
    "terminalVerbose": terminal_verbose,
    "syncMs": sync_ms,
    "reactivity": reactivity,
    "observationTrust": observation_trust,
    "confirmation": confirmation,
    "normWindow": int(norm_window),
    "entryThreshold": entry_threshold,
    "exitThreshold": exit_threshold,
    "shockThreshold": shock_threshold,
    "secondaryThreshold": secondary_threshold,
    "hmmPersistence": hmm_persistence,
    "zWindow": z_window,
    "accountCurrency": account_currency,
    "accountEquity": account_equity,
    "targetLeverage": target_leverage,
    "pointValueY": point_value_y,
    "pointValueX": point_value_x,
    "tickSizeY": tick_size_y,
    "tickSizeX": tick_size_x,
    "fxY": fx_y,
    "fxX": fx_x,
    "quantityStep": quantity_step,
    "commissionBps": commission_bps,
    "minCommission": min_commission,
    "extraSlippageTicks": extra_slippage_ticks,
    "allowShort": allow_short,
    "maxSessionLoss": max_session_loss,
    "maxTradeLoss": max_trade_loss,
    "maxHoldingSeconds": max_holding_seconds,
    "maxTrades": int(max_trades),
    "cooldownObservations": cooldown_observations,
    "cockpitHeight": int(cockpit_height),
}

# Le cockpit est une iframe : toute modification de `settings` rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©gÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©nÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¨re le
# srcdoc, recrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e lÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢iframe, coupe le WebSocket et remet la session ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  zÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©ro.
# Les rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©glages ne sont donc appliquÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s que sur demande explicite, ce qui laisse
# les curseurs libres pendant quÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢une session tourne.
LIVE_KEY = "paper_live_settings"

with st.sidebar:
    apply_clicked = st.button(
        "Appliquer & (re)lancer le cockpit",
        type="primary",
        use_container_width=True,
        key="paper_apply",
    )

if apply_clicked:
    st.session_state[LIVE_KEY] = settings

live_settings = st.session_state.get(LIVE_KEY)

if live_settings is None:
    st.info(
        "Configure la stratÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©gie, lÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢exÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©cution et le risque dans la sidebar, "
        "puis clique sur **Appliquer & (re)lancer le cockpit**."
    )
    st.stop()

if "signalModel" not in live_settings:
    st.session_state[LIVE_KEY] = settings
    live_settings = settings

if live_settings != settings:
    st.warning(
        "Des paramÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¨tres ont ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©tÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© modifiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s mais ne sont pas appliquÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s. "
        "Le cockpit tourne toujours avec la configuration prÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©cÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©dente. "
        "Clique sur **Appliquer & (re)lancer le cockpit** pour les prendre en "
        "compte ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â la session en cours sera rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©initialisÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e.",
        icon="ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã‚Â¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¸Ãƒâ€šÃ‚Â",
    )

html_template = r"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root{color-scheme:dark;--bg:#050708;--panel:#0a0f15;--panel2:#0d131b;--border:#202a36;--text:#edf2f7;--muted:#788596;--green:#28b69f;--red:#ef5b5b;--yellow:#d9b44a;--blue:#76b7e5;--purple:#a28af7}
*{box-sizing:border-box}html,body{height:100%}body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,system-ui,sans-serif;overflow:hidden}
button{border:1px solid var(--border);background:#111923;color:var(--text);border-radius:7px;padding:6px 10px;cursor:pointer;font-weight:650;font-size:11px}
button:hover{border-color:#425267;background:#17212d}button.primary{background:#12392f;border-color:#1f6c59;color:#b9f4e4}button.danger{background:#38191b;border-color:#6d292d;color:#ffc6c6}
button.view{padding:5px 9px;font-size:10px;letter-spacing:.06em;background:#0b1119;color:var(--muted)}button.view.active{background:#17212d;border-color:#425267;color:var(--text)}
.viewgroup{display:flex;gap:4px}
.page{height:100vh;display:flex;flex-direction:column;gap:6px;padding:7px}
.topbar{flex:0 0 auto;display:flex;align-items:center;gap:8px;flex-wrap:wrap;border:1px solid var(--border);background:var(--panel);border-radius:10px;padding:7px 9px}
.brand,.connection,.metric-value,.diag-value,.terminal,table,.session-summary{font-family:"JetBrains Mono","Cascadia Code",Consolas,monospace}
.brand{font-size:12px;font-weight:800;letter-spacing:.04em}.connection{color:var(--muted);font-size:10px;min-width:200px;margin-right:auto}
.metrics{flex:0 0 auto;display:grid;grid-template-columns:repeat(8,minmax(96px,1fr));gap:6px}
.metric{border:1px solid var(--border);background:var(--panel2);border-radius:8px;padding:6px 8px}
.metric-label{color:var(--muted);font-size:9px;text-transform:uppercase;letter-spacing:.07em;margin-bottom:4px}
.metric-value{font-size:14px;font-weight:760;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.metric-sub{color:var(--muted);font-size:9px;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
/* Le workspace remplit exactement la hauteur restante de l'iframe : charts,
   terminal et blotter sont visibles ensemble, sans scroll de page. */
.workspace{flex:1 1 auto;min-height:0;display:grid;gap:6px}
.workspace[data-view="cockpit"]{grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);grid-template-rows:minmax(0,1.06fr) minmax(0,1fr)}
.workspace[data-view="cockpit"] [data-cell="model"]{grid-row:1;grid-column:1}
.workspace[data-view="cockpit"] [data-cell="equity"]{grid-row:1;grid-column:2}
.workspace[data-view="cockpit"] [data-cell="terminal"]{grid-row:2;grid-column:1}
.workspace[data-view="cockpit"] [data-cell="blotter"]{grid-row:2;grid-column:2}
.workspace[data-view="charts"]{grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);grid-template-rows:minmax(0,1fr)}
.workspace[data-view="charts"] [data-cell="terminal"],.workspace[data-view="charts"] [data-cell="blotter"]{display:none}
.workspace[data-view="terminal"]{grid-template-columns:minmax(0,1fr);grid-template-rows:minmax(0,1fr)}
.workspace[data-view="terminal"] [data-cell="model"],.workspace[data-view="terminal"] [data-cell="equity"],.workspace[data-view="terminal"] [data-cell="blotter"]{display:none}
.workspace[data-view="blotter"]{grid-template-columns:minmax(0,1fr);grid-template-rows:minmax(0,1fr)}
.workspace[data-view="blotter"] [data-cell="model"],.workspace[data-view="blotter"] [data-cell="equity"],.workspace[data-view="blotter"] [data-cell="terminal"]{display:none}
.panel{display:flex;flex-direction:column;min-height:0;min-width:0;overflow:hidden;border:1px solid var(--border);background:var(--panel);border-radius:10px}
.panel-title{flex:0 0 28px;display:flex;align-items:center;gap:8px;padding:0 9px;border-bottom:1px solid var(--border);color:#cbd5e1;font-family:"JetBrains Mono",Consolas,monospace;font-size:10px;font-weight:780;letter-spacing:.05em}
.chart{flex:1 1 auto;min-height:0;width:100%}
.diagnostics{flex:0 0 auto;display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:5px;padding:6px;border-top:1px solid var(--border)}
.diag{background:#0d131b;border:1px solid #1c2733;border-radius:6px;padding:5px 6px;min-width:0}
.diag-label{color:var(--muted);font-size:8px;text-transform:uppercase;letter-spacing:.06em}
.diag-value{font-size:11px;font-weight:700;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.terminal{flex:1 1 auto;min-height:0;overflow-y:auto;padding:8px 10px;background:#030506;font-size:11px;line-height:1.5;white-space:pre-wrap}
.line{color:#9da9b8}.line.BUY,.line.LONG,.line.PROFIT{color:#67dabf}.line.SELL,.line.SHORT,.line.LOSS,.line.KILL{color:#ff8585}.line.EXIT,.line.RISK,.line.SHOCK{color:#e4c462}.line.SYSTEM{color:#77b9eb}.line.WAIT,.line.HOLD{color:#7b8796}
.blotter-wrap{flex:1 1 auto;min-height:0;overflow:auto;background:#050708}
table{width:100%;border-collapse:collapse;font-size:10px}
th{position:sticky;top:0;z-index:2;background:#101720;color:#8f9aaa;font-weight:650;text-align:left;padding:6px;border-bottom:1px solid var(--border)}
td{padding:6px;border-bottom:1px solid #151d27;color:#c4ceda;white-space:nowrap}
.positive{color:var(--green)!important}.negative{color:var(--red)!important}
.footer-actions{flex:0 0 auto;display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.session-summary{margin-left:auto;color:var(--muted);font-size:9px}
@media(max-width:1200px){.metrics{grid-template-columns:repeat(4,minmax(96px,1fr))}}
@media(max-width:820px){.metrics{grid-template-columns:repeat(2,minmax(96px,1fr))}.workspace[data-view="cockpit"],.workspace[data-view="charts"]{grid-template-columns:minmax(0,1fr)}.diagnostics{grid-template-columns:repeat(3,minmax(0,1fr))}}
</style>
</head>
<body>
<div class="page">
<div class="topbar">
<div class="brand" id="brand"></div>
<div class="connection" id="connection">BOOTINGÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦</div>
<div class="viewgroup" id="viewGroup">
<button class="view active" data-view="cockpit">COCKPIT</button>
<button class="view" data-view="charts">CHARTS</button>
<button class="view" data-view="terminal">TERMINAL</button>
<button class="view" data-view="blotter">BLOTTER</button>
</div>
<button class="primary" id="startButton">START SESSION</button>
<button class="danger" id="stopButton">STOP &amp; FLATTEN</button>
<button id="resetButton">RESET</button>
<button id="fullscreenButton">FULLSCREEN</button>
</div>
<div class="metrics">
<div class="metric"><div class="metric-label">Session</div><div class="metric-value" id="sessionMetric">IDLE</div><div class="metric-sub" id="sessionSub">En attente</div></div>
<div class="metric"><div class="metric-label">Signal</div><div class="metric-value" id="signalMetric">WAIT</div><div class="metric-sub" id="signalSub">Warm-up</div></div>
<div class="metric"><div class="metric-label">Position</div><div class="metric-value" id="positionMetric">FLAT</div><div class="metric-sub" id="positionSub">0 unitÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©</div></div>
<div class="metric"><div class="metric-label">P&L net</div><div class="metric-value" id="netMetric">0.00</div><div class="metric-sub" id="netSub">0.00 bps</div></div>
<div class="metric"><div class="metric-label">P&L latent</div><div class="metric-value" id="unrealizedMetric">0.00</div><div class="metric-sub" id="unrealizedSub">Flat</div></div>
<div class="metric"><div class="metric-label">Ticks capturÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s</div><div class="metric-value" id="ticksMetric">0.0</div><div class="metric-sub" id="ticksSub">Equivalent Y</div></div>
<div class="metric"><div class="metric-label">Trades / win rate</div><div class="metric-value" id="tradesMetric">0 / ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</div><div class="metric-sub" id="tradesSub">Profit factor ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</div></div>
<div class="metric"><div class="metric-label">Max drawdown</div><div class="metric-value" id="drawdownMetric">0.00</div><div class="metric-sub" id="drawdownSub">CoÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â»ts 0.00</div></div>
</div>
<div class="workspace" id="workspace" data-view="cockpit">
<div class="panel" data-cell="model">
<div class="panel-title">MODEL</div>
<div id="modelChart" class="chart"></div>
<div class="diagnostics">
<div class="diag"><div class="diag-label">Prix Y</div><div class="diag-value" id="diagPriceY">ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</div></div>
<div class="diag"><div class="diag-label">Prix X</div><div class="diag-value" id="diagPriceX">ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</div></div>
<div class="diag"><div class="diag-label">Pente / beta</div><div class="diag-value" id="diagPrimary">ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</div></div>
<div class="diag"><div class="diag-label">Innovation / z</div><div class="diag-value" id="diagSecondary">ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</div></div>
<div class="diag"><div class="diag-label">RÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©gime</div><div class="diag-value" id="diagRegime">ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â</div></div>
<div class="diag"><div class="diag-label">Levier rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©el</div><div class="diag-value" id="diagLeverage">0.00ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â</div></div>
</div>
</div>
<div class="panel" data-cell="equity">
<div class="panel-title">SESSION P&L</div>
<div id="equityChart" class="chart"></div>
</div>
<div class="panel" data-cell="terminal">
<div class="panel-title">LIVE DECISION TERMINAL</div>
<div id="terminal" class="terminal"></div>
</div>
<div class="panel" data-cell="blotter">
<div class="panel-title">TRADE BLOTTER</div>
<div class="blotter-wrap"><table><thead><tr><th>#</th><th>Direction</th><th>EntrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e</th><th>Sortie</th><th>DurÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e</th><th>Gross</th><th>CoÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â»ts</th><th>Net</th><th>Raison</th></tr></thead><tbody id="blotterBody"></tbody></table></div>
</div>
</div>
<div class="footer-actions">
<button id="exportTradesButton">EXPORT TRADES CSV</button>
<button id="exportDecisionsButton">EXPORT DECISIONS CSV</button>
<button id="exportSummaryButton">EXPORT SUMMARY CSV</button>
<div class="session-summary" id="sessionSummary">PAPER ONLY ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· NO LIVE ORDERS</div>
</div>
</div>
<script>
const SETTINGS = __SETTINGS__;

const API_KEY=SETTINGS.apiKey,STRATEGY=SETTINGS.strategy,SIGNAL_MODEL=SETTINGS.signalModel,PAIR_INPUT=SETTINGS.pairInput||"level",SYMBOL_Y=SETTINGS.symbolY,SYMBOL_X=SETTINGS.symbolX,ASSET_Y=SETTINGS.assetY,ASSET_X=SETTINGS.assetX;
const IS_PAIR=SETTINGS.strategyEngine==="pair",HAS_X=Boolean(SYMBOL_X&&SYMBOL_X!==SYMBOL_Y),REPLAY_MINUTES=Number(SETTINGS.replayMinutes),TRADE_REPLAY=Boolean(SETTINGS.tradeReplay),VERBOSE=Boolean(SETTINGS.terminalVerbose),SYNC_MS=Number(SETTINGS.syncMs);
const REACTIVITY=Number(SETTINGS.reactivity),OBSERVATION_TRUST=Number(SETTINGS.observationTrust),CONFIRMATION=Number(SETTINGS.confirmation),ENTRY_THRESHOLD=Number(SETTINGS.entryThreshold),EXIT_THRESHOLD=Number(SETTINGS.exitThreshold),SHOCK_THRESHOLD=Number(SETTINGS.shockThreshold),SECONDARY_THRESHOLD=Number(SETTINGS.secondaryThreshold),HMM_PERSISTENCE=Number(SETTINGS.hmmPersistence),Z_WINDOW=Number(SETTINGS.zWindow);
const ACCOUNT_CURRENCY=SETTINGS.accountCurrency,ACCOUNT_EQUITY=Number(SETTINGS.accountEquity),TARGET_LEVERAGE=Number(SETTINGS.targetLeverage),POINT_VALUE_Y=Number(SETTINGS.pointValueY),POINT_VALUE_X=Number(SETTINGS.pointValueX),TICK_SIZE_Y=Number(SETTINGS.tickSizeY),TICK_SIZE_X=Number(SETTINGS.tickSizeX),FX_Y=Number(SETTINGS.fxY),FX_X=Number(SETTINGS.fxX),QUANTITY_STEP=Number(SETTINGS.quantityStep),COMMISSION_BPS=Number(SETTINGS.commissionBps),MIN_COMMISSION=Number(SETTINGS.minCommission),EXTRA_SLIPPAGE_TICKS=Number(SETTINGS.extraSlippageTicks),ALLOW_SHORT=Boolean(SETTINGS.allowShort),MAX_SESSION_LOSS=Number(SETTINGS.maxSessionLoss),MAX_TRADE_LOSS=Number(SETTINGS.maxTradeLoss),MAX_HOLDING_SECONDS=Number(SETTINGS.maxHoldingSeconds),MAX_TRADES=Number(SETTINGS.maxTrades),COOLDOWN_OBSERVATIONS=Number(SETTINGS.cooldownObservations);

/* Normalisation : la pente et l'innovation du Kalman sont ramenÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©es ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  leur
   propre ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©chelle roulante. Sans ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§a, "ÃƒÆ’Ã‚ÂÃƒâ€ Ã¢â‚¬â„¢" ne veut rien dire : diviser la pente
   par l'ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©cart-type des diffÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©rences tick-ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â -tick donne un slopeZ dont le sd rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©el
   vaut ~0.25, donc un seuil d'entrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e de 0.65 est ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  ~2.6 sd dans la queue. */
const NORM_WINDOW=Math.max(120,Number(SETTINGS.normWindow)||750);
const NORM_MIN=Math.max(60,Math.floor(NORM_WINDOW*0.2));
const PAIR_WARMUP=PAIR_INPUT==="level"?240:60;
const CHART_MIN_INTERVAL_MS=150;
const MARKET_SESSION_Y=SETTINGS.marketSessionY||null,MARKET_SESSION_X=SETTINGS.marketSessionX||null,INITIAL_MARKET_OPEN=Boolean(SETTINGS.marketOpen),MARKET_STATUS=SETTINGS.marketStatus||"";
const HMM_MODELS=new Set(["hmm_directional","hmm_risk_off"]);
const PAIR_MEAN_REVERSION_MODELS=new Set(["pair_mean_reversion","pair_convergence","pair_stat_arb","pair_residual_shock_fade"]);

const COLORS={background:"#050708",grid:"#1b2530",text:"#d9e2ec",muted:"#748192",green:"#28b69f",red:"#ef5b5b",yellow:"#d9b44a",blue:"#76b7e5",purple:"#a28af7",raw:"#d9a36c"};
const currencyPrefix=({EUR:"ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬",USD:"$",GBP:"ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£",CHF:"CHF "}[ACCOUNT_CURRENCY]||`${ACCOUNT_CURRENCY} `);
const $=id=>document.getElementById(id);
const DOM={brand:$("brand"),connection:$("connection"),workspace:$("workspace"),startButton:$("startButton"),stopButton:$("stopButton"),resetButton:$("resetButton"),fullscreenButton:$("fullscreenButton"),terminal:$("terminal"),blotterBody:$("blotterBody"),sessionMetric:$("sessionMetric"),sessionSub:$("sessionSub"),signalMetric:$("signalMetric"),signalSub:$("signalSub"),positionMetric:$("positionMetric"),positionSub:$("positionSub"),netMetric:$("netMetric"),netSub:$("netSub"),unrealizedMetric:$("unrealizedMetric"),unrealizedSub:$("unrealizedSub"),ticksMetric:$("ticksMetric"),ticksSub:$("ticksSub"),tradesMetric:$("tradesMetric"),tradesSub:$("tradesSub"),drawdownMetric:$("drawdownMetric"),drawdownSub:$("drawdownSub"),diagPriceY:$("diagPriceY"),diagPriceX:$("diagPriceX"),diagPrimary:$("diagPrimary"),diagSecondary:$("diagSecondary"),diagRegime:$("diagRegime"),diagLeverage:$("diagLeverage"),sessionSummary:$("sessionSummary"),exportTradesButton:$("exportTradesButton"),exportDecisionsButton:$("exportDecisionsButton"),exportSummaryButton:$("exportSummaryButton")};
DOM.brand.textContent=`SHADOW TRADER :: ${STRATEGY.toUpperCase()} :: ${SYMBOL_Y}${SYMBOL_X?` / ${SYMBOL_X}`:""}`;

const plotConfig={responsive:true,displaylogo:false,scrollZoom:true,doubleClick:"reset+autosize",modeBarButtonsToAdd:["pan2d","zoomIn2d","zoomOut2d","autoScale2d","resetScale2d"],modeBarButtonsToRemove:["lasso2d","select2d"]};
function commonLayout(title,uirevision){return{template:"plotly_dark",paper_bgcolor:COLORS.background,plot_bgcolor:COLORS.background,autosize:true,margin:{l:32,r:58,t:34,b:26},title:{text:title,x:.01,y:.99,yanchor:"top",font:{size:11,color:COLORS.text,family:"JetBrains Mono, Consolas, monospace"}},hovermode:"x unified",dragmode:"pan",uirevision,legend:{orientation:"h",x:0,y:1.10,font:{size:9,color:COLORS.muted},bgcolor:"rgba(0,0,0,0)"},xaxis:{gridcolor:COLORS.grid,zeroline:false,showspikes:true,spikecolor:COLORS.muted},yaxis:{gridcolor:COLORS.grid,zeroline:false,side:"right",automargin:true}}}
function finite(value,fallback=null){const n=Number(value);return Number.isFinite(n)?n:fallback}
function parseTimestamp(value){if(typeof value==="number")return new Date(value<1e12?value*1000:value);const d=new Date(value);return Number.isNaN(d.getTime())?new Date():d}
function formatNumber(value,decimals=2){return Number.isFinite(value)?value.toLocaleString(undefined,{minimumFractionDigits:decimals,maximumFractionDigits:decimals}):"ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â"}
function formatMoney(value){return `${currencyPrefix}${value>0?"+":""}${formatNumber(value,2)}`}
function formatPrice(value){if(!Number.isFinite(value))return"ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â";const d=Math.abs(value)<10?5:(Math.abs(value)<100?4:2);return formatNumber(value,d)}
function signed(value,decimals=2){return Number.isFinite(value)?`${value>=0?"+":""}${value.toFixed(decimals)}`:"ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â"}
function variance(values){const a=values.filter(Number.isFinite);if(a.length<2)return 1e-8;const m=a.reduce((s,v)=>s+v,0)/a.length;return a.reduce((s,v)=>s+(v-m)**2,0)/a.length}
function rollingZ(values,windowSize){const a=values.slice(-Math.max(10,windowSize));if(a.length<10)return null;const m=a.reduce((s,v)=>s+v,0)/a.length,sd=Math.sqrt(variance(a));return !Number.isFinite(sd)||sd<1e-12?0:(a[a.length-1]-m)/sd}
/* RMS roulant autour de zÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©ro : contrairement ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  rollingZ, ne retire pas la
   moyenne, donc une tendance soutenue reste visible au lieu d'ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªtre absorbÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e. */
function rollingRms(values,windowSize){const a=values.length>windowSize?values.slice(values.length-windowSize):values;let s=0,n=0;for(const v of a){if(Number.isFinite(v)){s+=v*v;n++}}return n?Math.sqrt(s/n):null}
function roundQuantity(value){if(!Number.isFinite(value)||value<=0)return 0;const step=Math.max(QUANTITY_STEP,1e-8);return Math.floor(value/step)*step}
function canonicalSymbol(symbol){const s=String(symbol||"").toUpperCase();if(s===String(SYMBOL_Y).toUpperCase())return"Y";if(SYMBOL_X&&s===String(SYMBOL_X).toUpperCase())return"X";return null}
function nowIso(){return new Date().toISOString()}
function zonedParts(date,timeZone){
    const parts=new Intl.DateTimeFormat("en-US",{timeZone,weekday:"short",hour:"2-digit",minute:"2-digit",hour12:false}).formatToParts(date);
    const map=Object.fromEntries(parts.map(p=>[p.type,p.value]));
    const days={Mon:1,Tue:2,Wed:3,Thu:4,Fri:5,Sat:6,Sun:0};
    return{day:days[map.weekday]??0,minutes:Number(map.hour)*60+Number(map.minute)}
}
function hhmm(value){const [h,m]=String(value||"00:00").split(":").map(Number);return h*60+m}
function sessionOpen(session,date=new Date()){
    if(!session)return true;
    if(session.kind==="always")return true;
    const p=zonedParts(date,session.timezone||"UTC");
    if(session.kind==="weekday")return p.day>=1&&p.day<=5;
    if(session.kind==="regular")return p.day>=1&&p.day<=5&&p.minutes>=hhmm(session.open)&&p.minutes<=hhmm(session.close);
    return true
}
function marketOpenNow(){
    const yOpen=sessionOpen(MARKET_SESSION_Y);
    const xOpen=!IS_PAIR||sessionOpen(MARKET_SESSION_X);
    return yOpen&&xOpen
}
function closedMarketReason(){return MARKET_STATUS?`Marche ferme: ${MARKET_STATUS}`:"Marche ferme"}
function updateComparison(timestamp){
    if(!HAS_X||!market.Y||!market.X)return;
    if(comparison.baseY===null||comparison.baseX===null){
        comparison.baseY=market.Y.price;
        comparison.baseX=market.X.price;
    }
    if(!Number.isFinite(comparison.baseY)||!Number.isFinite(comparison.baseX)||comparison.baseY===0||comparison.baseX===0)return;
    comparison.timestamps.push(timestamp);
    comparison.normalizedY.push(market.Y.price/comparison.baseY*100);
    comparison.normalizedX.push(market.X.price/comparison.baseX*100);
    for(const a of [comparison.timestamps,comparison.normalizedY,comparison.normalizedX])if(a.length>5000)a.splice(0,a.length-5000);
}

function logLine(type,message,timestamp=new Date()){
    const time=timestamp.toLocaleTimeString([],{hour12:false,hour:"2-digit",minute:"2-digit",second:"2-digit",fractionalSecondDigits:3});
    portfolio.logs.push({timestamp:timestamp.toISOString(),type,message});
    if(portfolio.logs.length>5000)portfolio.logs.splice(0,portfolio.logs.length-5000);
    const e=document.createElement("div");e.className=`line ${type}`;e.textContent=`[${time}] ${type.padEnd(7," ")} | ${message}`;DOM.terminal.appendChild(e);
    while(DOM.terminal.children.length>800)DOM.terminal.removeChild(DOM.terminal.firstChild);
    DOM.terminal.scrollTop=DOM.terminal.scrollHeight;
}
function logVerbose(type,message,timestamp){if(VERBOSE)logLine(type,message,timestamp)}
function downloadCsv(filename,rows){
    if(!rows.length){logLine("SYSTEM",`Aucune donnÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  exporter pour ${filename}.`);return}
    const columns=Array.from(rows.reduce((set,row)=>{Object.keys(row).forEach(k=>set.add(k));return set},new Set()));
    const esc=v=>`"${(v===null||v===undefined?"":String(v)).replaceAll('"','""')}"`;
    const csv=[columns.map(esc).join(","),...rows.map(row=>columns.map(c=>esc(row[c])).join(","))].join("\n");
    const blob=new Blob([csv],{type:"text/csv;charset=utf-8"}),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=filename;a.click();URL.revokeObjectURL(url);
}

const market={Y:null,X:null,previousY:null,previousX:null,bucket:null,bucketY:null,bucketX:null,lastPairSignature:null,liveSeen:false};
const kalman={state:null,covariance:null,differences:[],trendBuffer:[],innovationBuffer:[],timestamps:[],observed:[],filtered:[],slopeZ:[],innovationZ:[]};
const hmm={posterior:[.82,.06,.06,.06],candidate:0,candidateCount:0,confirmedState:0,duration:0};
const regression={state:null,covariance:null,warmup:[],xBar:0,residualVariance:1e-8,residuals:[],spread:[],momentum:[],cumulativeResidual:0,cumulativeSeries:[],timestamps:[],beta:[],zscore:[],normalizedY:[],normalizedX:[],baseY:null,baseX:null};
const comparison={timestamps:[],normalizedY:[],normalizedX:[],baseY:null,baseX:null};
const portfolio={active:TRADE_REPLAY,locked:false,startedAt:TRADE_REPLAY?new Date():null,stoppedAt:null,position:0,trade:null,realized:0,grossRealized:0,unrealized:0,costs:0,currentTicks:0,totalTicks:0,currentTarget:0,candidateTarget:0,candidateCount:0,cooldown:0,trades:[],decisions:[],logs:[],equityTimestamps:[],equityNet:[],equityRealized:[],peakNet:0,maxDrawdown:0,observations:0,lastSignalLabel:"WAIT",lastSignalReason:"Warm-up",lastStateFingerprint:null};

function resetPortfolioState(){
    Object.assign(portfolio,{active:TRADE_REPLAY,locked:false,startedAt:TRADE_REPLAY?new Date():null,stoppedAt:null,position:0,trade:null,realized:0,grossRealized:0,unrealized:0,costs:0,currentTicks:0,totalTicks:0,currentTarget:0,candidateTarget:0,candidateCount:0,cooldown:0,trades:[],decisions:[],logs:[],equityTimestamps:[],equityNet:[],equityRealized:[],peakNet:0,maxDrawdown:0,observations:0,lastSignalLabel:"WAIT",lastSignalReason:"Warm-up",lastStateFingerprint:null});
    DOM.terminal.innerHTML="";DOM.blotterBody.innerHTML="";logLine("SYSTEM","Paper engine rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©initialisÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©. Aucun ordre rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©el ne sera envoyÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©.");
}

function updateKalman(timestamp,price){
    if(kalman.observed.length){const d=price-kalman.observed[kalman.observed.length-1];if(Number.isFinite(d)){kalman.differences.push(d);if(kalman.differences.length>300)kalman.differences.shift()}}
    const baseVariance=Math.max(variance(kalman.differences),price*price*1e-12,1e-10),qMultiplier=10**((REACTIVITY-5)/2),rMultiplier=10**((6-OBSERVATION_TRUST)/2),qLevel=baseVariance*.035*qMultiplier,qTrend=baseVariance*.0015*qMultiplier,measurementVariance=baseVariance*Math.max(rMultiplier,1e-4);
    let innovation=0,innovationVariance=baseVariance+measurementVariance;
    if(kalman.state===null){kalman.state=[price,0];kalman.covariance=[[baseVariance*10,0],[0,baseVariance]]}
    else{
        let [level,trend]=kalman.state,[[p00,p01],[p10,p11]]=kalman.covariance;
        const predictedLevel=level+trend,predictedTrend=trend,pp00=p00+p01+p10+p11+qLevel,pp01=p01+p11,pp10=p10+p11,pp11=p11+qTrend;
        innovation=price-predictedLevel;innovationVariance=pp00+measurementVariance;
        const k0=pp00/innovationVariance,k1=pp10/innovationVariance;
        level=predictedLevel+k0*innovation;trend=predictedTrend+k1*innovation;
        const np00=(1-k0)*pp00,np01=(1-k0)*pp01,np10=pp10-k1*pp00,np11=pp11-k1*pp01,off=(np01+np10)/2;
        kalman.state=[level,trend];kalman.covariance=[[Math.max(np00,1e-14),off],[off,Math.max(np11,1e-14)]];
    }
    const level=kalman.state[0],trend=kalman.state[1];
    kalman.trendBuffer.push(trend);kalman.innovationBuffer.push(innovation);
    if(kalman.trendBuffer.length>NORM_WINDOW)kalman.trendBuffer.splice(0,kalman.trendBuffer.length-NORM_WINDOW);
    if(kalman.innovationBuffer.length>NORM_WINDOW)kalman.innovationBuffer.splice(0,kalman.innovationBuffer.length-NORM_WINDOW);
    const ready=kalman.trendBuffer.length>=NORM_MIN;
    const trendRms=rollingRms(kalman.trendBuffer,NORM_WINDOW),innovationRms=rollingRms(kalman.innovationBuffer,NORM_WINDOW);
    const slopeZ=(ready&&Number.isFinite(trendRms)&&trendRms>1e-15)?trend/trendRms:null;
    const innovationZ=(ready&&Number.isFinite(innovationRms)&&innovationRms>1e-15)?innovation/innovationRms:null;
    kalman.timestamps.push(timestamp);kalman.observed.push(price);kalman.filtered.push(level);kalman.slopeZ.push(slopeZ);kalman.innovationZ.push(innovationZ);
    for(const a of [kalman.timestamps,kalman.observed,kalman.filtered,kalman.slopeZ,kalman.innovationZ])if(a.length>5000)a.splice(0,a.length-5000);
    return{timestamp,price,level,trend,slopeZ,innovationZ,ready,warmup:kalman.trendBuffer.length,beta:null,zscore:null,hmm:null}
}

function gaussianLogPdf(value,mean,sd){const s=Math.max(sd,1e-6),d=(value-mean)/s;return-Math.log(s*Math.sqrt(2*Math.PI))-.5*d*d}
function normalizeLogs(logs){const m=Math.max(...logs),a=logs.map(v=>Math.exp(v-m)),t=a.reduce((s,v)=>s+v,0);return a.map(v=>v/t)}
function updateHmm(slopeZ,innovationZ){
    const p=Math.min(Math.max(HMM_PERSISTENCE,.5),.995),m=1-p;
    const tr=[[p,m*.4,m*.4,m*.2],[m*.43,p,m*.05,m*.52],[m*.43,m*.05,p,m*.52],[m*.55,m*.225,m*.225,p]],pred=[0,0,0,0];
    for(let d=0;d<4;d++)for(let o=0;o<4;o++)pred[d]+=hmm.posterior[o]*tr[o][d];
    /* ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â°missions recalibrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©es sur le slopeZ normalisÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© (sd ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â°Ãƒâ€¹Ã¢â‚¬Â  1). Les anciennes
       supposaient N(ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â±0.9, 0.72) alors que le slopeZ observÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© valait N(0, 0.25) :
       l'ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©tat NOISE gagnait toujours et `up` n'atteignait jamais le seuil. */
    const ai=Math.abs(innovationZ),em=[gaussianLogPdf(slopeZ,0,.70)+gaussianLogPdf(innovationZ,0,.9),gaussianLogPdf(slopeZ,1.35,.95)+gaussianLogPdf(innovationZ,.1,1.15),gaussianLogPdf(slopeZ,-1.35,.95)+gaussianLogPdf(innovationZ,-.1,1.15),gaussianLogPdf(slopeZ,0,2.2)+gaussianLogPdf(ai,2.8,1.2)];
    hmm.posterior=normalizeLogs(pred.map((q,i)=>Math.log(Math.max(q,1e-15))+em[i]));
    let dominant=0;for(let i=1;i<4;i++)if(hmm.posterior[i]>hmm.posterior[dominant])dominant=i;
    if(dominant===hmm.candidate)hmm.candidateCount++;else{hmm.candidate=dominant;hmm.candidateCount=1}
    const needed=dominant===3?1:CONFIRMATION;
    if(hmm.candidateCount>=needed){if(hmm.confirmedState===dominant)hmm.duration++;else{hmm.confirmedState=dominant;hmm.duration=1}}else hmm.duration++;
    return{posterior:[...hmm.posterior],dominant,confirmed:hmm.confirmedState,duration:hmm.duration}
}

/* x est centre sur sa moyenne de warm-up. Avec x = log(prix) ~ 8.5, intercept et
   pente sont quasi colineaires et la covariance initiale de beta ([[rv,0],[0,0.1]],
   soit sd(beta) = 0.32 sur un beta vrai de ~0.7) rend le gain aberrant. Une fois
   x centre, la covariance OLS exacte est diagonale : var(alpha)=rv/n, var(beta)=rv/Sxx. */
function initializeRegression(obs){
    const n=obs.length;if(n<20)return null;
    let sx=0,sy=0;for(const v of obs){sx+=v.x;sy+=v.y}
    const xBar=sx/n;
    let sxx=0,sxy=0;for(const v of obs){const xc=v.x-xBar;sxx+=xc*xc;sxy+=xc*v.y}
    if(!(sxx>1e-18))return null;
    const beta=sxy/sxx,alpha=sy/n,res=obs.map(v=>v.y-alpha-beta*(v.x-xBar)),rv=Math.max(variance(res),1e-14);
    return{state:[alpha,beta],covariance:[[rv/n,0],[0,rv/sxx]],residualVariance:rv,xBar}
}
function updateRegression(timestamp,y,x,priceY,priceX){
    if(regression.state===null){
        regression.warmup.push({y,x});
        if(regression.warmup.length<PAIR_WARMUP)return{ready:false,warmup:regression.warmup.length};
        const init=initializeRegression(regression.warmup);if(!init)return{ready:false,warmup:regression.warmup.length};
        regression.state=init.state;regression.covariance=init.covariance;regression.residualVariance=init.residualVariance;regression.xBar=init.xBar;
    }
    const xc=x-regression.xBar;
    const qm=10**((REACTIVITY-5)/2),rm=10**((6-OBSERVATION_TRUST)/2);
    /* Pour le RV, l'intercept EST le niveau d'equilibre du spread. Avec l'ancien
       qA = rv*5e-3, alpha avait une memoire de ~14 ticks : il ramenait le spread
       a zero en permanence, donc un spread ne pouvait jamais PARAITRE etire.
       Mesure sur paire cointegree simulee : corr(z, vrai spread) = 0.04 avant,
       0.55 en ralentissant alpha d'un facteur 5000. Le modele momentum regresse
       des rendements (alpha ~ 0), il garde donc le reglage d'origine. */
    const isRv=PAIR_MEAN_REVERSION_MODELS.has(SIGNAL_MODEL);
    const qA=regression.residualVariance*(isRv?1e-6:.005)*qm,qB=(isRv?regression.residualVariance*1e-8:1e-5)*qm,r=regression.residualVariance*Math.max(rm,1e-4);
    let [alpha,beta]=regression.state,[[p00,p01],[p10,p11]]=regression.covariance;p00+=qA;p11+=qB;
    const predicted=alpha+beta*xc,residual=y-predicted,s=p00+xc*p01+xc*p10+xc*xc*p11+r,k0=(p00+p01*xc)/s,k1=(p10+p11*xc)/s;
    alpha+=k0*residual;beta+=k1*residual;
    const np00=p00-k0*(p00+xc*p10),np01=p01-k0*(p01+xc*p11),np10=p10-k1*(p00+xc*p10),np11=p11-k1*(p01+xc*p11),off=(np01+np10)/2;
    regression.state=[alpha,beta];regression.covariance=[[Math.max(np00,1e-18),off],[off,Math.max(np11,1e-18)]];
    regression.residuals.push(residual);if(regression.residuals.length>5000)regression.residuals.shift();

    /* Chaque modÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¨le construit sa propre mesure : le RV lit un niveau de spread,
       le momentum lit une dÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©rive cumulÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e. Le rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©sidu brut ne sert ni ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  l'un ni
       ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  l'autre. */
    let zscore=null;
    if(isRv){
        // Avec l'intercept ralenti, le residuel a priori EST l'ecart a la relation
        // de long terme : c'est lui le spread, z-score sur Z_WINDOW.
        regression.spread.push(residual);if(regression.spread.length>5000)regression.spread.shift();
        zscore=rollingZ(regression.spread,Z_WINDOW);
    }else{
        /* Momentum rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©siduel = somme des rendements rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©siduels sur Z_WINDOW.
           StandardisÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e par son propre RMS roulant, comme la pente du Kalman :
           diviser par sd(residual)ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â·ÃƒÆ’Ã‚Â¢Ãƒâ€¹Ã¢â‚¬Â Ãƒâ€¦Ã‚Â¡W suppose des rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©sidus iid, or ils sont
           autocorrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©lÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â mesure : sd rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©el 0.48 au lieu de 1, donc le seuil 1.25
           se retrouvait ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  2.6 sd dans la queue. MÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªme dÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©faut que le bug 1. */
        regression.cumulativeResidual+=residual;
        regression.cumulativeSeries.push(regression.cumulativeResidual);
        if(regression.cumulativeSeries.length>5000)regression.cumulativeSeries.shift();
        const w=Math.max(10,Math.min(Z_WINDOW,regression.cumulativeSeries.length-1));
        if(regression.cumulativeSeries.length>w){
            const drift=regression.cumulativeResidual-regression.cumulativeSeries[regression.cumulativeSeries.length-1-w];
            regression.momentum.push(drift);
            if(regression.momentum.length>NORM_WINDOW)regression.momentum.splice(0,regression.momentum.length-NORM_WINDOW);
            if(regression.momentum.length>=NORM_MIN){
                const rms=rollingRms(regression.momentum,NORM_WINDOW);
                zscore=(Number.isFinite(rms)&&rms>1e-18)?drift/rms:0;
            }
        }
    }

    regression.timestamps.push(timestamp);regression.beta.push(beta);regression.zscore.push(zscore);
    if(regression.baseY===null){regression.baseY=priceY;regression.baseX=priceX}
    regression.normalizedY.push(priceY/regression.baseY*100);regression.normalizedX.push(priceX/regression.baseX*100);
    for(const a of [regression.timestamps,regression.beta,regression.zscore,regression.normalizedY,regression.normalizedX])if(a.length>5000)a.splice(0,a.length-5000);
    return{ready:true,alpha,beta,residual,zscore,level:null,slopeZ:null,innovationZ:null,hmm:null}
}

function flatSignal(label,reason,regime="NEUTRAL",confidence=0){return{target:0,label,reason,confidence,regime}}
function directionalState(current,measure,label,regimeUp="UP",regimeDown="DOWN"){
    if(!Number.isFinite(measure))return flatSignal("WARM-UP","Normalisation en cours","WARMUP");
    if(current>0)return measure<=EXIT_THRESHOLD?flatSignal("EXIT LONG",`${label} retombe ${signed(measure)}`,"NEUTRAL",1):{target:1,label:"HOLD LONG",reason:`${label} ${signed(measure)}`,confidence:Math.min(1,Math.abs(measure)/ENTRY_THRESHOLD),regime:regimeUp};
    if(current<0)return measure>=-EXIT_THRESHOLD?flatSignal("EXIT SHORT",`${label} remonte ${signed(measure)}`,"NEUTRAL",1):{target:-1,label:"HOLD SHORT",reason:`${label} ${signed(measure)}`,confidence:Math.min(1,Math.abs(measure)/ENTRY_THRESHOLD),regime:regimeDown};
    if(measure>=ENTRY_THRESHOLD)return{target:1,label:"LONG CANDIDATE",reason:`${label} ${signed(measure)}`,confidence:Math.min(1,measure/ENTRY_THRESHOLD),regime:regimeUp};
    if(ALLOW_SHORT&&measure<=-ENTRY_THRESHOLD)return{target:-1,label:"SHORT CANDIDATE",reason:`${label} ${signed(measure)}`,confidence:Math.min(1,Math.abs(measure)/ENTRY_THRESHOLD),regime:regimeDown};
    return flatSignal("WAIT",`${label} ${signed(measure)} sous seuil ${ENTRY_THRESHOLD.toFixed(2)}`)
}
function meanReversionState(current,measure,label){
    if(!Number.isFinite(measure))return flatSignal("WARM-UP","Normalisation en cours","WARMUP");
    if(current>0)return(Math.abs(measure)<=EXIT_THRESHOLD||measure>0)?flatSignal("EXIT LONG",`${label} revenu ${signed(measure)}`,"MEAN",1):{target:1,label:"HOLD LONG",reason:`${label} negatif ${signed(measure)}`,confidence:Math.min(1,Math.abs(measure)/ENTRY_THRESHOLD),regime:"CHEAP"};
    if(current<0)return(Math.abs(measure)<=EXIT_THRESHOLD||measure<0)?flatSignal("EXIT SHORT",`${label} revenu ${signed(measure)}`,"MEAN",1):{target:-1,label:"HOLD SHORT",reason:`${label} positif ${signed(measure)}`,confidence:Math.min(1,Math.abs(measure)/ENTRY_THRESHOLD),regime:"RICH"};
    if(measure<=-ENTRY_THRESHOLD)return{target:1,label:"LONG CANDIDATE",reason:`${label} trop bas ${signed(measure)}`,confidence:Math.min(1,Math.abs(measure)/ENTRY_THRESHOLD),regime:"CHEAP"};
    if(ALLOW_SHORT&&measure>=ENTRY_THRESHOLD)return{target:-1,label:"SHORT CANDIDATE",reason:`${label} trop haut ${signed(measure)}`,confidence:Math.min(1,measure/ENTRY_THRESHOLD),regime:"RICH"};
    return flatSignal("WAIT",`${label} ${signed(measure)} sous seuil ${ENTRY_THRESHOLD.toFixed(2)}`,"MEAN")
}
function strategySignal(features){
    const current=portfolio.position,slope=features.slopeZ,innovation=features.innovationZ,z=features.zscore;
    if(SIGNAL_MODEL==="single_trend"){
        if(Number.isFinite(innovation)&&Math.abs(innovation)>=SHOCK_THRESHOLD)return flatSignal("RISK OFF",`Innovation choc ${signed(innovation)}`,"CHOC",Math.min(1,Math.abs(innovation)/SHOCK_THRESHOLD));
        return directionalState(current,slope,"Pente")
    }
    if(SIGNAL_MODEL==="single_mean_reversion")return meanReversionState(current,innovation,"Innovation");
    if(SIGNAL_MODEL==="single_breakout"){
        if(!Number.isFinite(slope)||!Number.isFinite(innovation))return flatSignal("WARM-UP","Normalisation en cours","WARMUP");
        const impulse=(Math.abs(innovation)>=SECONDARY_THRESHOLD&&Math.sign(slope)===Math.sign(innovation))?slope:0;
        return directionalState(current,impulse,"Breakout")
    }
    if(SIGNAL_MODEL==="single_pullback"){
        if(!Number.isFinite(slope)||!Number.isFinite(innovation))return flatSignal("WARM-UP","Normalisation en cours","WARMUP");
        let score=0;
        if(slope>=ENTRY_THRESHOLD&&innovation<=-SECONDARY_THRESHOLD)score=slope;
        if(slope<=-ENTRY_THRESHOLD&&innovation>=SECONDARY_THRESHOLD)score=slope;
        if(current!==0)score=slope;
        return directionalState(current,score,"Pullback")
    }
    if(SIGNAL_MODEL==="single_shock_fade")return meanReversionState(current,innovation,"Shock");
    if(SIGNAL_MODEL==="single_vol_breakout"){
        if(!Number.isFinite(slope)||!Number.isFinite(innovation))return flatSignal("WARM-UP","Normalisation en cours","WARMUP");
        const score=(Math.abs(innovation)>=ENTRY_THRESHOLD&&Math.abs(slope)>=SECONDARY_THRESHOLD)?Math.sign(innovation)*Math.max(Math.abs(innovation),Math.abs(slope)):0;
        return directionalState(current,score,"Vol breakout")
    }
    if(SIGNAL_MODEL==="hmm_directional"||SIGNAL_MODEL==="hmm_risk_off"){
        if(!features.hmm)return flatSignal("WARM-UP","HMM en calibration","WARMUP");
        const p=features.hmm.posterior,noise=p[0],up=p[1],down=p[2],shock=p[3];
        const shockLimit=SIGNAL_MODEL==="hmm_risk_off"?SECONDARY_THRESHOLD:SECONDARY_THRESHOLD;
        if(shock>=shockLimit)return flatSignal("RISK OFF",`Choc ${(shock*100).toFixed(0)}%`,"CHOC",shock);
        if(SIGNAL_MODEL==="hmm_risk_off"&&noise>=ENTRY_THRESHOLD)return flatSignal("WAIT",`Noise ${(noise*100).toFixed(0)}%`,"BRUIT",noise);
        if(current>0){if(up<EXIT_THRESHOLD||noise>=ENTRY_THRESHOLD)return flatSignal("EXIT LONG",`Up ${(up*100).toFixed(0)}% / noise ${(noise*100).toFixed(0)}%`,"BRUIT",Math.max(noise,1-up));return{target:1,label:"HOLD LONG",reason:`Regime hausse ${(up*100).toFixed(0)}%`,confidence:up,regime:"UP"}}
        if(current<0){if(down<EXIT_THRESHOLD||noise>=ENTRY_THRESHOLD)return flatSignal("EXIT SHORT",`Down ${(down*100).toFixed(0)}% / noise ${(noise*100).toFixed(0)}%`,"BRUIT",Math.max(noise,1-down));return{target:-1,label:"HOLD SHORT",reason:`Regime baisse ${(down*100).toFixed(0)}%`,confidence:down,regime:"DOWN"}}
        if(up>=ENTRY_THRESHOLD)return{target:1,label:"LONG CANDIDATE",reason:`Regime hausse ${(up*100).toFixed(0)}%`,confidence:up,regime:"UP"};
        if(ALLOW_SHORT&&down>=ENTRY_THRESHOLD)return{target:-1,label:"SHORT CANDIDATE",reason:`Regime baisse ${(down*100).toFixed(0)}%`,confidence:down,regime:"DOWN"};
        return flatSignal("WAIT",`Noise ${(noise*100).toFixed(0)}% / up ${(up*100).toFixed(0)}% / down ${(down*100).toFixed(0)}%`,"BRUIT",noise)
    }
    if(!Number.isFinite(z))return flatSignal("WARM-UP","Z-score indisponible","WARMUP");
    if(SIGNAL_MODEL==="pair_mean_reversion"||SIGNAL_MODEL==="pair_convergence"||SIGNAL_MODEL==="pair_stat_arb"||SIGNAL_MODEL==="pair_residual_shock_fade")return meanReversionState(current,z,"Spread z");
    if(SIGNAL_MODEL==="pair_residual_momentum"||SIGNAL_MODEL==="pair_breakout"||SIGNAL_MODEL==="pair_dispersion_widen"||SIGNAL_MODEL==="pair_beta_trend")return directionalState(current,z,"Residuel z","RESIDUAL UP","RESIDUAL DOWN");
    return flatSignal("WAIT","Mode non reconnu")
}

function executablePrice(tick,side,tickSize){
    if(!tick)return null;
    const base=side>0?(Number.isFinite(tick.ask)?tick.ask:tick.price):(Number.isFinite(tick.bid)?tick.bid:tick.price);
    return Number.isFinite(base)?base+side*EXTRA_SLIPPAGE_TICKS*tickSize:null
}
function markPrice(tick,positionSide,tickSize){return executablePrice(tick,-positionSide,tickSize)}
/* Commission en bps du notionnel. Une commission par unitÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© donnait 92 592 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬
   d'entrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e sur EUR/USD (185 185 unitÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 0.50) contre 5 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ sur le Nasdaq :
   le mÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªme dÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©faut couvrait quatre ordres de grandeur. */
function notionalFor(quantityY,priceY,quantityX,priceX){
    let notional=Math.abs(quantityY)*Math.abs(finite(priceY,0))*POINT_VALUE_Y*FX_Y;
    if(IS_PAIR&&Number.isFinite(priceX))notional+=Math.abs(quantityX)*Math.abs(priceX)*POINT_VALUE_X*FX_X;
    return notional
}
function commissionForNotional(notional){
    if(!Number.isFinite(notional)||notional<=0)return MIN_COMMISSION;
    return Math.max(notional*COMMISSION_BPS/10000,MIN_COMMISSION)
}
function estimatedExitCommission(trade){
    const exitY=markPrice(market.Y,trade.direction,TICK_SIZE_Y),exitX=trade.isPair?markPrice(market.X,-trade.direction,TICK_SIZE_X):null;
    const py=Number.isFinite(exitY)?exitY:trade.entryY,px=Number.isFinite(exitX)?exitX:trade.entryX;
    return commissionForNotional(notionalFor(trade.quantityY,py,trade.quantityX,px))
}
function sizePosition(betaValue){
    if(!market.Y)return null;
    const grossTarget=ACCOUNT_EQUITY*TARGET_LEVERAGE;
    if(!IS_PAIR){
        const per=market.Y.price*POINT_VALUE_Y*FX_Y,qy=roundQuantity(grossTarget/Math.max(per,1e-12));
        return{quantityY:qy,quantityX:0,grossNotional:qy*per,leverage:qy*per/ACCOUNT_EQUITY}
    }
    if(!market.X)return null;
    const beta=Math.max(Math.abs(finite(betaValue,1)),.05),ny=market.Y.price*POINT_VALUE_Y*FX_Y,nx=market.X.price*POINT_VALUE_X*FX_X,xPerY=beta*ny/Math.max(nx,1e-12),grossPerY=ny+xPerY*nx,qy=roundQuantity(grossTarget/Math.max(grossPerY,1e-12)),qx=roundQuantity(qy*xPerY),gross=qy*ny+qx*nx;
    return{quantityY:qy,quantityX:qx,grossNotional:gross,leverage:gross/ACCOUNT_EQUITY}
}
function currentGrossPnl(trade){
    if(!trade)return 0;
    const exitY=markPrice(market.Y,trade.direction,TICK_SIZE_Y);if(!Number.isFinite(exitY))return 0;
    let pnl=trade.direction*(exitY-trade.entryY)*trade.quantityY*POINT_VALUE_Y*FX_Y;
    if(trade.isPair){const xd=-trade.direction,exitX=markPrice(market.X,xd,TICK_SIZE_X);if(Number.isFinite(exitX))pnl+=xd*(exitX-trade.entryX)*trade.quantityX*POINT_VALUE_X*FX_X}
    return pnl
}
function currentEquivalentTicks(trade){
    if(!trade)return 0;
    const tickValue=Math.max(TICK_SIZE_Y*POINT_VALUE_Y*FX_Y*trade.quantityY,1e-12);
    return currentGrossPnl(trade)/tickValue
}

function openPosition(direction,signal,timestamp,features){
    if(direction<0&&!ALLOW_SHORT)return;
    if(portfolio.locked)return;
    if(portfolio.trades.length>=MAX_TRADES){portfolio.locked=true;portfolio.active=false;logLine("KILL",`Nombre maximal de trades atteint (${MAX_TRADES}).`,timestamp);return}
    const sizing=sizePosition(finite(features.beta,1));
    if(!sizing||sizing.quantityY<=0||(IS_PAIR&&sizing.quantityX<=0)){logLine("RISK","Taille nulle. VÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©rifie point value, FX et capital.",timestamp);return}
    const entryY=executablePrice(market.Y,direction,TICK_SIZE_Y),entryX=IS_PAIR?executablePrice(market.X,-direction,TICK_SIZE_X):null;
    if(!Number.isFinite(entryY)||(IS_PAIR&&!Number.isFinite(entryX)))return;
    const entryNotional=notionalFor(sizing.quantityY,entryY,sizing.quantityX,entryX);
    const entryCommission=commissionForNotional(entryNotional);
    portfolio.realized-=entryCommission;portfolio.costs+=entryCommission;portfolio.position=direction;
    portfolio.trade={id:portfolio.trades.length+1,isPair:IS_PAIR,direction,openedAt:timestamp,entryY,entryX,quantityY:sizing.quantityY,quantityX:sizing.quantityX,beta:finite(features.beta,1),leverage:sizing.leverage,grossNotional:sizing.grossNotional,entryNotional,entryCommission,signal:signal.label,entryReason:signal.reason};
    portfolio.cooldown=0;
    logLine(direction>0?"BUY":"SHORT",`${IS_PAIR?"SPREAD ":""}${direction>0?"LONG":"SHORT"} | Y ${sizing.quantityY.toFixed(4)} @ ${formatPrice(entryY)}${IS_PAIR?` | X ${sizing.quantityX.toFixed(4)} @ ${formatPrice(entryX)}`:""} | levier ${sizing.leverage.toFixed(2)}ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â | frais ${formatMoney(-entryCommission)} | ${signal.reason}`,timestamp);
}

function closePosition(reason,timestamp,exitType="EXIT"){
    const trade=portfolio.trade;if(!trade)return;
    const exitY=executablePrice(market.Y,-trade.direction,TICK_SIZE_Y),exitX=trade.isPair?executablePrice(market.X,trade.direction,TICK_SIZE_X):null;
    if(!Number.isFinite(exitY)||(trade.isPair&&!Number.isFinite(exitX)))return;
    let gross=trade.direction*(exitY-trade.entryY)*trade.quantityY*POINT_VALUE_Y*FX_Y;
    if(trade.isPair){const xd=-trade.direction;gross+=xd*(exitX-trade.entryX)*trade.quantityX*POINT_VALUE_X*FX_X}
    const exitNotional=notionalFor(trade.quantityY,exitY,trade.quantityX,exitX);
    const exitCommission=commissionForNotional(exitNotional),totalCosts=trade.entryCommission+exitCommission,net=gross-totalCosts;
    portfolio.grossRealized+=gross;portfolio.realized+=gross-exitCommission;portfolio.costs+=exitCommission;
    const duration=Math.max(0,(timestamp-trade.openedAt)/1000),tickValue=Math.max(TICK_SIZE_Y*POINT_VALUE_Y*FX_Y*trade.quantityY,1e-12),tickEq=gross/tickValue;
    portfolio.totalTicks+=tickEq;
    portfolio.trades.push({trade_id:trade.id,strategy:STRATEGY,direction:trade.direction>0?(trade.isPair?"LONG_SPREAD":"LONG"):(trade.isPair?"SHORT_SPREAD":"SHORT"),opened_at:trade.openedAt.toISOString(),closed_at:timestamp.toISOString(),duration_seconds:duration,symbol_y:SYMBOL_Y,quantity_y:trade.quantityY,entry_y:trade.entryY,exit_y:exitY,symbol_x:trade.isPair?SYMBOL_X:"",quantity_x:trade.quantityX,entry_x:trade.isPair?trade.entryX:"",exit_x:trade.isPair?exitX:"",beta_entry:trade.beta,entry_notional:trade.entryNotional,exit_notional:exitNotional,gross_pnl:gross,commission_bps:COMMISSION_BPS,entry_commission:trade.entryCommission,exit_commission:exitCommission,total_costs:totalCosts,net_pnl:net,equivalent_y_ticks:tickEq,leverage:trade.leverage,entry_reason:trade.entryReason,exit_reason:reason});
    portfolio.position=0;portfolio.trade=null;portfolio.unrealized=0;portfolio.currentTicks=0;portfolio.cooldown=COOLDOWN_OBSERVATIONS;portfolio.candidateTarget=0;portfolio.candidateCount=0;
    logLine(net>=0?"PROFIT":"LOSS",`${exitType} | gross ${formatMoney(gross)} | coÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â»ts ${formatMoney(-totalCosts)} | net ${formatMoney(net)} | ${signed(tickEq,1)} ticks Y-eq | ${reason}`,timestamp);
    updateBlotter()
}

function applyTarget(signal,timestamp,features,isReplay){
    portfolio.lastSignalLabel=signal.label;portfolio.lastSignalReason=signal.reason;portfolio.currentTarget=signal.target;
    const marketOpen=marketOpenNow();
    if(!marketOpen){portfolio.candidateTarget=0;portfolio.candidateCount=0;logVerbose("WAIT",`${signal.label} | marche ferme`,timestamp);return}
    const eligible=portfolio.active&&!portfolio.locked&&(TRADE_REPLAY||!isReplay);
    if(!eligible){portfolio.candidateTarget=0;portfolio.candidateCount=0;logVerbose("WAIT",`${signal.label} | ${signal.reason} | session non active`,timestamp);return}
    if(portfolio.position!==0&&signal.target===0){closePosition(signal.reason,timestamp,"MODEL EXIT");return}
    if(portfolio.position!==0&&signal.target===portfolio.position){logVerbose("HOLD",`${signal.label} | ${signal.reason} | uPnL ${formatMoney(portfolio.unrealized)}`,timestamp);return}
    if(portfolio.position!==0&&signal.target===-portfolio.position){closePosition(`Signal opposÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© : ${signal.reason}`,timestamp,"REVERSAL EXIT");return}
    if(portfolio.cooldown>0){portfolio.cooldown--;logVerbose("WAIT",`Cooldown ${portfolio.cooldown} | ${signal.reason}`,timestamp);return}
    if(portfolio.position===0&&signal.target!==0){
        if(signal.target===portfolio.candidateTarget)portfolio.candidateCount++;else{portfolio.candidateTarget=signal.target;portfolio.candidateCount=1}
        if(portfolio.candidateCount>=CONFIRMATION){openPosition(signal.target,signal,timestamp,features);portfolio.candidateTarget=0;portfolio.candidateCount=0}
        else logVerbose("WAIT",`${signal.label} | confirmation ${portfolio.candidateCount}/${CONFIRMATION} | ${signal.reason}`,timestamp);
        return
    }
    portfolio.candidateTarget=0;portfolio.candidateCount=0;logVerbose("WAIT",`${signal.label} | ${signal.reason}`,timestamp)
}

function updateRisk(timestamp){
    if(portfolio.active&&!marketOpenNow()){
        if(portfolio.trade)closePosition(closedMarketReason(),timestamp,"MARKET CLOSE");
        portfolio.active=false;
        logLine("RISK",closedMarketReason(),timestamp);
    }
    if(portfolio.trade){
        const trade=portfolio.trade;
        const gross=currentGrossPnl(trade),exitCost=estimatedExitCommission(trade);
        portfolio.unrealized=gross-exitCost;portfolio.currentTicks=currentEquivalentTicks(trade);
        const tradeNet=gross-trade.entryCommission-exitCost;
        if(MAX_TRADE_LOSS>0&&tradeNet<=-MAX_TRADE_LOSS)closePosition(`Stop trade ${formatMoney(tradeNet)}`,timestamp,"STOP");
        else if(MAX_HOLDING_SECONDS>0&&(timestamp-trade.openedAt)/1000>=MAX_HOLDING_SECONDS)closePosition(`Time stop ${((timestamp-trade.openedAt)/1000).toFixed(0)}s`,timestamp,"TIME STOP");
    }else{portfolio.unrealized=0;portfolio.currentTicks=0}
    /* Le kill switch session ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©tait enfermÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© derriÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¨re `if(!portfolio.trade)return`,
       donc inatteignable ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  plat : une perte rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©alisÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e massive ne verrouillait
       jamais la session, qui rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©ouvrait jusqu'ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  MAX_TRADES. */
    if(portfolio.locked||MAX_SESSION_LOSS<=0)return;
    const net=portfolio.realized+portfolio.unrealized;
    if(net<=-MAX_SESSION_LOSS){
        if(portfolio.trade)closePosition(`Kill switch session ${formatMoney(net)}`,timestamp,"KILL");
        portfolio.locked=true;portfolio.active=false;
        logLine("KILL",`Session verrouillÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e aprÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¨s la perte maximale (${formatMoney(portfolio.realized+portfolio.unrealized)}). Utilise RESET.`,timestamp)
    }
}

function appendDecision(timestamp,features,signal,isReplay){
    const net=portfolio.realized+portfolio.unrealized;
    portfolio.decisions.push({timestamp:timestamp.toISOString(),replay:Boolean(isReplay),strategy:STRATEGY,price_y:market.Y?market.Y.price:null,bid_y:market.Y?market.Y.bid:null,ask_y:market.Y?market.Y.ask:null,price_x:market.X?market.X.price:null,bid_x:market.X?market.X.bid:null,ask_x:market.X?market.X.ask:null,kalman_level:finite(features.level),slope_z:finite(features.slopeZ),innovation_z:finite(features.innovationZ),beta:finite(features.beta),residual_z:finite(features.zscore),hmm_noise:features.hmm?features.hmm.posterior[0]:null,hmm_up:features.hmm?features.hmm.posterior[1]:null,hmm_down:features.hmm?features.hmm.posterior[2]:null,hmm_shock:features.hmm?features.hmm.posterior[3]:null,signal:signal.label,signal_reason:signal.reason,target_position:signal.target,actual_position:portfolio.position,realized_pnl:portfolio.realized,unrealized_pnl:portfolio.unrealized,net_pnl:net});
    if(portfolio.decisions.length>25000)portfolio.decisions.splice(0,portfolio.decisions.length-25000)
}

function processModelObservation(timestamp,features,isReplay){
    portfolio.observations++;
    const signal=strategySignal(features);
    updateRisk(timestamp);applyTarget(signal,timestamp,features,isReplay);updateRisk(timestamp);appendDecision(timestamp,features,signal,isReplay);
    const net=portfolio.realized+portfolio.unrealized;portfolio.peakNet=Math.max(portfolio.peakNet,net);portfolio.maxDrawdown=Math.max(portfolio.maxDrawdown,portfolio.peakNet-net);
    portfolio.equityTimestamps.push(timestamp);portfolio.equityNet.push(net);portfolio.equityRealized.push(portfolio.realized);
    for(const a of [portfolio.equityTimestamps,portfolio.equityNet,portfolio.equityRealized])if(a.length>5000)a.splice(0,a.length-5000);
    const fp=`${signal.label}|${signal.regime}|${portfolio.position}`;
    if(fp!==portfolio.lastStateFingerprint){const type=signal.target>0?"LONG":(signal.target<0?"SHORT":(signal.regime==="CHOC"?"SHOCK":"WAIT"));logLine(type,`${signal.label} | ${signal.reason} | position ${portfolio.position>0?"LONG":portfolio.position<0?"SHORT":"FLAT"}`,timestamp);portfolio.lastStateFingerprint=fp}
    renderAll(features,signal)
}

function processSingleTick(tick,isReplay){
    const features=updateKalman(tick.timestamp,tick.price);
    if(!features.ready){renderAll(features,{target:0,label:"WARM-UP",reason:`Calibration ${features.warmup}/${NORM_MIN} obs`,confidence:0,regime:"WARMUP"});return}
    if(HMM_MODELS.has(SIGNAL_MODEL))features.hmm=updateHmm(features.slopeZ,features.innovationZ);
    processModelObservation(tick.timestamp,features,isReplay)
}
function processPairPrices(timestamp,priceY,priceX,isReplay){
    if(market.previousY===null||market.previousX===null){market.previousY=priceY;market.previousX=priceX;return}
    let y,x;
    if(PAIR_INPUT==="returns"){y=Math.log(priceY/market.previousY);x=Math.log(priceX/market.previousX)}
    else{y=Math.log(priceY);x=Math.log(priceX)}
    market.previousY=priceY;market.previousX=priceX;
    if(!Number.isFinite(y)||!Number.isFinite(x))return;
    if(PAIR_INPUT==="returns"&&Math.abs(y)<1e-14&&Math.abs(x)<1e-14)return;
    const result=updateRegression(timestamp,y,x,priceY,priceX);
    if(!result.ready){DOM.connection.textContent=`PAIR WARM-UP ${result.warmup||0}/${PAIR_WARMUP}`;renderAll({beta:null,zscore:null},{target:0,label:"WARM-UP",reason:`RÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©gression ${result.warmup||0}/${PAIR_WARMUP}`,regime:"WARMUP"});return}
    processModelObservation(timestamp,result,isReplay)
}
function processPairTick(side,tick,isReplay){
    if(SYNC_MS===0){
        if(!market.Y||!market.X)return;
        const sig=`${market.Y.timestamp.getTime()}|${market.X.timestamp.getTime()}|${market.Y.price}|${market.X.price}`;
        if(sig===market.lastPairSignature)return;market.lastPairSignature=sig;
        processPairPrices(tick.timestamp,market.Y.price,market.X.price,isReplay);return
    }
    const bucket=Math.floor(tick.timestamp.getTime()/SYNC_MS)*SYNC_MS;
    if(market.bucket===null)market.bucket=bucket;
    if(bucket>market.bucket){
        if(Number.isFinite(market.bucketY)&&Number.isFinite(market.bucketX))processPairPrices(new Date(market.bucket),market.bucketY,market.bucketX,isReplay);
        market.bucket=bucket;market.bucketY=market.Y?market.Y.price:market.bucketY;market.bucketX=market.X?market.X.price:market.bucketX
    }
    if(side==="Y")market.bucketY=tick.price;else market.bucketX=tick.price
}

function updateBlotter(){
    DOM.blotterBody.innerHTML="";
    for(const trade of [...portfolio.trades].reverse().slice(0,250)){
        const row=document.createElement("tr"),values=[trade.trade_id,trade.direction,formatPrice(trade.entry_y),formatPrice(trade.exit_y),`${trade.duration_seconds.toFixed(1)}s`,formatMoney(trade.gross_pnl),formatMoney(-trade.total_costs),formatMoney(trade.net_pnl),trade.exit_reason];
        values.forEach((value,index)=>{const cell=document.createElement("td");cell.textContent=value;if(index===7&&trade.net_pnl!==0)cell.className=trade.net_pnl>0?"positive":"negative";row.appendChild(cell)});
        DOM.blotterBody.appendChild(row)
    }
}

function renderMetrics(features,signal){
    const net=portfolio.realized+portfolio.unrealized,bps=net/ACCOUNT_EQUITY*10000,wins=portfolio.trades.filter(t=>t.net_pnl>0).length,losses=portfolio.trades.filter(t=>t.net_pnl<0).length,winRate=portfolio.trades.length?wins/portfolio.trades.length*100:null,grossWins=portfolio.trades.filter(t=>t.net_pnl>0).reduce((s,t)=>s+t.net_pnl,0),grossLosses=Math.abs(portfolio.trades.filter(t=>t.net_pnl<0).reduce((s,t)=>s+t.net_pnl,0)),pf=grossLosses>0?grossWins/grossLosses:(grossWins>0?Infinity:null);
    DOM.sessionMetric.textContent=portfolio.locked?"LOCKED":(portfolio.active?"ACTIVE":"IDLE");DOM.sessionMetric.style.color=portfolio.locked?COLORS.red:(portfolio.active?COLORS.green:COLORS.muted);DOM.sessionSub.textContent=!marketOpenNow()?"Market closed":(TRADE_REPLAY?"Replay + live":(market.liveSeen?"Live":"Replay warm-up"));
    DOM.signalMetric.textContent=signal.label;DOM.signalMetric.style.color=signal.target>0?COLORS.green:(signal.target<0?COLORS.red:(signal.regime==="CHOC"?COLORS.yellow:COLORS.text));DOM.signalSub.textContent=signal.reason;
    const pLabel=portfolio.position>0?(IS_PAIR?"LONG SPREAD":"LONG"):(portfolio.position<0?(IS_PAIR?"SHORT SPREAD":"SHORT"):"FLAT");
    DOM.positionMetric.textContent=pLabel;DOM.positionMetric.style.color=portfolio.position>0?COLORS.green:(portfolio.position<0?COLORS.red:COLORS.muted);DOM.positionSub.textContent=portfolio.trade?`Y ${portfolio.trade.quantityY.toFixed(4)}${IS_PAIR?` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· X ${portfolio.trade.quantityX.toFixed(4)}`:""}`:"0 unitÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©";
    DOM.netMetric.textContent=formatMoney(net);DOM.netMetric.style.color=net>0?COLORS.green:(net<0?COLORS.red:COLORS.text);DOM.netSub.textContent=`${signed(bps,2)} bps sur capital`;
    DOM.unrealizedMetric.textContent=formatMoney(portfolio.unrealized);DOM.unrealizedMetric.style.color=portfolio.unrealized>0?COLORS.green:(portfolio.unrealized<0?COLORS.red:COLORS.text);DOM.unrealizedSub.textContent=portfolio.trade?`EntrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e ${formatPrice(portfolio.trade.entryY)}`:"Flat";
    const totalTicks=portfolio.totalTicks+portfolio.currentTicks;DOM.ticksMetric.textContent=signed(totalTicks,1);DOM.ticksMetric.style.color=totalTicks>0?COLORS.green:(totalTicks<0?COLORS.red:COLORS.text);DOM.ticksSub.textContent=`RÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©alisÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s ${signed(portfolio.totalTicks,1)}`;
    DOM.tradesMetric.textContent=`${portfolio.trades.length} / ${winRate===null?"ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â":`${winRate.toFixed(1)}%`}`;DOM.tradesSub.textContent=`PF ${pf===Infinity?"ÃƒÆ’Ã‚Â¢Ãƒâ€¹Ã¢â‚¬Â Ãƒâ€¦Ã‚Â¾":pf===null?"ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â":pf.toFixed(2)} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· W ${wins} / L ${losses}`;
    DOM.drawdownMetric.textContent=formatMoney(-portfolio.maxDrawdown);DOM.drawdownMetric.style.color=portfolio.maxDrawdown>0?COLORS.red:COLORS.text;DOM.drawdownSub.textContent=`CoÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â»ts ${formatMoney(-portfolio.costs)}`;
    DOM.diagPriceY.textContent=market.Y?`${formatPrice(market.Y.price)}${Number.isFinite(market.Y.bid)&&Number.isFinite(market.Y.ask)?` [${formatPrice(market.Y.bid)} / ${formatPrice(market.Y.ask)}]`:""}`:"ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â";
    DOM.diagPriceX.textContent=market.X?`${formatPrice(market.X.price)}${Number.isFinite(market.X.bid)&&Number.isFinite(market.X.ask)?` [${formatPrice(market.X.bid)} / ${formatPrice(market.X.ask)}]`:""}`:"N/A";
    // Le seuil est affichÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  cÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â´tÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© de la mesure : on voit tout de suite si le
    // modÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¨le attend parce qu'il est loin du seuil ou parce qu'il vient de rater.
    DOM.diagPrimary.textContent=Number.isFinite(features.beta)?`ÃƒÆ’Ã…Â½Ãƒâ€šÃ‚Â² ${features.beta.toFixed(4)}`:(Number.isFinite(features.slopeZ)?`${signed(features.slopeZ,2)}ÃƒÆ’Ã‚ÂÃƒâ€ Ã¢â‚¬â„¢ / ${ENTRY_THRESHOLD.toFixed(2)}`:"ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â");
    DOM.diagSecondary.textContent=Number.isFinite(features.zscore)?`z ${signed(features.zscore,2)} / ${ENTRY_THRESHOLD.toFixed(2)}`:(Number.isFinite(features.innovationZ)?`${signed(features.innovationZ,2)}ÃƒÆ’Ã‚ÂÃƒâ€ Ã¢â‚¬â„¢ / ${SHOCK_THRESHOLD.toFixed(2)}`:"ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â");
    if(features.hmm){const labels=["NOISE","UP","DOWN","SHOCK"];let d=0;for(let i=1;i<4;i++)if(features.hmm.posterior[i]>features.hmm.posterior[d])d=i;DOM.diagRegime.textContent=`${labels[d]} ${(features.hmm.posterior[d]*100).toFixed(0)}%`}else DOM.diagRegime.textContent=signal.regime;
    DOM.diagLeverage.textContent=portfolio.trade?`${portfolio.trade.leverage.toFixed(2)}ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â`:"0.00ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â";
    DOM.sessionSummary.textContent=`OBS ${portfolio.observations} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· REALIZED ${formatMoney(portfolio.realized)} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· GROSS ${formatMoney(portfolio.grossRealized)} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· PAPER ONLY`
}

function renderModelChart(){
    let traces,layout;
    if(!IS_PAIR){
        traces=[{x:kalman.timestamps,y:kalman.observed,type:"scattergl",mode:"markers",name:"Ticks",marker:{size:3,color:COLORS.raw,opacity:.55}},{x:kalman.timestamps,y:kalman.filtered,type:"scattergl",mode:"lines",name:"Prix latent Kalman",line:{color:COLORS.blue,width:2.2}}];
        if(HAS_X&&comparison.timestamps.length){
            traces.push({x:comparison.timestamps,y:comparison.normalizedY,type:"scattergl",mode:"lines",name:`${ASSET_Y} base 100`,yaxis:"y2",line:{color:COLORS.green,width:1.3,dash:"dot"}});
            traces.push({x:comparison.timestamps,y:comparison.normalizedX,type:"scattergl",mode:"lines",name:`${ASSET_X} base 100`,yaxis:"y2",line:{color:COLORS.purple,width:1.5}});
        }
        if(portfolio.trade&&Number.isFinite(portfolio.trade.entryY))traces.push({x:[portfolio.trade.openedAt,kalman.timestamps[kalman.timestamps.length-1]],y:[portfolio.trade.entryY,portfolio.trade.entryY],type:"scatter",mode:"lines",name:"Prix dÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢entrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e",line:{color:portfolio.trade.direction>0?COLORS.green:COLORS.red,width:1.2,dash:"dot"}});
        layout=commonLayout(`${ASSET_Y} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Kalman${HAS_X?` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· comparaison ${ASSET_X}`:""}`,`shadow-single-${SYMBOL_Y}-${SYMBOL_X||"none"}`);
        if(HAS_X&&comparison.timestamps.length)layout.yaxis2={title:"base 100",overlaying:"y",side:"left",gridcolor:"rgba(0,0,0,0)",zeroline:false,automargin:true};
    }else{
        const zName=PAIR_MEAN_REVERSION_MODELS.has(SIGNAL_MODEL)?"Spread z":"Residuel z";
        traces=[{x:regression.timestamps,y:regression.normalizedY,type:"scattergl",mode:"lines",name:`${ASSET_Y} base 100`,line:{color:COLORS.blue,width:2}},{x:regression.timestamps,y:regression.normalizedX,type:"scattergl",mode:"lines",name:`${ASSET_X} base 100`,line:{color:COLORS.purple,width:2}},{x:regression.timestamps,y:regression.zscore,type:"scattergl",mode:"lines",name:zName,yaxis:"y2",line:{color:COLORS.raw,width:1.5}}];
        layout=commonLayout(`${ASSET_Y} / ${ASSET_X} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Pair model`,`shadow-pair-${SYMBOL_Y}-${SYMBOL_X}`);layout.yaxis2={title:"z-score",overlaying:"y",side:"left",gridcolor:"rgba(0,0,0,0)",zeroline:true,zerolinecolor:COLORS.muted,range:[-4,4]};layout.shapes=[-ENTRY_THRESHOLD,0,ENTRY_THRESHOLD].map(level=>({type:"line",xref:"paper",x0:0,x1:1,yref:"y2",y0:level,y1:level,line:{color:level===0?COLORS.muted:COLORS.yellow,width:.8,dash:"dot"},opacity:.55}))
    }
    Plotly.react("modelChart",traces,layout,plotConfig)
}
function renderEquityChart(){
    const layout=commonLayout(`Session P&L ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${ACCOUNT_CURRENCY}`,"shadow-equity");layout.yaxis.ticksuffix=` ${ACCOUNT_CURRENCY}`;layout.shapes=[{type:"line",xref:"paper",x0:0,x1:1,y0:0,y1:0,line:{color:COLORS.muted,width:1}}];
    Plotly.react("equityChart",[{x:portfolio.equityTimestamps,y:portfolio.equityNet,type:"scattergl",mode:"lines",name:"Net liquidation P&L",fill:"tozeroy",fillcolor:"rgba(40,182,159,0.08)",line:{color:COLORS.green,width:2}},{x:portfolio.equityTimestamps,y:portfolio.equityRealized,type:"scattergl",mode:"lines",name:"RÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©alisÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© net",line:{color:COLORS.blue,width:1.5,dash:"dot"}}],layout,plotConfig)
}
/* Les mÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©triques suivent le rAF, les charts sont limitÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©s ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  ~7 Hz : un Plotly.react
   sur 5 000 points ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  chaque tick fige l'onglet dÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¨s que le flux accÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©lÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¨re. */
let metricsQueued=false,chartTimer=null,lastChartRender=0,lastFeatures={},lastSignal={target:0,label:"WAIT",reason:"Warm-up",regime:"WARMUP"};
function renderCharts(){lastChartRender=performance.now();chartTimer=null;renderModelChart();renderEquityChart()}
function scheduleCharts(){if(chartTimer!==null)return;const wait=Math.max(0,CHART_MIN_INTERVAL_MS-(performance.now()-lastChartRender));chartTimer=setTimeout(renderCharts,wait)}
function renderAll(features=lastFeatures,signal=lastSignal){
    lastFeatures=features;lastSignal=signal;
    if(!metricsQueued){metricsQueued=true;requestAnimationFrame(()=>{metricsQueued=false;renderMetrics(lastFeatures,lastSignal)})}
    scheduleCharts()
}

function startSession(){
    if(portfolio.locked){logLine("RISK","Session verrouillÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e. Utilise RESET.");return}
    if(portfolio.active){logLine("SYSTEM","La session est dÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©jÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  active.");return}
    if(!marketOpenNow()){DOM.connection.textContent="MARKET CLOSED";logLine("RISK",closedMarketReason());renderAll();return}
    portfolio.active=true;portfolio.startedAt=new Date();portfolio.stoppedAt=null;
    logLine("SYSTEM",`SESSION START | capital ${formatMoney(ACCOUNT_EQUITY)} | levier cible ${TARGET_LEVERAGE.toFixed(2)}ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â | commission ${COMMISSION_BPS} bps/cÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â´tÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© | ${STRATEGY}`);renderAll()
}
function stopSession(){
    const t=new Date();if(portfolio.trade)closePosition("ArrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªt manuel de la session",t,"SESSION CLOSE");portfolio.active=false;portfolio.stoppedAt=t;
    logLine("SYSTEM",`SESSION STOP | net ${formatMoney(portfolio.realized)} | trades ${portfolio.trades.length} | ticks ${signed(portfolio.totalTicks,1)}`,t);renderAll()
}
function resetSession(){if(portfolio.trade)closePosition("Reset demandÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©",new Date(),"RESET CLOSE");resetPortfolioState();renderAll()}
function sessionSummaryRows(){
    const net=portfolio.realized+portfolio.unrealized,wins=portfolio.trades.filter(t=>t.net_pnl>0).length,losses=portfolio.trades.filter(t=>t.net_pnl<0).length;
    return[{generated_at:nowIso(),strategy:STRATEGY,symbol_y:SYMBOL_Y,symbol_x:SYMBOL_X||"",account_currency:ACCOUNT_CURRENCY,account_equity:ACCOUNT_EQUITY,target_leverage:TARGET_LEVERAGE,session_started_at:portfolio.startedAt?portfolio.startedAt.toISOString():"",session_stopped_at:portfolio.stoppedAt?portfolio.stoppedAt.toISOString():"",observations:portfolio.observations,trades:portfolio.trades.length,winning_trades:wins,losing_trades:losses,realized_pnl:portfolio.realized,unrealized_pnl:portfolio.unrealized,net_liquidation_pnl:net,session_bps:net/ACCOUNT_EQUITY*10000,gross_realized_pnl:portfolio.grossRealized,total_costs:portfolio.costs,commission_bps:COMMISSION_BPS,min_commission:MIN_COMMISSION,norm_window:NORM_WINDOW,entry_threshold:ENTRY_THRESHOLD,exit_threshold:EXIT_THRESHOLD,equivalent_y_ticks:portfolio.totalTicks+portfolio.currentTicks,max_drawdown:portfolio.maxDrawdown,point_value_y:POINT_VALUE_Y,tick_size_y:TICK_SIZE_Y,point_value_x:POINT_VALUE_X,tick_size_x:TICK_SIZE_X,trade_replay:TRADE_REPLAY}]
}

function resizeCharts(){for(const id of ["modelChart","equityChart"]){const el=$(id);if(el&&el.clientWidth>0&&el.clientHeight>0){try{Plotly.Plots.resize(el)}catch(error){}}}}
function setView(view){
    DOM.workspace.dataset.view=view;
    document.querySelectorAll("button.view").forEach(b=>b.classList.toggle("active",b.dataset.view===view));
    requestAnimationFrame(resizeCharts);
}
$("viewGroup").addEventListener("click",event=>{const b=event.target.closest("button.view");if(b)setView(b.dataset.view)});

DOM.startButton.addEventListener("click",startSession);DOM.stopButton.addEventListener("click",stopSession);DOM.resetButton.addEventListener("click",resetSession);
DOM.fullscreenButton.addEventListener("click",async()=>{try{if(!document.fullscreenElement)await document.documentElement.requestFullscreen();else await document.exitFullscreen()}catch(error){logLine("SYSTEM",`Fullscreen indisponible depuis lÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢iframe (${error.message}). Utilise les vues COCKPIT / CHARTS / TERMINAL / BLOTTER.`)}});
DOM.exportTradesButton.addEventListener("click",()=>downloadCsv("shadow_trader_trades.csv",portfolio.trades));
DOM.exportDecisionsButton.addEventListener("click",()=>downloadCsv("shadow_trader_decisions.csv",portfolio.decisions));
DOM.exportSummaryButton.addEventListener("click",()=>downloadCsv("shadow_trader_summary.csv",sessionSummaryRows()));

let socket=null,reconnectTimer=null;
function handleTick(message){
    const side=canonicalSymbol(message.symbol);if(!side)return;
    const timestamp=parseTimestamp(message.timestamp??message.ts),price=finite(message.price);if(!Number.isFinite(price)||Number.isNaN(timestamp.getTime()))return;
    const tick={timestamp,price,bid:finite(message.bid),ask:finite(message.ask),volume:finite(message.volume),replay:Boolean(message.replay)};
    market[side]=tick;if(!tick.replay)market.liveSeen=true;
    updateComparison(timestamp);
    DOM.connection.textContent=`${tick.replay?"REPLAY":"LIVE"} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${timestamp.toLocaleTimeString([],{hour12:false})} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Y ${market.Y?formatPrice(market.Y.price):"ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â"}${HAS_X?` ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· X ${market.X?formatPrice(market.X.price):"ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â"}`:""}`;
    if(IS_PAIR)processPairTick(side,tick,tick.replay);
    else if(side==="Y")processSingleTick(tick,tick.replay);
    else renderAll()
}
function connect(){
    clearTimeout(reconnectTimer);DOM.connection.textContent="CONNECTING TO LSE WEBSOCKETÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦";socket=new WebSocket("wss://data-ws.londonstrategicedge.com");
    socket.onmessage=event=>{
        const message=JSON.parse(event.data);
        if(message.type==="welcome"){socket.send(JSON.stringify({action:"auth",api_key:API_KEY}));return}
        if(message.type==="authenticated"){
            const start=(Date.now()-REPLAY_MINUTES*60000)/1000,symbols=[SYMBOL_Y];
            if(HAS_X)symbols.push(SYMBOL_X);
            for(const symbol of symbols)socket.send(JSON.stringify({action:"subscribe",symbol,start}));
            DOM.connection.textContent=`AUTHENTICATED ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· REPLAY ${REPLAY_MINUTES} MIN`;logLine("SYSTEM",`LSE connectÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© | replay ${REPLAY_MINUTES} min | ${TRADE_REPLAY?"replay tradÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©":"replay warm-up uniquement"}`);return
        }
        if(message.type==="replay_started"){DOM.connection.textContent="REPLAY WARM-UPÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦";return}
        if(message.type==="replay_complete"){DOM.connection.textContent="REPLAY COMPLETE ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· WAITING LIVE";return}
        if(message.type==="tick"){handleTick(message);return}
        if(message.type==="error"){const e=message.message||message.code||"Unknown error";DOM.connection.textContent=`ERROR ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${e}`;logLine("RISK",`Erreur LSE : ${e}`)}
    };
    socket.onerror=()=>{DOM.connection.textContent="WEBSOCKET ERROR";logLine("RISK","Erreur de connexion WebSocket.")};
    socket.onclose=()=>{DOM.connection.textContent="DISCONNECTED ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· RECONNECTINGÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦";logLine("SYSTEM","Connexion perdue. Reconnexion dans 2.5 secondes.");reconnectTimer=setTimeout(connect,2500)}
}
window.addEventListener("beforeunload",()=>{if(socket)socket.close()});
if(typeof ResizeObserver!=="undefined"){const ro=new ResizeObserver(()=>resizeCharts());ro.observe($("modelChart"));ro.observe($("equityChart"))}
window.addEventListener("resize",resizeCharts);

resetPortfolioState();
Plotly.newPlot("modelChart",[],commonLayout("Waiting for model observationsÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦","shadow-model-empty"),plotConfig);
Plotly.newPlot("equityChart",[],commonLayout(`Session P&L ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${ACCOUNT_CURRENCY}`,"shadow-equity-empty"),plotConfig);
requestAnimationFrame(resizeCharts);
logLine("SYSTEM",`Normalisation sur ${NORM_WINDOW} obs (min ${NORM_MIN}) ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· seuil entrÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e ${ENTRY_THRESHOLD} ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· commission ${COMMISSION_BPS} bps/cÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â´tÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©.`);
logLine("SYSTEM",TRADE_REPLAY?"AUTO START ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· le replay sera inclus dans le paper P&L.":"Le replay initialise le modÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¨le. Clique START SESSION pour commencer le P&L live.");
connect();
</script>
</body>
</html>
"""

html = html_template.replace(
    "__SETTINGS__",
    json.dumps(live_settings),
)

components.html(
    html,
    height=int(live_settings["cockpitHeight"]),
    scrolling=False,
)

st.caption(
    "ExÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©cution paper au bid/ask lorsquÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ils sont fournis, sinon au dernier prix "
    "avec slippage. Adapte la valeur du point, le tick size et la conversion FX "
    "au produit rÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©ellement tradable que tu souhaites simuler."
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

elif selected_page == "Kalman Lab":
    execute_embedded_page(
        KALMAN_LAB_SOURCE,
        "flavio_monitor_kalman_lab",
        "embedded_kalman_lab.py",
    )

else:
    execute_embedded_page(
        PAPER_TRADING_SOURCE,
        "flavio_monitor_shadow_trader",
        "embedded_shadow_trader.py",
    )
