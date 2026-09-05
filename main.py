"""Flavio Monitor Streamlit entrypoint."""

from __future__ import annotations

import streamlit as st


st.set_page_config(
    page_title="Flavio Monitor",
    layout="wide",
    initial_sidebar_state="collapsed",
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

        [data-testid="stIconMaterial"],
        span.material-icons, span.material-icons-outlined,
        [class*="material-symbols"] {
            font-family: 'Material Symbols Rounded', 'Material Symbols Outlined',
                'Material Icons', 'Material Icons Outlined' !important;
        }

        [data-testid="stSidebarNav"] {
            display: none;
        }

        section[data-testid="stSidebar"],
        [data-testid="collapsedControl"] {
            display: none !important;
        }

        section[data-testid="stSidebar"] + div {
            margin-left: 0 !important;
        }

        [data-testid="stElementContainer"],
        .element-container {
            opacity: 1 !important;
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

        div[data-testid="stHorizontalBlock"] .stButton > button {
            border-radius: 0 !important;
            border-color: rgba(255, 255, 255, 0.18) !important;
            background: rgba(255, 255, 255, 0.02) !important;
            color: #8b949e !important;
            font-size: 0.72rem !important;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        div[data-testid="stHorizontalBlock"] .stButton > button[kind="primary"] {
            color: #f4f5f7 !important;
            border-color: rgba(255, 255, 255, 0.42) !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

from regime.ui.dashboard import render as render_regime_matrix
from regime.ui.live_pilot import render as render_live_pilot


PAGES = {
    "Pilotage Live": render_live_pilot,
    "Regime Matrix": render_regime_matrix,
}

selected_page = st.session_state.get("flavio_page", "Pilotage Live")
if selected_page not in PAGES:
    selected_page = "Pilotage Live"

nav_cols = st.columns([1, 1, 7])
for index, page_name in enumerate(PAGES):
    with nav_cols[index]:
        if st.button(
            page_name,
            key=f"nav_{page_name}",
            type="primary" if selected_page == page_name else "secondary",
            use_container_width=True,
        ):
            st.session_state["flavio_page"] = page_name
            st.rerun()

PAGES[selected_page]()
