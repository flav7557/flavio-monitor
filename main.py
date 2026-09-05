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
        'Data online · Morning desk · Quant lab'
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
            "Data Online",
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
stamp = now_paris.strftime("%d/%m/%Y %H:%M")

header_left, header_right = st.columns([4, 1])
with header_left:
    st.markdown(
        "<div class='do-title'>Data Online</div>"
        f"<div class='do-sub'>Performance des indices &middot; "
        f"mise à jour {stamp} (Paris) &middot; source Yahoo Finance</div>",
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
            const start = (Date.now() - REPLAY_MINUTES * 60000) / 1000;
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


if selected_page == "Data Online":
    execute_embedded_page(
        DATA_ONLINE_SOURCE,
        "flavio_monitor_data_online",
        "embedded_data_online.py",
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
