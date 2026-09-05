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

        /* keep Material icon ligatures rendering as icons, not as text */
        [data-testid="stIconMaterial"],
        span.material-icons, span.material-icons-outlined,
        [class*="material-symbols"] {
            font-family: 'Material Symbols Rounded', 'Material Symbols Outlined',
                'Material Icons', 'Material Icons Outlined' !important;
        }

        [data-testid="stSidebarNav"] {
            display: none;
        }

        .stApp {
            background-color: #08080a;
            background-image:
                radial-gradient(55vw 55vw at 12% -5%,
                    rgba(96, 130, 210, 0.10), transparent 60%),
                radial-gradient(50vw 50vw at 105% 25%,
                    rgba(210, 120, 90, 0.07), transparent 55%),
                radial-gradient(45vw 45vw at 50% 115%,
                    rgba(90, 200, 170, 0.06), transparent 60%);
            background-attachment: fixed;
            background-repeat: no-repeat;
        }

        .unified-navigation-title {
            color: #f4f5f7;
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
            background: rgba(255, 255, 255, 0.12);
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
            background: rgba(255, 255, 255, 0.06) !important;
            color: #f4f5f7 !important;
        }
        section[data-testid="stSidebar"] .stButton > button:focus:not(:active) {
            color: #9aa0a6 !important;
        }
        section[data-testid="stSidebar"] .stButton > button[kind="primary"],
        section[data-testid="stSidebar"] .stButton > button[kind="primary"]:focus {
            background: transparent !important;
            color: #f4f5f7 !important;
            font-weight: 700 !important;
            border-left: 2px solid #f4f5f7 !important;
        }
        section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
            background: rgba(255, 255, 255, 0.06) !important;
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
        'Data online · Regime matrix'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="unified-divider"></div>',
        unsafe_allow_html=True,
    )

    if "show_regime_matrix" not in st.session_state:
        st.session_state["show_regime_matrix"] = True
    show_regime_matrix = st.session_state["show_regime_matrix"]

    nav_pages = ["Data Online"]
    if show_regime_matrix:
        nav_pages.append("Regime Matrix")

    for nav_page in nav_pages:
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
    if selected_page not in nav_pages:
        selected_page = "Data Online"

    st.markdown(
        '<div class="unified-divider"></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="unified-navigation-subtitle" '
        'style="margin-bottom:0.35rem;">Modules</div>',
        unsafe_allow_html=True,
    )
    st.toggle(
        "Regime Matrix",
        key="show_regime_matrix",
        help="Activer ou masquer la page Regime Matrix dans le menu.",
    )


# -----------------------------------------------------------------------------
# Barre de navigation en haut de page (toujours visible, même si la barre
# latérale est repliée — utile sur mobile et quand la flèche est introuvable).
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
        .topnav-hint {
            color: #8490a3; font-size: 0.7rem; letter-spacing: 0.16em;
            text-transform: uppercase; margin: 0 0 0.35rem 0;
        }
        div[data-testid="stHorizontalBlock"] .stButton > button {
            border-radius: 999px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown('<div class="topnav-hint">Navigation</div>', unsafe_allow_html=True)

_topnav_cols = st.columns([3] * len(nav_pages) + [4])
for _i, _page in enumerate(nav_pages):
    with _topnav_cols[_i]:
        if st.button(
            _page,
            key=f"topnav_btn_{_page}",
            use_container_width=True,
            type="primary" if selected_page == _page else "secondary",
        ):
            st.session_state["flavio_nav"] = _page
            st.rerun()

st.markdown(
    '<div style="height:1px;background:rgba(255,255,255,0.10);'
    'margin:0.45rem 0 1.1rem 0;"></div>',
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
    .block-container { padding-top: 2.4rem; max-width: 940px; }
    #MainMenu, header, footer { visibility: hidden; }

    .do-title {
        font-size: 1.9rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #f4f5f7;
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
        color: #7c828c;
        margin: 2.1rem 0 0.4rem 0;
    }
    table.do {
        width: 100%;
        border-collapse: collapse;
        border: 1px solid rgba(244, 245, 247, 0.85);
        background: rgba(255, 255, 255, 0.015);
    }
    table.do th {
        font-size: 0.68rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #7c828c;
        padding: 0.45rem 0.6rem;
        text-align: right;
        border-bottom: 1px solid rgba(244, 245, 247, 0.85);
    }
    table.do th.do-name, table.do td.do-name {
        text-align: left;
    }
    table.do td {
        padding: 0.7rem 0.6rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        font-size: 0.95rem;
        color: #f4f5f7;
        text-align: right;
        font-variant-numeric: tabular-nums;
    }
    table.do td.do-name {
        font-weight: 600;
    }
    .do-up { color: #34d399; font-weight: 600; }
    .do-down { color: #f87171; font-weight: 600; }
    .do-flat, .do-muted { color: #7c828c; }
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
'''

if selected_page == "Regime Matrix":
    from regime.ui.dashboard import render as render_regime_matrix

    render_regime_matrix()

else:
    execute_embedded_page(
        DATA_ONLINE_SOURCE,
        "flavio_monitor_data_online",
        "embedded_data_online.py",
    )
