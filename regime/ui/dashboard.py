"""Market Regime / Direction Matrix — dashboard page.

Institutional, near-black, minimal. All rendering; zero business logic (the
engine lives in ``regime.engine`` and is imported, never re-implemented here).
"""

from __future__ import annotations

import html
from dataclasses import replace
from typing import List

import pandas as pd
import streamlit as st

from ..config import DEFAULT_CONFIG
from ..engine.classification import regime_direction
from ..engine.explain import display_regime, explain_instrument
from ..engine.models import GroupResult, InstrumentScore
from ..service import compute_regime

STORE_PATH = ".regime_state/commodities.json"

UP = "#3fb950"
DOWN = "#f85149"
FLAT = "#6e7681"
TXT = "#e6edf3"
DIM = "#8b949e"


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def _direction(group) -> str:
    d = regime_direction(group.regime)
    if d == "neutral":
        if group.score <= -8:
            return "bear"
        if group.score >= 8:
            return "bull"
    return d


def _color(direction: str) -> str:
    return {"bull": UP, "bear": DOWN}.get(direction, FLAT)


def _change_glyph(status: str) -> str:
    return {
        "strengthening": "▲ strengthening",
        "weakening": "▼ weakening",
        "newly changed": "• new",
        "pending change": "… pending",
        "unchanged": "— unchanged",
    }.get(status, "—")


def _sparkline(values: List[float], color: str, w: int = 96, h: int = 24) -> str:
    vals = [v for v in (values or []) if v is not None]
    if len(vals) < 2:
        return f"<svg width='{w}' height='{h}'></svg>"
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    n = len(vals)
    pts = []
    for i, v in enumerate(vals):
        x = i / (n - 1) * (w - 2) + 1
        y = h - 1 - (v - lo) / rng * (h - 2)
        pts.append(f"{x:.1f},{y:.1f}")
    return (
        f"<svg width='{w}' height='{h}' viewBox='0 0 {w} {h}' "
        f"preserveAspectRatio='none'><polyline points='{' '.join(pts)}' "
        f"fill='none' stroke='{color}' stroke-width='1.3' opacity='0.85'/></svg>"
    )


def _fmt_price(v) -> str:
    if v is None:
        return "—"
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    if abs(v) >= 1:
        return f"{v:,.2f}"
    return f"{v:.4f}"


def _fmt_pct(v) -> str:
    if v is None:
        return "—"
    return f"{v:+.2f}%"


def _comp(v) -> str:
    if v is None:
        return "<span style='color:#484f58'>·</span>"
    c = UP if v > 0 else DOWN if v < 0 else FLAT
    return f"<span style='color:{c}'>{v:+.0f}</span>"


# --------------------------------------------------------------------------- #
# styling
# --------------------------------------------------------------------------- #
CSS = f"""
<style>
    .rgm {{ color: {TXT}; }}
    .rgm .eyebrow {{
        font-size: 0.72rem; letter-spacing: 0.22em; text-transform: uppercase;
        color: {DIM}; margin: 0 0 0.5rem 0;
    }}
    .rgm .headline {{
        font-size: 3.1rem; font-weight: 700; line-height: 1.0; margin: 0;
        letter-spacing: -0.02em;
    }}
    .rgm .headscore {{ font-size: 1.5rem; font-weight: 600; margin: 0.35rem 0 0 0; }}
    .rgm .headmeta {{ color: {DIM}; font-size: 0.85rem; margin: 0.5rem 0 0 0; }}
    .rgm .warn {{
        border-left: 2px solid #b8860b; background: rgba(184,134,11,0.08);
        color: #d6c07a; padding: 0.5rem 0.8rem; margin: 0.6rem 0;
        font-size: 0.82rem; border-radius: 3px;
    }}
    .rgm table.mx {{ width: 100%; border-collapse: collapse; margin-top: 0.4rem; }}
    .rgm table.mx th {{
        font-size: 0.66rem; letter-spacing: 0.10em; text-transform: uppercase;
        color: {DIM}; font-weight: 600; text-align: right; padding: 0.5rem 0.7rem;
        border-bottom: 1px solid rgba(255,255,255,0.10);
    }}
    .rgm table.mx th.l, .rgm table.mx td.l {{ text-align: left; }}
    .rgm table.mx td {{
        padding: 0.7rem 0.7rem; text-align: right;
        border-bottom: 1px solid rgba(255,255,255,0.05);
        font-variant-numeric: tabular-nums; font-size: 0.92rem;
    }}
    .rgm table.mx tr:hover td {{ background: rgba(255,255,255,0.02); }}
    .rgm .sector-name {{ font-weight: 600; }}
    .rgm .dot {{ display:inline-block; width:7px; height:7px; border-radius:50%;
        margin-right:0.5rem; vertical-align: middle; }}
    .rgm .chg {{ color: {DIM}; font-size: 0.8rem; }}
    .rgm table.inst {{ width: 100%; border-collapse: collapse; }}
    .rgm table.inst th {{
        font-size: 0.62rem; letter-spacing: 0.08em; text-transform: uppercase;
        color: {DIM}; font-weight: 600; text-align: right; padding: 0.35rem 0.5rem;
        border-bottom: 1px solid rgba(255,255,255,0.08);
    }}
    .rgm table.inst th.l, .rgm table.inst td.l {{ text-align: left; }}
    .rgm table.inst td {{
        padding: 0.45rem 0.5rem; text-align: right; font-size: 0.85rem;
        border-bottom: 1px solid rgba(255,255,255,0.04);
        font-variant-numeric: tabular-nums;
    }}
    .rgm .why {{ color: {DIM}; font-size: 0.82rem; margin: 0.5rem 0 0.2rem 0;
        line-height: 1.5; }}
    .rgm .clname {{ color: {DIM}; font-size: 0.7rem; letter-spacing: 0.10em;
        text-transform: uppercase; padding-top: 0.6rem; }}
    section[data-testid="stSidebar"] {{ }}
</style>
"""


# --------------------------------------------------------------------------- #
# data loading (cached)
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=300, show_spinner=False)
def _load(provider: str, timeframe: str, intraday: bool, salt: int):
    cfg = replace(
        DEFAULT_CONFIG, provider=provider,
        primary_timeframe=timeframe, intraday_enabled=intraday,
    )
    return compute_regime(cfg, store_path=STORE_PATH)


# --------------------------------------------------------------------------- #
# rendering blocks
# --------------------------------------------------------------------------- #
def _render_header(result) -> None:
    g = result.global_regime
    d = _direction(g)
    color = _color(d)
    label = display_regime(g).upper()
    conf = g.confidence
    conf_word = "High" if conf >= 75 else "Moderate" if conf >= 50 else "Low"

    st.markdown(
        f"<div class='rgm'>"
        f"<div class='eyebrow'>{html.escape(result.asset_class.upper())} COMPLEX</div>"
        f"<div class='headline' style='color:{color}'>{html.escape(label)}</div>"
        f"<div class='headscore' style='color:{color}'>{g.score:+.0f}</div>"
        f"<div class='headmeta'>{conf_word} confidence · {conf:.0f}% &nbsp;·&nbsp; "
        f"{_change_glyph(g.change_status)} &nbsp;·&nbsp; "
        f"{result.n_eligible}/{result.n_instruments} instruments active</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<div class='rgm why'>{html.escape(g.explanation)}</div>",
                unsafe_allow_html=True)


def _render_warnings(result) -> None:
    for w in result.warnings:
        st.markdown(f"<div class='rgm'><div class='warn'>⚠ {html.escape(w)}</div></div>",
                    unsafe_allow_html=True)


def _render_matrix(result) -> None:
    rows = []
    for s in result.global_regime.children:
        if not isinstance(s, GroupResult):
            continue
        d = _direction(s)
        color = _color(d)
        breadth = (
            f"{max(s.pct_bull, s.pct_bear) * 100:.0f}% {s.dominant}"
            if s.n_active else "no data"
        )
        stale_flag = " ⚠" if not s.data_quality_ok else ""
        rows.append(
            f"<tr>"
            f"<td class='l'><span class='dot' style='background:{color}'></span>"
            f"<span class='sector-name'>{html.escape(s.name)}</span>"
            f"<span class='chg'> ({s.n_active}/{s.n_children} clusters)</span></td>"
            f"<td style='color:{color}'>{html.escape(display_regime(s))}</td>"
            f"<td style='color:{color};font-weight:600'>{s.score:+.0f}</td>"
            f"<td>{html.escape(breadth)}{stale_flag}</td>"
            f"<td>{s.confidence:.0f}%</td>"
            f"<td class='chg'>{_change_glyph(s.change_status)}</td>"
            f"</tr>"
        )
    table = (
        "<div class='rgm'><table class='mx'><thead><tr>"
        "<th class='l'>Sector</th><th>Regime</th><th>Score</th>"
        "<th>Breadth</th><th>Confidence</th><th>Change</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )
    st.markdown(table, unsafe_allow_html=True)


def _instrument_table(cluster: GroupResult) -> str:
    rows = []
    for i in cluster.children:
        if not isinstance(i, InstrumentScore):
            continue
        if not i.eligible:
            why = i.reasons[0] if i.reasons else "no data"
            rows.append(
                f"<tr><td class='l'>{html.escape(i.name)}</td>"
                f"<td colspan='9' class='l' style='color:#6e7681'>excluded — "
                f"{html.escape(why)}</td></tr>"
            )
            continue
        d = regime_direction(i.regime)
        color = _color(d)
        dchg = i.daily_change_pct
        dchg_c = UP if (dchg or 0) > 0 else DOWN if (dchg or 0) < 0 else FLAT
        c = i.components
        spark = _sparkline(i.sparkline, color)
        stale = " ⚠" if i.stale else ""
        rows.append(
            f"<tr>"
            f"<td class='l'>{html.escape(i.name)}{stale}</td>"
            f"<td>{_fmt_price(i.price)}</td>"
            f"<td style='color:{dchg_c}'>{_fmt_pct(dchg)}</td>"
            f"<td style='color:{color};font-weight:600'>{i.score:+.0f}</td>"
            f"<td style='color:{color}'>{html.escape(i.regime)}</td>"
            f"<td>{_comp(c.get('trend'))}</td>"
            f"<td>{_comp(c.get('momentum'))}</td>"
            f"<td>{_comp(c.get('intraday'))}</td>"
            f"<td>{_comp(c.get('breakout'))}</td>"
            f"<td class='chg'>{'' if i.contribution is None else f'{i.contribution:+.1f}'}</td>"
            f"<td>{spark}</td>"
            f"</tr>"
        )
    return (
        "<table class='inst'><thead><tr>"
        "<th class='l'>Instrument</th><th>Price</th><th>Δ Day</th><th>Score</th>"
        "<th>Regime</th><th>Trend</th><th>Mom</th><th>Intra</th><th>Break</th>"
        "<th>Contrib</th><th>Trend 30d</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _render_drilldown(result) -> None:
    st.markdown("<div class='rgm eyebrow' style='margin-top:1.6rem'>"
                "Sector detail</div>", unsafe_allow_html=True)
    for s in result.global_regime.children:
        if not isinstance(s, GroupResult):
            continue
        d = _direction(s)
        head = f"{s.name}   ·   {display_regime(s)}   {s.score:+.0f}   ·   {s.confidence:.0f}%"
        with st.expander(head, expanded=False):
            st.markdown(f"<div class='rgm why'>{html.escape(s.explanation)}</div>",
                        unsafe_allow_html=True)
            for cl in s.children:
                if not isinstance(cl, GroupResult):
                    continue
                st.markdown(
                    f"<div class='rgm'><div class='clname'>{html.escape(cl.name)} "
                    f"· {html.escape(display_regime(cl))} {cl.score:+.0f}</div>"
                    f"{_instrument_table(cl)}</div>",
                    unsafe_allow_html=True,
                )


def _render_methodology(result) -> None:
    cfg = DEFAULT_CONFIG
    with st.expander("Methodology & parameters", expanded=False):
        st.markdown(
            "<div class='rgm why'>Every score is deterministic and traceable: "
            "instrument → cluster → sector → complex. Instrument score = "
            f"{cfg.w_trend:.0%} trend + {cfg.w_momentum:.0%} momentum + "
            f"{cfg.w_intraday:.0%} intraday + {cfg.w_breakout:.0%} breakout "
            "(missing components are dropped and the rest renormalised). "
            "Breadth counts clusters, not raw instruments, so correlated "
            "contracts cannot inflate confirmations. Sector/cluster scores use a "
            "median-based center (4+ children) so one outlier cannot flip a group."
            "</div>",
            unsafe_allow_html=True,
        )
        st.json({
            "provider": result.provider,
            "weights": cfg.component_weights(),
            "ma_periods": [cfg.sma_fast, cfg.sma_slow],
            "momentum_horizons": list(cfg.momentum_horizons),
            "zscore_window": cfg.zscore_window,
            "thresholds": {
                "strong_bull": cfg.t_strong_bull, "bull": cfg.t_bull,
                "bear": cfg.t_bear, "strong_bear": cfg.t_strong_bear,
            },
            "breadth": {
                "bull_pct": cfg.breadth_bull_pct,
                "strong_pct": cfg.breadth_strong_pct,
            },
            "persistence_length": cfg.persistence_length,
            "sector_weights": cfg.sector_weights,
        })


# --------------------------------------------------------------------------- #
# page entry point
# --------------------------------------------------------------------------- #
def render() -> None:
    st.markdown(CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("<div class='rgm eyebrow'>Regime data</div>",
                    unsafe_allow_html=True)
        source = st.selectbox(
            "Source", ["Auto (LSE → Yahoo)", "Yahoo Finance"],
            index=0, label_visibility="collapsed",
        )
        timeframe = st.selectbox("Daily timeframe", ["1d"], index=0)
        intraday = st.toggle("Use intraday impulse", value=True)
        if st.button("Refresh data", use_container_width=True):
            _load.clear()

    provider = "yfinance" if source == "Yahoo Finance" else "lse"

    try:
        salt = int(pd.Timestamp.utcnow().timestamp() // 300)
        result = _load(provider, timeframe, intraday, salt)
    except Exception as exc:  # never crash the whole app
        st.error(f"Regime engine could not load market data: {exc}")
        return

    _render_header(result)
    _render_warnings(result)
    _render_matrix(result)
    _render_drilldown(result)
    _render_methodology(result)

    ts = result.timestamp
    try:
        paris = ts.tz_localize("UTC").tz_convert("Europe/Paris") \
            if ts.tzinfo is None else ts.tz_convert("Europe/Paris")
        stamp = paris.strftime("%d/%m %H:%M")
    except Exception:
        stamp = str(ts)
    st.caption(
        f"Regime engine · {result.asset_class} · source {result.provider} · "
        f"computed {stamp} Paris · deterministic & fully traceable"
    )
