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
        @import url('https://fonts.googleapis.com/css2?family=Questrial&display=swap');

        html, body, .stApp, [class*="st-"],
        button, input, textarea, select, h1, h2, h3, h4, h5, h6, p, div {
            font-family: "Century Gothic", "Questrial", "URW Gothic",
                "Avenir", "Futura", sans-serif;
        }

        [data-testid="stSidebarNav"] {
            display: none;
        }

        .unified-navigation-title {
            color: #0a0a0a;
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
            background: #e6e8eb;
            margin: 0.25rem 0 0.8rem 0;
        }

        section[data-testid="stSidebar"] .stButton {
            margin-bottom: 0.05rem;
        }
        section[data-testid="stSidebar"] .stButton > button {
            width: 100%;
            justify-content: flex-start !important;
            background: transparent !important;
            border: none !important;
            border-left: 2px solid transparent !important;
            border-radius: 0 !important;
            color: #9aa0a6 !important;
            font-weight: 500;
            font-size: 0.95rem;
            padding: 0.3rem 0.2rem 0.3rem 0.7rem !important;
            min-height: 0 !important;
            box-shadow: none !important;
            transition: color 0.12s ease, background 0.12s ease;
        }
        section[data-testid="stSidebar"] .stButton > button p {
            text-align: left !important;
            margin: 0 !important;
        }
        section[data-testid="stSidebar"] .stButton > button:hover {
            background: #f4f5f6 !important;
            color: #0a0a0a !important;
        }
        section[data-testid="stSidebar"] .stButton > button:focus:not(:active) {
            color: #9aa0a6 !important;
        }
        section[data-testid="stSidebar"] .stButton > button[kind="primary"],
        section[data-testid="stSidebar"] .stButton > button[kind="primary"]:focus {
            background: transparent !important;
            color: #0a0a0a !important;
            font-weight: 700 !important;
            border-left: 2px solid #0a0a0a !important;
        }
        section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
            background: #f4f5f6 !important;
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
        'Data online · Morning desk'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="unified-divider"></div>',
        unsafe_allow_html=True,
    )

    for nav_page in ("Data Online", "Bureau Larbou"):
        is_active = (
            st.session_state.get("flavio_nav", "Data Online") == nav_page
        )
        if st.button(
            nav_page,
            key=f"flavio_nav_btn_{nav_page}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state["flavio_nav"] = nav_page
            st.rerun()

    selected_page = st.session_state.get("flavio_nav", "Data Online")

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


DATA_ONLINE_SOURCE = r'''
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import yfinance as yf


# =============================================================================
# CONFIGURATION
# =============================================================================

SECTIONS = [
    ("Europe", [
        ("Euro Stoxx 50", "^STOXX50E"),
        ("CAC 40", "^FCHI"),
        ("DAX", "^GDAXI"),
    ]),
    ("US", [
        ("Nasdaq 100", "^NDX"),
        ("S&P 500", "^GSPC"),
    ]),
    ("Monde", [
        ("Nikkei 225", "^N225"),
        ("Hang Seng", "^HSI"),
    ]),
    ("Or & Pétrole", [
        ("Or (Gold)", "GC=F"),
        ("Brent", "BZ=F"),
    ]),
]

ALL_TICKERS = [ticker for _, rows in SECTIONS for _, ticker in rows]

PERIODS = [
    ("3 jours", 3),
    ("1 semaine", 5),
    ("1 mois", 21),
]


# =============================================================================
# DONNEES
# =============================================================================

@st.cache_data(ttl=600, show_spinner=False)
def load_closes(tickers):
    frame = yf.download(
        tickers,
        period="3mo",
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="ticker",
    )

    closes = {}
    for ticker in tickers:
        series = pd.Series(dtype="float64")
        try:
            if len(tickers) == 1:
                series = frame["Close"]
            else:
                series = frame[ticker]["Close"]
        except Exception:
            series = pd.Series(dtype="float64")
        closes[ticker] = series.dropna()
    return closes


def compute_perf(series, lookback):
    if series is None or len(series) <= lookback:
        return None
    last = float(series.iloc[-1])
    prev = float(series.iloc[-(lookback + 1)])
    if prev == 0:
        return None
    return last / prev - 1.0


def last_price(series):
    if series is None or len(series) == 0:
        return None
    return float(series.iloc[-1])


# =============================================================================
# FORMATAGE
# =============================================================================

def fmt_price(value):
    if value is None:
        return "&mdash;"
    return f"{value:,.2f}".replace(",", " ")


def fmt_pct(value):
    if value is None:
        return "<span class='do-muted'>&mdash;</span>"
    if value > 0:
        css = "do-up"
        sign = "+"
    elif value < 0:
        css = "do-down"
        sign = ""
    else:
        css = "do-flat"
        sign = ""
    return f"<span class='{css}'>{sign}{value * 100:.2f}%</span>"


# =============================================================================
# STYLE
# =============================================================================

STYLE = """
<style>
    .stApp { background: #ffffff; }
    .block-container { padding-top: 2.4rem; max-width: 940px; }
    #MainMenu, header, footer { visibility: hidden; }

    .do-title {
        font-size: 1.9rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #0a0a0a;
        margin: 0;
    }
    .do-sub {
        font-size: 0.82rem;
        color: #8a8f98;
        margin: 0.15rem 0 0 0;
    }
    .do-section-title {
        font-size: 0.74rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: #6b7078;
        margin: 2.1rem 0 0.4rem 0;
    }
    table.do {
        width: 100%;
        border-collapse: collapse;
    }
    table.do th {
        font-size: 0.68rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #9aa0a6;
        padding: 0.35rem 0.6rem;
        text-align: right;
        border-bottom: 1px solid #e6e8eb;
    }
    table.do th.do-name, table.do td.do-name {
        text-align: left;
    }
    table.do td {
        padding: 0.7rem 0.6rem;
        border-bottom: 1px solid #f1f2f4;
        font-size: 0.95rem;
        color: #0a0a0a;
        text-align: right;
        font-variant-numeric: tabular-nums;
    }
    table.do td.do-name {
        font-weight: 600;
    }
    .do-up { color: #0a8f3c; font-weight: 600; }
    .do-down { color: #d32f2f; font-weight: 600; }
    .do-flat, .do-muted { color: #9aa0a6; }
</style>
"""


def render_section(name, rows, closes):
    head = "".join(f"<th>{label}</th>" for label, _ in PERIODS)
    body = []
    for display_name, ticker in rows:
        series = closes.get(ticker)
        price_cell = fmt_price(last_price(series))
        perf_cells = "".join(
            f"<td>{fmt_pct(compute_perf(series, lookback))}</td>"
            for _, lookback in PERIODS
        )
        body.append(
            f"<tr><td class='do-name'>{display_name}</td>"
            f"<td>{price_cell}</td>{perf_cells}</tr>"
        )
    rows_html = "".join(body)
    return (
        f"<div class='do-section-title'>{name}</div>"
        "<table class='do'><thead><tr>"
        "<th class='do-name'>Indice</th><th>Dernier</th>"
        f"{head}</tr></thead><tbody>{rows_html}</tbody></table>"
    )


# =============================================================================
# PAGE
# =============================================================================

st.markdown(STYLE, unsafe_allow_html=True)

closes = load_closes(ALL_TICKERS)

now_paris = datetime.now(ZoneInfo("Europe/Paris"))
stamp = now_paris.strftime("%H:%M")

header_left, header_right = st.columns([4, 1])
with header_left:
    st.markdown(
        "<div class='do-title'>Data Online</div>"
        f"<div class='do-sub'>Mis à jour à {stamp} (Paris)</div>",
        unsafe_allow_html=True,
    )
with header_right:
    if st.button("Rafraîchir", use_container_width=True):
        load_closes.clear()
        st.rerun()

html_sections = "".join(
    render_section(name, rows, closes) for name, rows in SECTIONS
)
st.markdown(html_sections, unsafe_allow_html=True)

st.caption(
    "Perf calculée sur les cours de clôture ajustés. "
    "3 jours / 1 semaine / 1 mois = 3 / 5 / 21 jours de bourse. "
    "Données différées."
)
'''

BUREAU_LARBOU_SOURCE = r'''
from __future__ import annotations

from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlencode
import json
import os
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

        div[data-testid="stPopover"] > button {
            border-color: #3b82f6;
            color: #dbeafe;
            background: rgba(37, 99, 235, 0.14);
        }

        .bureau-ai-chip {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 7px 10px;
            border: 1px solid #273142;
            border-radius: 8px;
            background: #101620;
            color: #d1d4dc;
            font-size: 0.82rem;
            margin-bottom: 0.45rem;
        }

        .bureau-ai-panel-title {
            color: #f4f7fb;
            font-size: 1rem;
            font-weight: 720;
            margin-bottom: 0.1rem;
        }

        .bureau-ai-panel-hint {
            color: #8490a3;
            font-size: 0.78rem;
            line-height: 1.35;
            margin-bottom: 0.7rem;
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

bureau_ai_slot = st.empty()


# =============================================================================
# HELPERS
# =============================================================================

INDEX_SYMBOLS = {
    "CAC 40": "^FCHI",
    "DAX": "^GDAXI",
    "Euro Stoxx 50": "^STOXX50E",
    "FTSE 100": "^FTSE",
    "S&P 500": "^GSPC",
    "Nasdaq 100": "^NDX",
    "Dow Jones": "^DJI",
    "Russell 2000": "^RUT",
    "Nikkei 225": "^N225",
}

COMMODITY_SYMBOLS = {
    "Énergie": {
        "WTI crude": "CL=F",
        "Brent": "BZ=F",
        "Gaz naturel": "NG=F",
        "Essence RBOB": "RB=F",
        "Heating oil": "HO=F",
    },
    "Métaux": {
        "Or": "GC=F",
        "Argent": "SI=F",
        "Cuivre": "HG=F",
        "Platine": "PL=F",
        "Palladium": "PA=F",
    },
    "Agricoles": {
        "Blé": "ZW=F",
        "Maïs": "ZC=F",
        "Soja": "ZS=F",
        "Café": "KC=F",
        "Cacao": "CC=F",
        "Sucre": "SB=F",
        "Coton": "CT=F",
    },
    "Élevage": {
        "Live cattle": "LE=F",
        "Feeder cattle": "GF=F",
        "Lean hogs": "HE=F",
    },
}

PERFORMANCE_HORIZONS = {
    "1 jour": 1,
    "1 semaine": 5,
    "2 semaines": 10,
    "1 mois": 21,
}

MACRO_CPI_SERIES = {
    "États-Unis": {
        "CPI total": "CPIAUCSL",
        "Core CPI": "CPILFESL",
    },
    "Zone euro": {
        "HICP total": "CP0000EZ19M086NEST",
    },
    "France": {
        "HICP total": "CP0000FRM086NEST",
        "Core CPI": "FRACPICORMINMEI",
    },
    "Allemagne": {
        "HICP total": "CP0000DEM086NEST",
        "Core CPI": "DEUCPICORMINMEI",
    },
    "Italie": {
        "HICP total": "CP0000ITM086NEST",
        "Core CPI": "ITACPICORMINMEI",
    },
    "Espagne": {
        "HICP total": "CP0000ESM086NEST",
        "Core CPI": "ESPCPICORMINMEI",
    },
    "Royaume-Uni": {
        "CPI total": "GBRCPIALLMINMEI",
        "Core CPI": "GBRCPICORMINMEI",
    },
    "Chine": {
        "CPI total": "CHNCPIALLMINMEI",
    },
    "Japon": {
        "CPI total": "JPNCPIALLMINMEI",
        "Core CPI": "JPNCPICORMINMEI",
    },
    "Canada": {
        "CPI total": "CANCPIALLMINMEI",
        "Core CPI": "CANCPICORMINMEI",
    },
    "Inde": {
        "CPI total": "INDCPIALLMINMEI",
    },
    "Brésil": {
        "CPI total": "BRACPIALLMINMEI",
    },
}

MACRO_HORIZONS = {
    "Var. 3 mois": 3,
    "Var. 6 mois": 6,
    "Var. 1 an": 12,
}

US_LABOR_SERIES = {
    "NFP": {
        "fred": "PAYEMS",
        "label": "Nonfarm payrolls",
    },
}

ASSET_COLORS = [
    "#8bb8e8",
    "#d7a86e",
    "#9ccf8a",
    "#c79bf2",
    "#e7b7c8",
    "#79c7b7",
    "#d8cf7a",
    "#9fb0c7",
    "#e09f86",
    "#8ed1e6",
    "#b8d28b",
    "#c4a7e7",
]

POSITIVE_STYLE = (
    "color: #b7e4d6; "
    "background-color: rgba(96, 190, 160, 0.14);"
)
NEGATIVE_STYLE = (
    "color: #f4b8b8; "
    "background-color: rgba(230, 120, 120, 0.14);"
)

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


def asset_color(name: str) -> str:
    stable_index = sum(
        (index + 1) * ord(character)
        for index, character in enumerate(name)
    )
    return ASSET_COLORS[
        stable_index % len(ASSET_COLORS)
    ]


def asset_badge(name: str) -> str:
    color = asset_color(name)
    return (
        f'<span style="display:inline-flex;align-items:center;gap:7px;">'
        f'<span style="width:10px;height:10px;border-radius:3px;'
        f'background:{color};display:inline-block;"></span>'
        f'<span>{name}</span></span>'
    )


def color_value_style(value: Any) -> str:
    if pd.isna(value):
        return "color: #8490a3;"
    if float(value) > 0:
        return POSITIVE_STYLE
    if float(value) < 0:
        return NEGATIVE_STYLE
    return "color: #d1d4dc;"


def format_change_value(
    value: Any,
    label: str,
) -> str:
    if pd.isna(value):
        return "—"

    if label in {
        "Dernier NFP",
        "Moy. 3 mois",
        "Moy. 6 mois",
        "Moy. 1 an",
        "Cumul 1 an",
    }:
        return f"{float(value):+.0f}k"

    suffix = " pt" if label.startswith("Var.") else "%"
    return f"{float(value):+.2f}{suffix}"


def style_performance_table(
    dataframe: pd.DataFrame,
) -> pd.io.formats.style.Styler:
    return (
        dataframe.style
        .map(color_value_style)
        .format(lambda value: "—" if pd.isna(value) else f"{value:+.2f}%")
    )


def style_change_columns(
    dataframe: pd.DataFrame,
    columns: list[str],
) -> pd.io.formats.style.Styler:
    valid_columns = [
        column
        for column in columns
        if column in dataframe.columns
    ]

    formatters = {
        column: (
            lambda value, column=column: format_change_value(
                value,
                column,
            )
        )
        for column in valid_columns
    }

    if "Dernier" in dataframe.columns:
        formatters["Dernier"] = (
            lambda value: "—"
            if pd.isna(value)
            else f"{float(value):.2f}"
        )

    return (
        dataframe.style
        .map(color_value_style, subset=valid_columns)
        .format(formatters)
    )


def style_bureau_table(
    dataframe: pd.DataFrame,
    change_columns: list[str],
    asset_column: str = "Actif",
) -> pd.io.formats.style.Styler:
    valid_change_columns = [
        column
        for column in change_columns
        if column in dataframe.columns
    ]

    def color_asset_column(row: pd.Series) -> list[str]:
        styles = [""] * len(row)

        if asset_column not in row.index:
            return styles

        color_key = str(row[asset_column])

        if "Famille" in row.index and str(row["Famille"]) != "Indices":
            color_key = f"{row['Famille']} · {row[asset_column]}"

        color = asset_color(color_key)
        asset_index = list(row.index).index(asset_column)
        styles[asset_index] = f"color: {color}; font-weight: 700;"

        return styles

    return (
        dataframe.style
        .apply(color_asset_column, axis=1)
        .map(color_value_style, subset=valid_change_columns)
        .format({
            **{
                column: (
                    lambda value, column=column: format_change_value(
                        value,
                        column,
                    )
                )
                for column in valid_change_columns
            },
            **(
                {
                    "Dernier": (
                        lambda value: "—"
                        if pd.isna(value)
                        else f"{float(value):.2f}"
                    )
                }
                if "Dernier" in dataframe.columns
                else {}
            ),
        })
    )


# =============================================================================
# BUREAU AI ASSISTANT
# =============================================================================

def get_secret_value(
    name: str,
    default: str | None = None,
) -> str | None:
    value = None

    try:
        value = st.secrets.get(name)
    except Exception:
        value = None

    if value is None:
        value = os.environ.get(name)

    if value in (None, ""):
        return default

    return str(value)


def clean_ai_value(value: Any) -> Any:
    if pd.isna(value):
        return None

    if isinstance(value, float):
        return round(value, 4)

    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()

    return value


def dataframe_preview(
    dataframe: pd.DataFrame,
    max_rows: int = 12,
) -> str:
    if dataframe is None or dataframe.empty:
        return "Aucune donnée disponible."

    preview = dataframe.head(max_rows).copy()

    for column in preview.columns:
        preview[column] = preview[column].map(clean_ai_value)

    return preview.to_string(index=False)


def selected_dataframe_rows(event: Any) -> list[int]:
    try:
        return list(event.selection.rows)
    except Exception:
        pass

    try:
        return list(event["selection"]["rows"])
    except Exception:
        return []


def set_bureau_ai_selection(
    label: str,
    context: str,
) -> None:
    st.session_state["bureau_ai_selected_label"] = label
    st.session_state["bureau_ai_selected_context"] = context


def metric_context_from_row(
    row: pd.Series | dict[str, Any],
) -> str:
    items = []

    for key, value in dict(row).items():
        if pd.isna(value):
            continue

        if isinstance(value, float):
            value = f"{value:.4f}"

        items.append(f"- {key}: {value}")

    return "\n".join(items)


def add_context_option(
    options: dict[str, str],
    label: str,
    context: str,
) -> None:
    base_label = label
    suffix = 2

    while label in options:
        label = f"{base_label} ({suffix})"
        suffix += 1

    options[label] = context


def extract_openai_text(data: dict[str, Any]) -> str:
    output_text = data.get("output_text")
    if output_text:
        return str(output_text).strip()

    parts: list[str] = []

    for item in data.get("output", []):
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue

            text = content.get("text") or content.get("output_text")

            if text:
                parts.append(str(text))

    return "\n\n".join(parts).strip()


def openai_error_message(
    response: requests.Response,
) -> str:
    try:
        payload = response.json()
        error = payload.get("error", {})
    except Exception:
        return response.text[:700]

    code = error.get("code")
    message = error.get("message", "")

    if code == "insufficient_quota":
        return (
            "quota OpenAI insuffisant. La clé est bien lue par le site, "
            "mais le projet OpenAI n'a pas de crédit/quota actif. "
            "Active le billing OpenAI ou utilise une clé d'un projet avec "
            "quota disponible."
        )

    if code == "invalid_api_key":
        return (
            "clé OpenAI invalide ou révoquée. Remplace OPENAI_API_KEY "
            "dans les secrets Streamlit."
        )

    if response.status_code == 429:
        return (
            "limite OpenAI atteinte. Réessaie plus tard ou vérifie les "
            f"quotas du projet. Détail: {message[:300]}"
        )

    return message[:700] or response.text[:700]


def groq_error_message(
    response: requests.Response,
) -> str:
    try:
        payload = response.json()
        error = payload.get("error", {})
    except Exception:
        return response.text[:700]

    message = error.get("message", "")
    code = error.get("code")

    if response.status_code in {401, 403}:
        return (
            "clé Groq invalide ou non autorisée. Remplace GROQ_API_KEY "
            "dans les secrets Streamlit."
        )

    if response.status_code == 429:
        return (
            "quota ou limite Groq atteint. Réessaie plus tard ou vérifie "
            f"les limites du compte Groq. Détail: {message[:300]}"
        )

    if code:
        return f"{code}: {message[:650]}"

    return message[:700] or response.text[:700]


def build_bureau_ai_prompt(
    *,
    selected_label: str,
    selected_context: str,
    dashboard_context: str,
    user_question: str,
    use_web: bool,
) -> str:
    question = user_question.strip() or (
        "Explique simplement ce que signifie l'élément sélectionné."
    )
    web_instruction = (
        "Si tu utilises le web, distingue ce qui vient du dashboard et ce "
        "qui vient de sources externes."
        if use_web
        else "N'utilise que les données fournies par le dashboard."
    )

    return f"""
Tu es l'assistant analyste intégré au Bureau Larbou de Flavio Monitor.
Réponds en français, de façon claire et utile pour lire le dashboard.
Tu n'envoies aucun ordre, tu ne donnes pas de recommandation d'achat ou de vente.
{web_instruction}
Si tu n'as pas assez d'information, dis-le clairement.

Date système: {pd.Timestamp.utcnow().date().isoformat()}

Élément sélectionné par l'utilisateur:
{selected_label}

Contexte exact de l'élément:
{selected_context}

Vue synthétique du Bureau Larbou:
{dashboard_context}

Question ou contexte utilisateur:
{question}

Format attendu:
- commence par une réponse courte en 2-3 phrases ;
- puis donne les points importants ;
- reste prudent sur les causes de marché et signale les hypothèses.
""".strip()


def call_bureau_ai(
    *,
    provider: str,
    api_key: str,
    model: str,
    selected_label: str,
    selected_context: str,
    dashboard_context: str,
    user_question: str,
    use_web: bool,
) -> str:
    provider = provider.lower().strip()
    prompt = build_bureau_ai_prompt(
        selected_label=selected_label,
        selected_context=selected_context,
        dashboard_context=dashboard_context,
        user_question=user_question,
        use_web=use_web and provider == "openai",
    )

    if provider == "groq":
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Tu es un analyste de marché prudent. "
                        "Tu réponds uniquement en français."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.2,
            "max_tokens": 900,
        }

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload),
            timeout=75,
        )

        if response.status_code >= 400:
            raise RuntimeError(
                f"Groq a retourné {response.status_code}: "
                f"{groq_error_message(response)}"
            )

        data = response.json()
        answer = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

        if not answer:
            raise RuntimeError(
                "Réponse Groq vide malgré un appel API réussi."
            )

        return answer

    if provider != "openai":
        raise RuntimeError(
            "AI_PROVIDER doit valoir 'groq' ou 'openai'."
        )

    payload: dict[str, Any] = {
        "model": model,
        "input": prompt,
        "max_output_tokens": 900,
    }

    if use_web:
        payload["tools"] = [
            {
                "type": "web_search",
            }
        ]
        payload["tool_choice"] = "auto"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers=headers,
        data=json.dumps(payload),
        timeout=75,
    )

    if (
        use_web
        and response.status_code in {400, 404}
    ):
        payload.pop("tools", None)
        payload.pop("tool_choice", None)
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers=headers,
            data=json.dumps(payload),
            timeout=75,
        )

    if response.status_code >= 400:
        raise RuntimeError(
            f"OpenAI a retourné {response.status_code}: "
            f"{openai_error_message(response)}"
        )

    answer = extract_openai_text(response.json())

    if not answer:
        raise RuntimeError(
            "Réponse IA vide malgré un appel API réussi."
        )

    return answer


def render_bureau_ai_assistant(
    context_options: dict[str, str],
    dashboard_context: str,
) -> None:
    with bureau_ai_slot.container():
        _, assistant_column = st.columns(
            [5.2, 2.4],
            vertical_alignment="top",
        )

        with assistant_column:
            assistant_open = bool(
                st.session_state.get("bureau_ai_open", False)
            )

            if st.button(
                "Fermer l'assistant" if assistant_open else "Assistant IA",
                use_container_width=True,
                key="bureau_ai_toggle_button",
            ):
                assistant_open = not assistant_open
                st.session_state["bureau_ai_open"] = assistant_open

            if not assistant_open:
                return

            with st.container(border=True):
                st.markdown(
                    '<div class="bureau-ai-panel-title">'
                    "Assistant Bureau</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    '<div class="bureau-ai-panel-hint">'
                    "Clique une ligne du Bureau, ou choisis un élément ici, "
                    "puis demande une explication. Le panneau reste ouvert "
                    "après l'analyse.</div>",
                    unsafe_allow_html=True,
                )

                if not context_options:
                    st.info(
                        "Le Bureau n'a pas encore assez de données à analyser."
                    )
                    return

                labels = list(context_options)
                session_label = st.session_state.get(
                    "bureau_ai_selected_label"
                )
                default_index = (
                    labels.index(session_label)
                    if session_label in labels
                    else 0
                )

                selected_label = st.selectbox(
                    "Élément",
                    options=labels,
                    index=default_index,
                    key="bureau_ai_context_picker",
                )

                st.markdown(
                    f'<div class="bureau-ai-chip">Sélection : '
                    f'{selected_label}</div>',
                    unsafe_allow_html=True,
                )

                question = st.text_area(
                    "Question ou contexte optionnel",
                    placeholder=(
                        "Ex : explique pourquoi ça monte, compare avec "
                        "les autres actifs, ou résume le signal macro."
                    ),
                    key="bureau_ai_question",
                    height=95,
                )

                provider = get_secret_value(
                    "AI_PROVIDER",
                    "groq",
                ).lower().strip()
                provider_label = (
                    "Groq"
                    if provider == "groq"
                    else "OpenAI"
                    if provider == "openai"
                    else provider
                )
                st.caption(f"Moteur IA : {provider_label}")

                use_web = st.toggle(
                    "Recherche web si utile",
                    value=provider == "openai",
                    disabled=provider != "openai",
                    key="bureau_ai_use_web",
                    help=(
                        "Disponible avec OpenAI. Avec Groq, l'assistant "
                        "analyse les données du dashboard sans recherche web."
                    ),
                )

                if st.button(
                    "Expliquer",
                    type="primary",
                    use_container_width=True,
                    key="bureau_ai_explain_button",
                ):
                    st.session_state["bureau_ai_open"] = True
                    if provider == "groq":
                        api_key = get_secret_value("GROQ_API_KEY")
                        model = get_secret_value(
                            "GROQ_MODEL",
                            "llama-3.3-70b-versatile",
                        )
                        missing_secret_message = (
                            "Ajoute GROQ_API_KEY dans les secrets "
                            "Streamlit pour activer l'assistant Groq."
                        )
                    elif provider == "openai":
                        api_key = get_secret_value("OPENAI_API_KEY")
                        model = get_secret_value(
                            "OPENAI_MODEL",
                            "gpt-4.1-mini",
                        )
                        missing_secret_message = (
                            "Ajoute OPENAI_API_KEY dans les secrets "
                            "Streamlit pour activer l'assistant OpenAI."
                        )
                    else:
                        api_key = None
                        model = None
                        missing_secret_message = (
                            "AI_PROVIDER doit valoir 'groq' ou 'openai'."
                        )
                    st.session_state.pop(
                        "bureau_ai_last_error",
                        None,
                    )

                    if not api_key:
                        st.session_state[
                            "bureau_ai_last_error"
                        ] = missing_secret_message
                    else:
                        with st.spinner("Analyse en cours..."):
                            try:
                                answer = call_bureau_ai(
                                    provider=provider,
                                    api_key=api_key,
                                    model=model
                                    or (
                                        "llama-3.3-70b-versatile"
                                        if provider == "groq"
                                        else "gpt-4.1-mini"
                                    ),
                                    selected_label=selected_label,
                                    selected_context=context_options[
                                        selected_label
                                    ],
                                    dashboard_context=dashboard_context,
                                    user_question=question,
                                    use_web=use_web,
                                )
                                st.session_state[
                                    "bureau_ai_last_answer"
                                ] = answer
                            except Exception as error:
                                st.session_state[
                                    "bureau_ai_last_error"
                                ] = (
                                    "Assistant IA indisponible : "
                                    f"{error}"
                                )

                last_error = st.session_state.get(
                    "bureau_ai_last_error"
                )
                last_answer = st.session_state.get(
                    "bureau_ai_last_answer"
                )

                if last_error:
                    st.markdown("---")
                    st.error(last_error)
                elif last_answer:
                    st.markdown("---")
                    st.markdown(last_answer)


# =============================================================================
# INDEX PERFORMANCE
# =============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def load_symbol_performance(
    selected_names: tuple[str, ...],
    symbol_items: tuple[tuple[str, str], ...],
    max_horizon: int = 21,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    symbol_map = dict(symbol_items)
    selected_symbols = [
        symbol_map[name]
        for name in selected_names
        if name in symbol_map
    ]

    if not selected_symbols:
        raise ValueError("Aucun actif sélectionné.")

    downloaded = yf.download(
        tickers=selected_symbols,
        period="5y",
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=True,
        group_by="column",
    )

    close = extract_close_frame(
        downloaded,
        selected_symbols,
    )

    if close.empty:
        raise ValueError(
            "Yahoo n’a retourné aucune clôture pour la sélection."
        )

    reverse_names = {
        symbol: name
        for name, symbol in symbol_map.items()
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

    for asset_name in selected_names:
        if asset_name not in close.columns:
            horizon_values[asset_name] = {
                f"{day}j": None
                for day in range(1, max_horizon + 1)
            }
            continue

        series = close[asset_name].dropna()
        current = (
            float(series.iloc[-1])
            if not series.empty
            else None
        )

        row: dict[str, float | None] = {}

        for day in range(1, max_horizon + 1):
            if current is None or len(series) <= day:
                row[f"{day}j"] = None
            else:
                reference = float(
                    series.iloc[-(day + 1)]
                )
                row[f"{day}j"] = (
                    current / reference - 1
                ) * 100

        horizon_values[asset_name] = row

    performance = pd.DataFrame.from_dict(
        horizon_values,
        orient="index",
    )

    return performance, close


def flatten_commodity_symbols(
    selected_families: list[str],
) -> dict[str, str]:
    symbols: dict[str, str] = {}

    for family in selected_families:
        for name, symbol in COMMODITY_SYMBOLS.get(family, {}).items():
            symbols[f"{family} · {name}"] = symbol

    return symbols


@st.cache_data(ttl=21600, show_spinner=False)
def load_fred_series(
    series_id: str,
) -> pd.Series:
    url = (
        "https://fred.stlouisfed.org/graph/fredgraph.csv"
        f"?id={series_id}"
    )
    dataframe = pd.read_csv(url)

    if "observation_date" not in dataframe.columns:
        raise ValueError(f"Série FRED invalide : {series_id}")

    value_columns = [
        column
        for column in dataframe.columns
        if column != "observation_date"
    ]

    if not value_columns:
        raise ValueError(f"Aucune colonne valeur pour {series_id}")

    series = pd.Series(
        pd.to_numeric(
            dataframe[value_columns[0]],
            errors="coerce",
        ).values,
        index=pd.to_datetime(
            dataframe["observation_date"],
            errors="coerce",
        ),
        name=series_id,
    )

    series = series.dropna()
    series = series[~series.index.isna()].sort_index()

    if series.empty:
        raise ValueError(f"Aucune donnée exploitable pour {series_id}")

    return series


def inflation_yoy_series(
    series: pd.Series,
) -> pd.Series:
    return (
        series.pct_change(
            periods=12,
            fill_method=None,
        )
        * 100
    ).dropna()


def point_change_over_months(
    series: pd.Series,
    months: int,
) -> float | None:
    if len(series) <= months:
        return None

    return float(series.iloc[-1] - series.iloc[-(months + 1)])


def nfp_monthly_change_series(
    payroll_level_series: pd.Series,
) -> pd.Series:
    return payroll_level_series.diff().dropna()


def trailing_average(
    series: pd.Series,
    months: int,
) -> float | None:
    if series.empty:
        return None

    window = series.tail(months).dropna()

    if window.empty:
        return None

    return float(window.mean())


@st.cache_data(ttl=21600, show_spinner=False)
def load_us_labor_bookmap() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    history_frames: list[pd.DataFrame] = []
    today = pd.Timestamp.utcnow().tz_localize(None)

    for short_name, config in US_LABOR_SERIES.items():
        series_id = config["fred"]
        label = config["label"]
        level_series = load_fred_series(series_id)
        nfp_series = nfp_monthly_change_series(level_series)

        if nfp_series.empty:
            continue

        latest_date = pd.Timestamp(nfp_series.index[-1])
        months_lag = (
            today.year - latest_date.year
        ) * 12 + today.month - latest_date.month
        freshness = (
            "Récent"
            if months_lag <= 2
            else (
                "À surveiller"
                if months_lag <= 6
                else "Ancien"
            )
        )

        row = {
            "Zone": "États-Unis",
            "Indicateur": short_name,
            "Description": label,
            "FRED": series_id,
            "Dernière date": latest_date.date().isoformat(),
            "Dernier NFP": float(nfp_series.iloc[-1]),
            "Moy. 3 mois": trailing_average(
                nfp_series,
                3,
            ),
            "Moy. 6 mois": trailing_average(
                nfp_series,
                6,
            ),
            "Moy. 1 an": trailing_average(
                nfp_series,
                12,
            ),
            "Cumul 1 an": float(nfp_series.tail(12).sum())
            if len(nfp_series) >= 12
            else None,
            "Fraîcheur": freshness,
        }
        rows.append(row)

        frame = nfp_series.tail(60).rename(
            "NFP mensuel"
        ).to_frame()
        frame["Zone"] = "États-Unis"
        frame["Indicateur"] = short_name
        frame["Série"] = f"États-Unis · {short_name}"
        frame["Date"] = frame.index
        history_frames.append(
            frame.reset_index(drop=True)
        )

    summary = pd.DataFrame(rows)
    history = (
        pd.concat(history_frames, ignore_index=True)
        if history_frames
        else pd.DataFrame()
    )

    return summary, history


@st.cache_data(ttl=21600, show_spinner=False)
def load_macro_bookmap(
    selected_regions: tuple[str, ...],
    selected_indicators: tuple[str, ...],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    history_frames: list[pd.DataFrame] = []
    today = pd.Timestamp.utcnow().tz_localize(None)

    for region in selected_regions:
        indicator_map = MACRO_CPI_SERIES.get(region, {})

        for indicator in selected_indicators:
            series_id = indicator_map.get(indicator)

            if series_id is None:
                continue

            try:
                series = load_fred_series(series_id)
            except Exception:
                continue

            inflation_series = inflation_yoy_series(series)

            if inflation_series.empty:
                continue

            latest_date = pd.Timestamp(inflation_series.index[-1])
            months_lag = (
                today.year - latest_date.year
            ) * 12 + today.month - latest_date.month
            freshness = (
                "Récent"
                if months_lag <= 3
                else (
                    "À surveiller"
                    if months_lag <= 12
                    else "Ancien"
                )
            )

            row = {
                "Zone": region,
                "Indicateur": indicator,
                "FRED": series_id,
                "Dernière date": latest_date.date().isoformat(),
                "Inflation YoY": float(inflation_series.iloc[-1]),
                "Fraîcheur": freshness,
            }

            for label, months in MACRO_HORIZONS.items():
                row[label] = point_change_over_months(
                    inflation_series,
                    months,
                )

            rows.append(row)

            frame = inflation_series.tail(60).rename(
                "Inflation YoY"
            ).to_frame()
            frame["Zone"] = region
            frame["Indicateur"] = indicator
            frame["Série"] = f"{region} · {indicator}"
            frame["Date"] = frame.index
            history_frames.append(frame.reset_index(drop=True))

    summary = pd.DataFrame(rows)
    history = (
        pd.concat(history_frames, ignore_index=True)
        if history_frames
        else pd.DataFrame()
    )

    return summary, history


with st.sidebar:
    st.markdown("### Bureau Larbou")

    if st.button(
        "Actualiser les données",
        use_container_width=True,
    ):
        st.cache_data.clear()
        st.rerun()

    st.caption(
        "Les horizons courts utilisent les derniers jours de cotation disponibles ; "
        "les graphiques historiques affichent une base 100 sur 5 ans."
    )

    selected_indices = st.multiselect(
        "Indices suivis",
        options=list(INDEX_SYMBOLS),
        default=[
            "CAC 40",
            "Euro Stoxx 50",
        ],
        help="Choisis les indices affichés dans les cartes, le graphique et le tableau général.",
    )

    selected_commodity_families = st.multiselect(
        "Familles matières premières",
        options=list(COMMODITY_SYMBOLS),
        default=[
            "Agricoles",
        ],
        help="Les contrats Yahoo Finance sont regroupés par famille.",
    )

if not selected_indices:
    selected_indices = ["CAC 40"]
    st.warning(
        "Aucun indice sélectionné : CAC 40 affiché par défaut."
    )

bureau_ai_context_options: dict[str, str] = {}
display_macro = pd.DataFrame()
display_labor = pd.DataFrame()
top_movers = pd.DataFrame()
bottom_movers = pd.DataFrame()


try:
    performance_table, index_closes = load_symbol_performance(
        tuple(selected_indices),
        tuple(INDEX_SYMBOLS.items()),
    )
except Exception as error:
    st.error(f"Performance indices : {error}")
    st.stop()

for index_name in selected_indices:
    if index_name not in performance_table.index:
        continue

    row = {
        "Classe": "Indice",
        "Actif": index_name,
    }

    for label, days in PERFORMANCE_HORIZONS.items():
        row[label] = performance_table.loc[
            index_name,
            f"{days}j",
        ]

    series = index_closes[index_name].dropna()

    if not series.empty:
        row["Première date historique"] = (
            pd.Timestamp(series.index[0]).date().isoformat()
        )
        row["Dernière date historique"] = (
            pd.Timestamp(series.index[-1]).date().isoformat()
        )
        row["Dernière clôture"] = float(series.iloc[-1])

    add_context_option(
        bureau_ai_context_options,
        f"Indice · {index_name}",
        metric_context_from_row(row),
    )


st.markdown(
    '<div class="section-label">Indices sélectionnés</div>',
    unsafe_allow_html=True,
)

metric_horizons = [
    (f"{days}j", label)
    for label, days in PERFORMANCE_HORIZONS.items()
]

for index_name in selected_indices:
    if index_name not in performance_table.index:
        continue

    st.markdown(
        f"#### {asset_badge(index_name)}",
        unsafe_allow_html=True,
    )

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


index_chart = go.Figure()

for index_name in selected_indices:
    if index_name not in performance_table.index:
        continue

    series = index_closes[index_name].dropna()
    if series.empty:
        continue

    normalized = series / float(series.iloc[0]) * 100

    index_chart.add_trace(
        go.Scatter(
            x=normalized.index,
            y=normalized.tolist(),
            mode="lines",
            name=index_name,
            line=dict(
                color=asset_color(index_name),
                width=2.2,
            ),
            hovertemplate=(
                index_name
                + "<br>%{x|%Y-%m-%d}"
                + "<br>Base 100: %{y:.2f}"
                + "<extra></extra>"
            ),
        )
    )

index_chart.add_hline(
    y=100,
    line_width=1,
    line_dash="dot",
)

index_chart.update_layout(
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
        title="Date",
        gridcolor="#202938",
        zeroline=False,
    ),
    yaxis=dict(
        title="Base 100",
        gridcolor="#202938",
        zeroline=False,
        side="right",
    ),
)

st.plotly_chart(
    index_chart,
    use_container_width=True,
    config={
        "displaylogo": False,
        "scrollZoom": True,
    },
)

with st.expander(
    "Voir toutes les performances indices de 1j à 21j",
    expanded=False,
):
    st.dataframe(
        style_performance_table(
            performance_table
        ),
        use_container_width=True,
    )

st.caption(
    "Calcul : dernières clôtures Yahoo disponibles. Les cartes montrent les "
    "variations courtes ; le graphique affiche l'historique en base 100 sur "
    "5 ans quand la donnée existe."
)


# =============================================================================
# COMMODITIES
# =============================================================================

commodity_performance = pd.DataFrame()
commodity_symbols = flatten_commodity_symbols(
    selected_commodity_families
)

if commodity_symbols:
    st.divider()

    st.markdown(
        '<div class="section-label">Matières premières</div>',
        unsafe_allow_html=True,
    )

    try:
        commodity_performance, commodity_closes = load_symbol_performance(
            tuple(commodity_symbols),
            tuple(commodity_symbols.items()),
        )

        commodity_rows = []

        for full_name, row in commodity_performance.iterrows():
            family, asset = full_name.split(" · ", 1)
            item = {
                "Famille": family,
                "Actif": asset,
            }

            for label, days in PERFORMANCE_HORIZONS.items():
                item[label] = row.get(f"{days}j")

            commodity_rows.append(item)

        commodity_table = pd.DataFrame(commodity_rows)

        for item in commodity_rows:
            label = (
                f"Matière première · {item['Famille']} · "
                f"{item['Actif']}"
            )
            full_name = f"{item['Famille']} · {item['Actif']}"
            context_row = {
                **item,
            }

            if full_name in commodity_closes.columns:
                series = commodity_closes[full_name].dropna()

                if not series.empty:
                    context_row["Dernière clôture"] = float(
                        series.iloc[-1]
                    )
                    context_row["Dernière date"] = pd.Timestamp(
                        series.index[-1]
                    ).date().isoformat()

            add_context_option(
                bureau_ai_context_options,
                label,
                metric_context_from_row(context_row),
            )

        st.dataframe(
            style_bureau_table(
                commodity_table,
                list(PERFORMANCE_HORIZONS),
            ),
            hide_index=True,
            use_container_width=True,
        )

        commodity_chart = go.Figure()

        for full_name in commodity_performance.index:
            series = commodity_closes[full_name].dropna()
            if series.empty:
                continue

            normalized = series / float(series.iloc[0]) * 100
            commodity_chart.add_trace(
                go.Scatter(
                    x=normalized.index,
                    y=normalized.tolist(),
                    mode="lines",
                    name=full_name,
                    line=dict(
                        color=asset_color(full_name),
                        width=1.9,
                    ),
                    hovertemplate=(
                        full_name
                        + "<br>%{x|%Y-%m-%d}"
                        + "<br>Base 100: %{y:.2f}"
                        + "<extra></extra>"
                    ),
                )
            )

        commodity_chart.add_hline(
            y=100,
            line_width=1,
            line_dash="dot",
        )
        commodity_chart.update_layout(
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
                title="Date",
                gridcolor="#202938",
                zeroline=False,
            ),
            yaxis=dict(
                title="Base 100",
                gridcolor="#202938",
                zeroline=False,
                side="right",
            ),
        )

        with st.expander(
            "Historique matières premières base 100 sur 5 ans",
            expanded=False,
        ):
            st.plotly_chart(
                commodity_chart,
                use_container_width=True,
                config={
                    "displaylogo": False,
                    "scrollZoom": True,
                },
            )

    except Exception as error:
        st.warning(
            f"Matières premières indisponibles : {error}"
        )


st.divider()

st.markdown(
    '<div class="section-label">Tableau général</div>',
    unsafe_allow_html=True,
)

general_rows = []

for index_name, row in performance_table.iterrows():
    item = {
        "Classe": "Indice",
        "Famille": "Indices",
        "Actif": index_name,
    }

    for label, days in PERFORMANCE_HORIZONS.items():
        item[label] = row.get(f"{days}j")

    general_rows.append(item)

if not commodity_performance.empty:
    for full_name, row in commodity_performance.iterrows():
        family, asset = full_name.split(" · ", 1)
        item = {
            "Classe": "Matière première",
            "Famille": family,
            "Actif": asset,
        }

        for label, days in PERFORMANCE_HORIZONS.items():
            item[label] = row.get(f"{days}j")

        general_rows.append(item)

general_table = pd.DataFrame(general_rows)

general_table_event = st.dataframe(
    style_bureau_table(
        general_table,
        list(PERFORMANCE_HORIZONS),
    ),
    hide_index=True,
    use_container_width=True,
    on_select="rerun",
    selection_mode="single-row",
    key="bureau_general_table",
)

general_selected_rows = selected_dataframe_rows(
    general_table_event
)

if general_selected_rows:
    selected_general_row = general_table.iloc[
        general_selected_rows[0]
    ]
    selected_general_label = (
        f"{selected_general_row['Classe']} · "
        f"{selected_general_row['Famille']} · "
        f"{selected_general_row['Actif']}"
    )
    selected_general_context = metric_context_from_row(
        selected_general_row
    )
    set_bureau_ai_selection(
        selected_general_label,
        selected_general_context,
    )
    add_context_option(
        bureau_ai_context_options,
        selected_general_label,
        selected_general_context,
    )


st.divider()

st.markdown(
    '<div class="section-label">Macro bookmap inflation</div>',
    unsafe_allow_html=True,
)

macro_control_one, macro_control_two, macro_control_three = st.columns(
    [2.2, 1.4, 1]
)

with macro_control_one:
    selected_macro_regions = st.multiselect(
        "Zones / pays",
        options=list(MACRO_CPI_SERIES),
        default=[
            "États-Unis",
            "Zone euro",
            "France",
            "Allemagne",
            "Chine",
            "Japon",
        ],
        help="Sélectionne les grandes zones que tu veux surveiller.",
    )

with macro_control_two:
    available_macro_indicators = sorted(
        {
            indicator
            for region in selected_macro_regions
            for indicator in MACRO_CPI_SERIES.get(region, {})
        }
    )
    selected_macro_indicators = st.multiselect(
        "Indicateurs",
        options=available_macro_indicators,
        default=[
            indicator
            for indicator in ["CPI total", "HICP total", "Core CPI"]
            if indicator in available_macro_indicators
        ],
        help="Les séries manquantes pour un pays sont ignorées automatiquement.",
    )

with macro_control_three:
    macro_sort_label = st.selectbox(
        "Tri",
        options=["Inflation YoY", *list(MACRO_HORIZONS)],
        index=0,
    )

if not selected_macro_regions or not selected_macro_indicators:
    st.info(
        "Choisis au moins une zone et un indicateur pour afficher le bookmap macro."
    )
else:
    macro_summary, macro_history = load_macro_bookmap(
        tuple(selected_macro_regions),
        tuple(selected_macro_indicators),
    )

    if macro_summary.empty:
        st.warning(
            "Aucune série macro exploitable pour cette sélection."
        )
    else:
        macro_summary = macro_summary.sort_values(
            by=macro_sort_label,
            ascending=False,
            na_position="last",
        )

        display_macro = macro_summary[
            [
                "Zone",
                "Indicateur",
                "Dernière date",
                "Inflation YoY",
                *list(MACRO_HORIZONS),
                "Fraîcheur",
            ]
        ].copy()

        for _, row in display_macro.iterrows():
            macro_label = (
                f"Macro · {row['Zone']} · {row['Indicateur']}"
            )
            add_context_option(
                bureau_ai_context_options,
                macro_label,
                metric_context_from_row(row),
            )

        macro_table_event = st.dataframe(
            style_bureau_table(
                display_macro,
                ["Inflation YoY", *list(MACRO_HORIZONS)],
                asset_column="Zone",
            ),
            hide_index=True,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
            key="bureau_macro_table",
        )

        macro_selected_rows = selected_dataframe_rows(
            macro_table_event
        )

        if macro_selected_rows:
            selected_macro_row = display_macro.iloc[
                macro_selected_rows[0]
            ]
            selected_macro_label = (
                f"Macro · {selected_macro_row['Zone']} · "
                f"{selected_macro_row['Indicateur']}"
            )
            selected_macro_context = metric_context_from_row(
                selected_macro_row
            )
            set_bureau_ai_selection(
                selected_macro_label,
                selected_macro_context,
            )
            add_context_option(
                bureau_ai_context_options,
                selected_macro_label,
                selected_macro_context,
            )

        if not macro_history.empty:
            macro_history_chart = go.Figure()

            for series_name, group in macro_history.groupby("Série"):
                macro_history_chart.add_trace(
                    go.Scatter(
                        x=group["Date"],
                        y=group["Inflation YoY"],
                        mode="lines",
                        name=series_name,
                        line=dict(
                            color=asset_color(series_name),
                            width=2,
                        ),
                        hovertemplate=(
                            series_name
                            + "<br>%{x|%Y-%m}"
                            + "<br>Inflation YoY: %{y:+.2f}%"
                            + "<extra></extra>"
                        ),
                    )
                )

            macro_history_chart.update_layout(
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
                    gridcolor="#202938",
                    zeroline=False,
                ),
                yaxis=dict(
                    title="Inflation YoY",
                    ticksuffix="%",
                    gridcolor="#202938",
                    zeroline=False,
                    side="right",
                ),
            )

            with st.expander(
                "Historique inflation YoY sur 5 ans",
                expanded=False,
            ):
                st.plotly_chart(
                    macro_history_chart,
                    use_container_width=True,
                    config={
                        "displaylogo": False,
                        "scrollZoom": True,
                    },
                )

        st.caption(
            "Source : FRED / Federal Reserve Bank of St. Louis. "
            "Inflation YoY = variation de l'indice CPI/HICP par rapport au "
            "même mois un an plus tôt. Les colonnes Var. indiquent la "
            "variation du taux d'inflation en points de pourcentage sur "
            "3 mois, 6 mois et 1 an. La colonne fraîcheur signale les "
            "séries anciennes."
        )


st.divider()

st.markdown(
    '<div class="section-label">Emploi US · NFP</div>',
    unsafe_allow_html=True,
)

try:
    labor_summary, labor_history = load_us_labor_bookmap()

    if labor_summary.empty:
        st.warning(
            "Aucune série emploi US exploitable pour le moment."
        )
    else:
        display_labor = labor_summary[
            [
                "Zone",
                "Indicateur",
                "Dernière date",
                "Dernier NFP",
                "Moy. 3 mois",
                "Moy. 6 mois",
                "Moy. 1 an",
                "Cumul 1 an",
                "Fraîcheur",
            ]
        ].copy()

        for _, row in display_labor.iterrows():
            labor_label = (
                f"Emploi US · {row['Indicateur']}"
            )
            add_context_option(
                bureau_ai_context_options,
                labor_label,
                metric_context_from_row(row),
            )

        labor_table_event = st.dataframe(
            style_bureau_table(
                display_labor,
                [
                    "Dernier NFP",
                    "Moy. 3 mois",
                    "Moy. 6 mois",
                    "Moy. 1 an",
                    "Cumul 1 an",
                ],
                asset_column="Zone",
            ),
            hide_index=True,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
            key="bureau_labor_table",
        )

        labor_selected_rows = selected_dataframe_rows(
            labor_table_event
        )

        if labor_selected_rows:
            selected_labor_row = display_labor.iloc[
                labor_selected_rows[0]
            ]
            selected_labor_label = (
                f"Emploi US · {selected_labor_row['Indicateur']}"
            )
            selected_labor_context = metric_context_from_row(
                selected_labor_row
            )
            set_bureau_ai_selection(
                selected_labor_label,
                selected_labor_context,
            )
            add_context_option(
                bureau_ai_context_options,
                selected_labor_label,
                selected_labor_context,
            )

        if not labor_history.empty:
            labor_chart = go.Figure()

            for series_name, group in labor_history.groupby("Série"):
                labor_chart.add_trace(
                    go.Bar(
                        x=group["Date"],
                        y=group["NFP mensuel"],
                        name=series_name,
                        marker_color=asset_color(series_name),
                        hovertemplate=(
                            series_name
                            + "<br>%{x|%Y-%m}"
                            + "<br>NFP: %{y:+.0f}k"
                            + "<extra></extra>"
                        ),
                    )
                )

            labor_chart.add_hline(
                y=0,
                line_width=1,
                line_dash="dot",
            )
            labor_chart.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0b0f15",
                plot_bgcolor="#0b0f15",
                height=390,
                margin=dict(l=25, r=25, t=30, b=35),
                hovermode="x unified",
                xaxis=dict(
                    gridcolor="#202938",
                    zeroline=False,
                ),
                yaxis=dict(
                    title="Créations nettes d'emplois",
                    ticksuffix="k",
                    gridcolor="#202938",
                    zeroline=False,
                    side="right",
                ),
            )

            with st.expander(
                "Historique NFP sur 5 ans",
                expanded=False,
            ):
                st.plotly_chart(
                    labor_chart,
                    use_container_width=True,
                    config={
                        "displaylogo": False,
                        "scrollZoom": True,
                    },
                )

        st.caption(
            "Source : FRED / Federal Reserve Bank of St. Louis, série PAYEMS. "
            "Le NFP affiché correspond à la variation mensuelle de l'emploi "
            "salarié non agricole total, en milliers d'emplois."
        )

except Exception as error:
    st.warning(
        f"NFP indisponible : {error}"
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
    period: str = "3mo",
    chunk_size: int = 90,
) -> pd.DataFrame:
    close_frames: list[pd.DataFrame] = []

    for start in range(0, len(symbols), chunk_size):
        chunk = symbols[
            start:start + chunk_size
        ]

        downloaded = yf.download(
            tickers=chunk,
            period=period,
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
    horizon_days: int = 1,
) -> pd.DataFrame:
    constituents = load_constituents(
        universe
    )

    close = download_close_chunks(
        constituents["Yahoo"].tolist(),
        period="3mo",
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

        if len(series) <= horizon_days:
            continue

        previous = float(series.iloc[-(horizon_days + 1)])
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
                "Période": f"{horizon_days}j",
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

control_one, control_two, control_three = st.columns(
    [2, 1.4, 1]
)

with control_one:
    movers_universe = st.selectbox(
        "Univers",
        options=["CAC 40", "S&P 500"],
    )

with control_two:
    movers_period_label = st.selectbox(
        "Période",
        options=list(PERFORMANCE_HORIZONS),
        index=0,
    )

with control_three:
    mover_count = st.selectbox(
        "Nombre de valeurs",
        options=[5, 10, 15, 20],
        index=0,
    )

movers_horizon_days = PERFORMANCE_HORIZONS[movers_period_label]

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
            movers_universe,
            movers_horizon_days,
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

    for _, row in top_movers[display_columns].iterrows():
        add_context_option(
            bureau_ai_context_options,
            f"Top performer · {row['Ticker']} · {row['Nom']}",
            metric_context_from_row(
                {
                    **row.to_dict(),
                    "Univers": movers_universe,
                    "Période": movers_period_label,
                    "Rang": "Top performer",
                }
            ),
        )

    for _, row in bottom_movers[display_columns].iterrows():
        add_context_option(
            bureau_ai_context_options,
            f"Flop performer · {row['Ticker']} · {row['Nom']}",
            metric_context_from_row(
                {
                    **row.to_dict(),
                    "Univers": movers_universe,
                    "Période": movers_period_label,
                    "Rang": "Flop performer",
                }
            ),
        )

    with top_column:
        st.markdown("#### Top")
        top_movers_event = st.dataframe(
            style_change_columns(
                top_movers[display_columns],
                ["Performance"],
            ),
            hide_index=True,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
            key="bureau_top_movers_table",
        )

        top_selected_rows = selected_dataframe_rows(
            top_movers_event
        )

        if top_selected_rows:
            selected_top_row = top_movers[display_columns].iloc[
                top_selected_rows[0]
            ]
            selected_top_label = (
                f"Top performer · {selected_top_row['Ticker']} · "
                f"{selected_top_row['Nom']}"
            )
            selected_top_context = metric_context_from_row(
                {
                    **selected_top_row.to_dict(),
                    "Univers": movers_universe,
                    "Période": movers_period_label,
                    "Rang": "Top performer",
                }
            )
            set_bureau_ai_selection(
                selected_top_label,
                selected_top_context,
            )

    with bottom_column:
        st.markdown("#### Flop")
        bottom_movers_event = st.dataframe(
            style_change_columns(
                bottom_movers[display_columns],
                ["Performance"],
            ),
            hide_index=True,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
            key="bureau_bottom_movers_table",
        )

        bottom_selected_rows = selected_dataframe_rows(
            bottom_movers_event
        )

        if bottom_selected_rows:
            selected_bottom_row = bottom_movers[
                display_columns
            ].iloc[
                bottom_selected_rows[0]
            ]
            selected_bottom_label = (
                f"Flop performer · {selected_bottom_row['Ticker']} · "
                f"{selected_bottom_row['Nom']}"
            )
            selected_bottom_context = metric_context_from_row(
                {
                    **selected_bottom_row.to_dict(),
                    "Univers": movers_universe,
                    "Période": movers_period_label,
                    "Rang": "Flop performer",
                }
            )
            set_bureau_ai_selection(
                selected_bottom_label,
                selected_bottom_context,
            )

except Exception as error:
    st.warning(
        f"Market movers indisponibles : {error}"
    )

st.caption(
    "Composants récupérés depuis Wikipédia, cours et performances "
    "calculés avec Yahoo Finance. Les variations sont calculées clôture à "
    f"clôture sur la période sélectionnée : {movers_period_label}."
)

session_ai_label = st.session_state.get(
    "bureau_ai_selected_label"
)
session_ai_context = st.session_state.get(
    "bureau_ai_selected_context"
)

if (
    session_ai_label
    and session_ai_context
    and session_ai_label not in bureau_ai_context_options
):
    bureau_ai_context_options[session_ai_label] = session_ai_context

dashboard_context_parts = [
    "Tableau général actifs:",
    dataframe_preview(
        general_table,
        max_rows=24,
    ),
]

if not display_macro.empty:
    dashboard_context_parts.extend(
        [
            "\nMacro inflation:",
            dataframe_preview(
                display_macro,
                max_rows=18,
            ),
        ]
    )

if not display_labor.empty:
    dashboard_context_parts.extend(
        [
            "\nEmploi US / NFP:",
            dataframe_preview(
                display_labor,
                max_rows=8,
            ),
        ]
    )

if not top_movers.empty:
    dashboard_context_parts.extend(
        [
            f"\nTop performers {movers_universe} "
            f"sur {movers_period_label}:",
            dataframe_preview(
                top_movers[display_columns],
                max_rows=10,
            ),
        ]
    )

if not bottom_movers.empty:
    dashboard_context_parts.extend(
        [
            f"\nFlop performers {movers_universe} "
            f"sur {movers_period_label}:",
            dataframe_preview(
                bottom_movers[display_columns],
                max_rows=10,
            ),
        ]
    )

render_bureau_ai_assistant(
    bureau_ai_context_options,
    "\n".join(dashboard_context_parts),
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

if selected_page == "Data Online":
    execute_embedded_page(
        DATA_ONLINE_SOURCE,
        "flavio_monitor_data_online",
        "embedded_data_online.py",
    )

else:
    execute_embedded_page(
        BUREAU_LARBOU_SOURCE,
        "flavio_monitor_bureau_larbou",
        "embedded_bureau_larbou.py",
    )
