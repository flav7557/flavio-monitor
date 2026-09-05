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
    </style>
    """,
    unsafe_allow_html=True,
)

from regime.ui.dashboard import render as render_regime_matrix


render_regime_matrix()
