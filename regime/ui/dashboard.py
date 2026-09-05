"""Market Regime / Direction Matrix — dashboard page.

Information architecture: three levels of progressive disclosure.
  1. MARKET STATE   — the hero (score + label + regime scale), read in ~2s
  2. SECTOR DRIVERS — compact sector rows + a market map, read in ~10s
  3. UNDERLYING     — sector drill-down and per-instrument component drawers

All calculations come from ``regime.engine`` unchanged; this module only decides
what to show, when, and how. Near-black, typographic hierarchy, no cards.
"""

from __future__ import annotations

import html
import math
from dataclasses import replace
from typing import List, Optional

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from ..config import DEFAULT_CONFIG
from ..engine.classification import regime_direction
from ..engine.models import GroupResult, InstrumentScore
from ..service import compute_regime

STORE_PATH = ".regime_state/commodities.json"

UP = "#3fb950"
DOWN = "#f85149"
FLAT = "#6e7681"
TXT = "#e6edf3"
DIM = "#8b949e"
FAINT = "#484f58"


# --------------------------------------------------------------------------- #
# vocabulary + colours
# --------------------------------------------------------------------------- #
def short_regime(regime: str, score: float) -> str:
    if regime in ("Strong Bullish", "Bullish", "Bearish", "Strong Bearish"):
        return regime
    if score >= 8:
        return "Slight Bullish"
    if score <= -8:
        return "Slight Bearish"
    return "Neutral"


def color_for(score: float) -> str:
    if score >= 8:
        return UP
    if score <= -8:
        return DOWN
    return FLAT


def arrow_for(score: float) -> str:
    if score >= 40:
        return "↑"
    if score >= 15:
        return "↗"
    if score > -15:
        return "→"
    if score > -40:
        return "↘"
    return "↓"


def agreement_of(components: dict) -> str:
    signs = []
    for k in ("trend", "momentum", "intraday", "breakout"):
        v = components.get(k)
        if v is None or abs(v) < 5:
            continue
        signs.append(1 if v > 0 else -1)
    if len(signs) < 2:
        return "—"
    pos = sum(1 for s in signs if s > 0)
    neg = len(signs) - pos
    if pos == 0 or neg == 0:
        return "Aligned"
    if min(pos, neg) / len(signs) <= 0.34:
        return "Mixed"
    return "Divergent"


def _f(score: float, lo: float = 60, span: float = 880) -> float:
    s = max(-100.0, min(100.0, float(score)))
    return lo + (s + 100.0) / 200.0 * span


# --------------------------------------------------------------------------- #
# visual atoms
# --------------------------------------------------------------------------- #
def regime_scale(score: float, labels: bool = True) -> str:
    """The recurring −100…+100 horizontal scale with a marker."""
    x = _f(score)
    col = color_for(score)
    seps = "".join(
        f"<line x1='{_f(s):.0f}' y1='24' x2='{_f(s):.0f}' y2='44' "
        f"stroke='#20242b' stroke-width='1'/>"
        for s in (-40, -20, 20, 40)
    )
    lbls = ""
    if labels:
        band = [("STRONG BEARISH", -70), ("BEARISH", -30), ("NEUTRAL", 0),
                ("BULLISH", 30), ("STRONG BULLISH", 70)]
        lbls = "".join(
            f"<text x='{_f(s):.0f}' y='54' text-anchor='middle' "
            f"font-size='15' letter-spacing='1.5' fill='{FAINT}'>{t}</text>"
            for t, s in band
        )
    h = 60 if labels else 34
    return (
        f"<svg viewBox='0 0 1000 {h}' width='100%' height='auto' "
        f"preserveAspectRatio='xMidYMid meet' style='display:block'>"
        f"<line x1='60' y1='34' x2='940' y2='34' stroke='#20242b' "
        f"stroke-width='2'/>{seps}"
        f"<line x1='{x:.0f}' y1='20' x2='{x:.0f}' y2='48' stroke='{col}' "
        f"stroke-width='2'/>"
        f"<polygon points='{x-7:.0f},16 {x+7:.0f},16 {x:.0f},26' fill='{col}'/>"
        f"{lbls}</svg>"
    )


def mini_scale(score: float, w: int = 220) -> str:
    x = 6 + (max(-100.0, min(100.0, score)) + 100) / 200 * (w - 12)
    col = color_for(score)
    return (
        f"<svg viewBox='0 0 {w} 16' width='{w}' height='16' style='display:block'>"
        f"<line x1='6' y1='8' x2='{w-6}' y2='8' stroke='#20242b' "
        f"stroke-width='2'/>"
        f"<line x1='{w/2:.0f}' y1='3' x2='{w/2:.0f}' y2='13' stroke='#2b3138' "
        f"stroke-width='1'/>"
        f"<circle cx='{x:.1f}' cy='8' r='4' fill='{col}'/></svg>"
    )


def component_bar(value: float, w: int = 240) -> str:
    center = w / 2
    x = 8 + (max(-100.0, min(100.0, value)) + 100) / 200 * (w - 16)
    col = color_for(value)
    x0, x1 = (center, x) if x >= center else (x, center)
    return (
        f"<svg viewBox='0 0 {w} 12' width='{w}' height='12' style='display:block'>"
        f"<line x1='8' y1='6' x2='{w-8}' y2='6' stroke='#1a1e24' "
        f"stroke-width='2'/>"
        f"<line x1='{center:.0f}' y1='1' x2='{center:.0f}' y2='11' "
        f"stroke='#2b3138' stroke-width='1'/>"
        f"<rect x='{x0:.1f}' y='4' width='{max(1,x1-x0):.1f}' height='4' "
        f"rx='2' fill='{col}'/></svg>"
    )


def label_bar(score: float, length: int = 19) -> str:
    """Monospace unicode bar for use inside a Streamlit expander label."""
    s = max(-100.0, min(100.0, score))
    pos = round((s + 100) / 200 * (length - 1))
    chars = ["─"] * length
    chars[length // 2] = "┼"
    chars[pos] = "●"
    return "".join(chars)


# --------------------------------------------------------------------------- #
# styling
# --------------------------------------------------------------------------- #
CSS = f"""
<style>
    .rg {{ color: {TXT}; }}
    .rg .eyebrow {{ font-size:0.68rem; letter-spacing:0.22em; text-transform:uppercase;
        color:{DIM}; margin:1.8rem 0 0.6rem 0; }}
    .rg .hero-name {{ font-size:0.8rem; letter-spacing:0.28em; text-transform:uppercase;
        color:{DIM}; margin:0; }}
    .rg .hero-score {{ font-size:4.2rem; font-weight:700; line-height:0.95;
        letter-spacing:-0.03em; margin:0.2rem 0 0 0; }}
    .rg .hero-label {{ font-size:1.4rem; font-weight:600; margin:0.1rem 0 0 0; }}
    .rg .hero-meta {{ color:{DIM}; font-size:0.85rem; margin:0.7rem 0 0 0; }}
    .rg .lowconf {{ display:inline-block; font-size:0.66rem; letter-spacing:0.14em;
        color:#d6a13a; border:1px solid rgba(214,161,58,0.4); border-radius:3px;
        padding:0.05rem 0.4rem; margin-left:0.5rem; vertical-align:middle; }}
    .rg .stale {{ color:{FAINT}; font-size:0.78rem; margin:0.35rem 0 0 0; }}
    .rg .scalewrap {{ max-width:620px; margin:1.0rem 0 0 0; }}

    .rg table.sec {{ width:100%; border-collapse:collapse; }}
    .rg table.sec td {{ padding:0.85rem 0.4rem; border-bottom:1px solid rgba(255,255,255,0.05);
        vertical-align:middle; }}
    .rg table.sec td.s-name {{ font-size:1.0rem; font-weight:600; }}
    .rg table.sec td.s-score {{ font-size:1.5rem; font-weight:700; text-align:right;
        font-variant-numeric:tabular-nums; width:80px; }}
    .rg table.sec td.s-reg {{ color:{DIM}; font-size:0.85rem; width:130px; }}
    .rg table.sec td.s-arrow {{ font-size:1.1rem; width:28px; text-align:center; }}
    .rg table.sec td.s-bar {{ width:240px; }}
    .rg .mgrp {{ margin:0.1rem 0 0.5rem 0; }}
    .rg .mgrp .mlab {{ display:inline-block; width:110px; font-size:0.64rem;
        letter-spacing:0.14em; text-transform:uppercase; color:{DIM};
        vertical-align:top; padding-top:0.5rem; }}

    .rg .map-sector {{ font-size:0.66rem; letter-spacing:0.16em; text-transform:uppercase;
        color:{DIM}; margin:1.1rem 0 0.4rem 0; }}
    .rg .map-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(96px,1fr));
        gap:6px; }}
    .rg .cell {{ border:1px solid rgba(255,255,255,0.06); border-radius:4px;
        padding:0.45rem 0.55rem; background:#0d0d0f; }}
    .rg .cell .c-name {{ font-size:0.66rem; color:{DIM}; white-space:nowrap;
        overflow:hidden; text-overflow:ellipsis; }}
    .rg .cell .c-score {{ font-size:1.0rem; font-weight:700; font-variant-numeric:tabular-nums; }}

    .rg .cl-head {{ font-size:0.72rem; letter-spacing:0.06em; color:{DIM};
        margin:0.9rem 0 0.2rem 0; }}
    .rg .drawer {{ margin:0.1rem 0 0.4rem 0; }}
    .rg .drow {{ display:flex; align-items:center; gap:0.6rem; margin:0.25rem 0; }}
    .rg .dlab {{ width:78px; font-size:0.78rem; color:{DIM}; }}
    .rg .dval {{ width:42px; font-size:0.82rem; text-align:right;
        font-variant-numeric:tabular-nums; }}
    .rg .kv {{ color:{DIM}; font-size:0.82rem; margin-top:0.5rem; }}
    .rg .foot {{ color:{FAINT}; font-size:0.72rem; margin-top:2rem; }}
    .rg .agree {{ font-size:0.7rem; letter-spacing:0.06em; }}
    .rg .newchip {{ font-size:0.6rem; letter-spacing:0.12em; color:#5aa0ff;
        border:1px solid rgba(90,160,255,0.4); border-radius:3px;
        padding:0.05rem 0.35rem; margin-left:0.5rem; vertical-align:middle; }}
    .rg table.map {{ width:100%; border-collapse:collapse; }}
    .rg table.map td {{ vertical-align:top; padding:0.35rem 0.4rem 0.9rem 0; border:0; }}
    .rg td.mlabel {{ font-size:0.64rem; letter-spacing:0.14em; text-transform:uppercase;
        color:{DIM}; white-space:nowrap; width:118px; padding-top:0.55rem; }}
    .rg span.mcell {{ display:inline-block; width:88px; margin:0 6px 6px 0;
        padding:0.4rem 0.5rem; border:1px solid rgba(255,255,255,0.06);
        border-radius:4px; vertical-align:top; }}
    .rg span.mcell .mn {{ display:block; font-size:0.62rem; color:{DIM};
        white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
    .rg span.mcell .ms {{ display:block; font-size:0.98rem; font-weight:700;
        font-variant-numeric:tabular-nums; }}
    .rg table.term2 {{ width:100%; border-collapse:collapse; }}
    .rg table.term2 th {{ font-size:0.62rem; letter-spacing:0.1em;
        text-transform:uppercase; color:{DIM}; font-weight:600; text-align:right;
        padding:0.4rem 0.8rem; border-bottom:1px solid rgba(255,255,255,0.12); }}
    .rg table.term2 th.l {{ text-align:left; }}
    .rg table.term2 td {{ padding:0.42rem 0.8rem; text-align:right;
        border-bottom:1px solid rgba(255,255,255,0.04);
        font-variant-numeric:tabular-nums; font-size:0.88rem; color:#c9d1d9; }}
    .rg table.term2 td.l {{ text-align:left; }}
    .rg table.term2 tr.cat td {{ background:rgba(255,255,255,0.025);
        border-top:1px solid rgba(255,255,255,0.09);
        border-bottom:1px solid rgba(255,255,255,0.09);
        padding-top:0.6rem; padding-bottom:0.6rem; }}
    .rg table.term2 .catname {{ font-size:0.72rem; letter-spacing:0.12em;
        text-transform:uppercase; color:#e6edf3; font-weight:700; }}
    .rg table.term2 .tagcell {{ font-weight:700; letter-spacing:0.5px;
        font-size:0.78rem; }}
    .rg .quote-board {{ border:1px solid rgba(255,255,255,0.08); border-radius:5px;
        background:rgba(255,255,255,0.018); overflow:hidden; }}
    .rg table.quotes {{ width:100%; border-collapse:collapse; table-layout:fixed; }}
    .rg table.quotes th {{ color:{DIM}; font-size:0.56rem; letter-spacing:0.08em;
        text-transform:uppercase; font-weight:600; text-align:right;
        padding:0.42rem 0.34rem; border-bottom:1px solid rgba(255,255,255,0.08); }}
    .rg table.quotes th.l {{ text-align:left; }}
    .rg table.quotes th.cat {{ width:15%; }}
    .rg table.quotes th.asset {{ width:22%; }}
    .rg table.quotes td {{ color:#c9d1d9; font-size:0.74rem; text-align:right;
        padding:0.46rem 0.34rem; border-bottom:1px solid rgba(255,255,255,0.14);
        font-variant-numeric:tabular-nums; white-space:nowrap; overflow:hidden;
        text-overflow:ellipsis; }}
    .rg table.quotes td.l {{ text-align:left; color:#e6edf3; font-weight:650; }}
    .rg table.quotes td.cat {{ color:{DIM}; font-size:0.66rem; letter-spacing:0.08em;
        text-transform:uppercase; font-weight:700; }}
    .rg table.quotes td.sym {{ color:{FAINT}; font-size:0.66rem; }}
    .rg table.quotes tr.group-start td {{ border-top:1px solid rgba(255,255,255,0.28); }}
    .rg table.quotes tr:last-child td {{ border-bottom:0; }}
    div[data-testid="stHorizontalBlock"] .stButton > button {{ border-radius:999px; }}
</style>
"""


# --------------------------------------------------------------------------- #
# data loading (cached)
# --------------------------------------------------------------------------- #
@st.cache_resource(ttl=300, show_spinner=False)
def _load(provider: str, timeframe: str, intraday: bool, salt: int):
    cfg = replace(DEFAULT_CONFIG, provider=provider,
                  primary_timeframe=timeframe, intraday_enabled=intraday,
                  allow_yf_fallback=False)
    return compute_regime(cfg, store_path=STORE_PATH)


# --------------------------------------------------------------------------- #
# blocks
# --------------------------------------------------------------------------- #
def _all_instruments(g: GroupResult) -> List[InstrumentScore]:
    out = []
    for c in g.children:
        if isinstance(c, InstrumentScore):
            out.append(c)
        elif isinstance(c, GroupResult):
            out.extend(_all_instruments(c))
    return out


def _stale_note(result) -> Optional[str]:
    insts = [i for i in _all_instruments(result.global_regime) if i.eligible]
    if not insts:
        return None
    stale = sum(1 for i in insts if i.stale)
    if stale == 0:
        return None
    if stale == len(insts):
        return "Market closed · quotes may be stale"
    return f"{stale} / {len(insts)} quotes stale"


def _render_hero(result) -> None:
    g = result.global_regime
    col = color_for(g.score)
    label = short_regime(g.regime, g.score).upper()
    mp = max(g.pct_bull, g.pct_bear)
    if mp < 0.55:
        breadth = "Mixed breadth"
    else:
        breadth = f"{mp:.0%} {'bullish' if g.dominant == 'bull' else 'bearish'} breadth"

    low = g.confidence < 35
    low_html = "<span class='lowconf'>LOW CONFIDENCE</span>" if low else ""

    stale = _stale_note(result)
    stale_html = (f"<div class='stale'>{html.escape(stale)}</div>"
                  if stale else "")
    st.markdown(
        "<div class='rg'>"
        f"<div class='hero-name'>{html.escape(result.asset_class)}</div>"
        f"<div class='hero-score' style='color:{col}'>{g.score:+.0f}</div>"
        f"<div class='hero-label' style='color:{col}'>{html.escape(label)}"
        f"{low_html}</div>"
        f"<div class='scalewrap'>{regime_scale(g.score, labels=True)}</div>"
        f"<div class='hero-meta'>Confidence {g.confidence:.0f}% · "
        f"{breadth} · {result.n_eligible} active</div>"
        f"{stale_html}</div>",
        unsafe_allow_html=True,
    )
    # verbose commentary hidden behind an interaction
    with st.popover("Why?"):
        st.write(g.explanation)

    # only the provider-fallback note survives as a subtle line
    for w in result.warnings:
        if "LSE_API_KEY" in w or "fallback" in w.lower():
            st.markdown(f"<div class='rg'><div class='stale'>ℹ {html.escape(w)}"
                        f"</div></div>", unsafe_allow_html=True)
            break


IFRAME_CSS = """
*{box-sizing:border-box}
body{margin:0;background:transparent;color:#e6edf3;
  font-family:'Century Gothic','Questrial','URW Gothic','Avenir',sans-serif;}
.eb{font-size:11px;letter-spacing:3px;text-transform:uppercase;color:#8b949e;
  margin:0 0 8px 0;}
.eb.mt{margin-top:26px;}
table.sec{width:100%;border-collapse:collapse;}
table.sec td{padding:12px 6px;border-bottom:1px solid rgba(255,255,255,0.05);
  vertical-align:middle;}
td.s-name{font-size:15px;font-weight:600;}
td.s-score{font-size:24px;font-weight:700;text-align:right;width:70px;
  font-variant-numeric:tabular-nums;}
td.s-reg{color:#8b949e;font-size:13px;width:120px;padding-left:16px;}
td.s-bar{width:230px;}
td.s-arrow{text-align:center;width:26px;font-size:17px;}
.chip{font-size:9px;letter-spacing:1.5px;border-radius:3px;padding:1px 5px;
  margin-left:8px;vertical-align:middle;}
.chip.low{color:#d6a13a;border:1px solid rgba(214,161,58,0.4);}
.chip.new{color:#5aa0ff;border:1px solid rgba(90,160,255,0.4);}
.ms-sec{font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#8b949e;
  margin:16px 0 6px 0;}
.ms-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(108px,1fr));
  gap:6px;}
.ms-cell{border:1px solid rgba(255,255,255,0.06);border-radius:4px;padding:7px 9px;
  background:#0d0d0f;}
.ms-n{font-size:10px;color:#8b949e;white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis;}
.ms-s{font-size:15px;font-weight:700;font-variant-numeric:tabular-nums;}
"""


def _render_visual(result) -> None:
    """Sector overview + market map in a sanitizer-free iframe (full CSS)."""
    sectors = [s for s in result.global_regime.children
               if isinstance(s, GroupResult)]

    sec_rows = []
    for s in sectors:
        col = color_for(s.score)
        chips = ""
        if s.n_active and s.confidence < 35:
            chips += "<span class='chip low'>LOW</span>"
        if s.change_status == "newly changed":
            chips += "<span class='chip new'>NEW REGIME</span>"
        sec_rows.append(
            "<tr>"
            f"<td class='s-name'>{html.escape(s.name)}{chips}</td>"
            f"<td class='s-score' style='color:{col}'>{s.score:+.0f}</td>"
            f"<td class='s-reg'>{html.escape(short_regime(s.regime, s.score))}</td>"
            f"<td class='s-bar'>{mini_scale(s.score, 220)}</td>"
            f"<td class='s-arrow' style='color:{col}'>{arrow_for(s.score)}</td>"
            "</tr>"
        )

    map_html = []
    map_height = 0
    for s in sectors:
        cells = []
        for inst in _all_instruments(s):
            if not inst.eligible:
                continue
            sc = inst.score
            col = color_for(sc)
            alpha = min(0.22, abs(sc) / 100 * 0.24)
            tint = (f"rgba(63,185,80,{alpha:.3f})" if sc >= 8
                    else f"rgba(248,81,73,{alpha:.3f})" if sc <= -8
                    else "#0d0d0f")
            cells.append(
                f"<div class='ms-cell' style='background:{tint}'>"
                f"<div class='ms-n'>{html.escape(inst.name)}</div>"
                f"<div class='ms-s' style='color:{col}'>{sc:+.0f}</div></div>"
            )
        if cells:
            map_html.append(
                f"<div class='ms-sec'>{html.escape(s.name)}</div>"
                f"<div class='ms-grid'>{''.join(cells)}</div>"
            )
            map_height += 24 + math.ceil(len(cells) / 5) * 64

    doc = (
        f"<style>{IFRAME_CSS}</style>"
        "<div class='eb'>Sector regime</div>"
        f"<table class='sec'><tbody>{''.join(sec_rows)}</tbody></table>"
        "<div class='eb mt'>Market map</div>"
        f"{''.join(map_html)}"
    )
    height = 40 + len(sec_rows) * 50 + 60 + map_height + 30
    components.html(doc, height=height, scrolling=False)


# --------------------------------------------------------------------------- #
# live terminal
# --------------------------------------------------------------------------- #
TERMINAL_CSS = """
*{box-sizing:border-box}
body{margin:0;background:transparent;color:#e6edf3;
  font-family:ui-monospace,'SFMono-Regular',Menlo,Consolas,monospace;}
.term{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}
.col{border:1px solid rgba(255,255,255,0.07);border-radius:5px;background:#0b0b0d;}
.col h3{margin:0;padding:9px 10px;font-size:10px;letter-spacing:2px;
  text-transform:uppercase;color:#8b949e;
  border-bottom:1px solid rgba(255,255,255,0.09);
  display:flex;justify-content:space-between;align-items:center;gap:8px;}
.col h3 .cat{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.col h3 .hgrp{display:flex;align-items:baseline;gap:8px;flex-shrink:0;}
.col h3 .st{font-weight:700;font-size:11px;}
.col h3 .hp{font-weight:700;font-size:12px;letter-spacing:0;
  font-variant-numeric:tabular-nums;}
.row{display:flex;align-items:center;gap:8px;padding:5px 10px;
  border-bottom:1px solid rgba(255,255,255,0.04);font-size:12px;}
.row:last-child{border-bottom:0;}
.nm{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#c9d1d9;}
.px{width:70px;text-align:right;color:#e6edf3;font-variant-numeric:tabular-nums;}
.chg{width:60px;text-align:right;font-variant-numeric:tabular-nums;font-size:11px;}
.tag{width:46px;text-align:right;font-weight:700;letter-spacing:0.5px;}
.bull{color:#3fb950}.bear{color:#f85149}.neut{color:#6e7681}
"""


def _tag(score: float):
    if score >= 15:
        return "BULL", "bull"
    if score <= -15:
        return "BEAR", "bear"
    return "NEUT", "neut"


MARKET_BOARD_TARGETS = [
    ("Énergie", "Brent", "commodities", ("BRENT", "UKOIL", "BCO", "BZ")),
    ("Énergie", "WTI", "commodities", ("WTI", "USOIL", "CL")),
    ("Énergie", "Natural Gas", "commodities", ("NATURAL GAS", "NAT GAS", "NG")),
    ("Énergie", "Gasoline", "commodities", ("GASOLINE", "RBOB", "RB")),
    ("Énergie", "Heating Oil", "commodities", ("HEATING OIL", "GASOIL", "HO")),
    ("Métaux précieux", "Gold", "commodities", ("XAU/USD", "GOLD", "GC", "XAU")),
    ("Métaux précieux", "Silver", "commodities", ("XAG/USD", "SILVER", "SI", "XAG")),
    ("Métaux précieux", "Platinum", "commodities", ("XPT/USD", "PLATINUM", "PL", "XPT")),
    ("Métaux précieux", "Palladium", "commodities", ("XPD/USD", "PALLADIUM", "PA", "XPD")),
    ("Indices", "S&P 500", "indices", ("SPX", "S&P 500", "US500", "SP500")),
    ("Indices", "Nasdaq 100", "indices", ("NDX", "NASDAQ 100", "US100")),
    ("Indices", "Dow Jones", "indices", ("DJI", "DOW JONES", "US30")),
    ("Indices", "Euro Stoxx 50", "indices", ("STOXX50E", "EURO STOXX 50", "EU50")),
    ("Indices", "CAC 40", "indices", ("CAC 40", "FCHI", "FR40")),
    ("Indices", "DAX", "indices", ("DAX", "GDAXI", "DE40")),
    ("Forex", "EUR/USD", "forex", ("EUR/USD",)),
    ("Forex", "GBP/USD", "forex", ("GBP/USD",)),
    ("Forex", "USD/JPY", "forex", ("USD/JPY",)),
    ("Forex", "USD/CHF", "forex", ("USD/CHF",)),
    ("Forex", "USD/CAD", "forex", ("USD/CAD",)),
    ("Forex", "AUD/USD", "forex", ("AUD/USD",)),
    ("Forex", "NZD/USD", "forex", ("NZD/USD",)),
]


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


def _resolve_board_rows(catalog: list[dict]) -> list[dict]:
    rows = []
    by_category = {}
    for item in catalog:
        key = str(item.get("category") or "").lower()
        by_category.setdefault(key, []).append(item)

    for category, display_name, catalog_name, candidates in MARKET_BOARD_TARGETS:
        pool = by_category.get(catalog_name.lower(), [])
        scored = sorted(
            ((_match_score(item, candidates), item) for item in pool),
            key=lambda pair: pair[0],
            reverse=True,
        )
        item = scored[0][1] if scored and scored[0][0][0] > 0 else None
        rows.append({
            "category": category,
            "name": display_name,
            "symbol": item.get("symbol") if item else None,
            "dataset": item.get("dataset") if item else None,
        })
    return rows


def _quote_from_lse_candles(api_key: str, symbol: str, dataset: Optional[str]) -> dict:
    from ..data.provider import normalize_candles

    from lse import LSE

    client = LSE(api_key=api_key, timeout=15)
    try:
        try:
            daily = normalize_candles(
                client.candles(
                    symbol,
                    timeframe="1d",
                    limit=2,
                    order="desc",
                    dataset=dataset,
                )
            )
        except Exception:
            daily = pd.DataFrame()

        try:
            minute = normalize_candles(
                client.candles(
                    symbol,
                    timeframe="1m",
                    limit=1,
                    order="desc",
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
    if not minute.empty:
        live = _as_float(minute["close"].iloc[-1]) or live

    day = None
    if live is not None and previous not in (None, 0):
        day = (live / previous - 1) * 100

    return {"previous": previous, "live": live, "day": day}


def _stream_lse_prices(api_key: str, symbols: tuple[str, ...], seconds: float = 3.0) -> dict:
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
            tick = events.get(timeout=0.2)
        except queue.Empty:
            continue
        price = _as_float(getattr(tick, "price", None))
        symbol = getattr(tick, "symbol", None)
        if symbol:
            ticks[symbol] = {"live": price}

    client = client_box.get("client")
    if client is not None:
        try:
            client.disconnect()
        except Exception:
            pass
    return ticks


@st.cache_data(ttl=10, show_spinner=False)
def _load_market_board_lse(salt: int) -> list[dict]:
    import os
    from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed

    from lse import LSE

    api_key = os.environ.get("LSE_API_KEY")
    if not api_key:
        raise RuntimeError("LSE_API_KEY manquant : Regime Matrix utilise uniquement l'API LSE.")

    client = LSE(api_key=api_key, timeout=30)
    try:
        rows = _resolve_board_rows(client.catalog())
        resolved = [row for row in rows if row["symbol"]]
        quotes = {}

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(
                    _quote_from_lse_candles,
                    api_key,
                    row["symbol"],
                    row["dataset"],
                ): row["symbol"]
                for row in resolved
            }
            try:
                for future in as_completed(futures, timeout=12):
                    symbol = futures[future]
                    try:
                        quotes[symbol] = future.result()
                    except Exception:
                        quotes[symbol] = {}
            except TimeoutError:
                pass

        stream_quotes = _stream_lse_prices(
            api_key,
            tuple(row["symbol"] for row in resolved),
            seconds=3.0,
        )
        for row in rows:
            symbol = row["symbol"]
            quote = quotes.get(symbol, {}) if symbol else {}
            tick = stream_quotes.get(symbol, {}) if symbol else {}
            if tick.get("live") is not None:
                quote["live"] = tick["live"]
            row.update(quote)
        return rows
    finally:
        try:
            client.disconnect()
        except Exception:
            pass


def _fmt_px(v, decimals: Optional[int] = None) -> str:
    if v is None:
        return "—"
    if decimals is not None:
        return f"{v:,.{decimals}f}"
    if abs(v) >= 1000:
        return f"{v:,.1f}"
    if abs(v) >= 1:
        return f"{v:,.2f}"
    return f"{v:.4f}"


def _live_change(inst, live: dict):
    """Live daily performance %: live price vs the pipeline's prior close."""
    live_px = live.get(inst.symbol, inst.price)
    dcp = inst.daily_change_pct
    prev = None
    if inst.price is not None and dcp is not None and (1 + dcp / 100) != 0:
        prev = inst.price / (1 + dcp / 100)
    if live_px is not None and prev:
        return (live_px / prev - 1) * 100
    return dcp


@st.cache_data(ttl=10, show_spinner=False)
def _load_live(provider: str, intraday: bool, symbols: tuple, salt: int) -> dict:
    from ..service import fetch_live_prices
    cfg = replace(
        DEFAULT_CONFIG,
        provider=provider,
        intraday_enabled=intraday,
        allow_yf_fallback=False,
    )
    return fetch_live_prices(cfg, list(symbols))


def _render_status(result, live: dict) -> None:
    g = result.global_regime
    _, cls = _tag(g.score)
    col = {"bull": UP, "bear": DOWN, "neut": FLAT}[cls]
    live_on = len(live) > 0
    live_lbl = ("<span style='color:#3fb950'>● LIVE</span>" if live_on
                else "<span style='color:#8b949e'>○ delayed</span>")
    now = pd.Timestamp.now(tz="Europe/Paris")
    perfs = [c for c in (_live_change(i, live)
             for i in _all_instruments(g) if i.eligible) if c is not None]
    gperf = sum(perfs) / len(perfs) if perfs else None
    gperf_c = UP if (gperf or 0) > 0 else DOWN if (gperf or 0) < 0 else DIM
    gperf_s = "—" if gperf is None else f"{gperf:+.2f}%"
    st.markdown(
        f"<div class='rg' style='display:flex;align-items:baseline;gap:14px;"
        f"flex-wrap:wrap;margin-bottom:0.4rem'>"
        f"<span style='font-size:0.8rem;letter-spacing:0.24em;color:{DIM}'>"
        f"{html.escape(result.asset_class.upper())}</span>"
        f"<span style='font-size:1.6rem;font-weight:700;color:{col}'>{g.score:+.0f}</span>"
        f"<span style='font-size:1rem;font-weight:600;color:{col}'>"
        f"{html.escape(short_regime(g.regime, g.score))}</span>"
        f"<span style='font-size:1rem;font-weight:700;color:{gperf_c}'>{gperf_s}</span>"
        f"<span style='color:{DIM};font-size:0.82rem'>conf {g.confidence:.0f}% · "
        f"{result.n_eligible} active · {live_lbl}"
        f"<span style='color:{DIM}'> · maj {now.strftime('%H:%M:%S')} Paris · "
        f"auto-refresh 10s</span></span></div>",
        unsafe_allow_html=True,
    )


def _cell_color(v) -> str:
    return UP if (v or 0) > 0 else DOWN if (v or 0) < 0 else DIM


def _fmt_pct(v) -> str:
    if v is None:
        return "—"
    return f"{v:+.2f}%"


def _quote_decimals(category: str, symbol: Optional[str]) -> Optional[int]:
    if category != "Forex":
        return None
    return 2 if symbol and "JPY" in symbol else 4


def _render_market_board(rows: list[dict]) -> None:
    body = [
        "<table class='quotes'><thead><tr>"
        "<th class='l cat'>Catégorie</th><th class='l asset'>Actif</th>"
        "<th class='l'>Symbole LSE</th><th>Prix</th><th>Direct</th>"
        "<th>Jour</th></tr></thead><tbody>"
    ]
    previous_category = None
    for row in rows:
        category = row["category"]
        symbol = row.get("symbol")
        previous = row.get("previous")
        live = row.get("live")
        day = row.get("day")
        day_col = _cell_color(day)
        decimals = _quote_decimals(category, symbol)
        row_class = (
            " class='group-start'"
            if previous_category and category != previous_category
            else ""
        )
        body.append(
            f"<tr{row_class}>"
            f"<td class='l cat'>{html.escape(category)}</td>"
            f"<td class='l'>{html.escape(row['name'])}</td>"
            f"<td class='l sym'>{html.escape(symbol or 'Non trouvé')}</td>"
            f"<td>{_fmt_px(previous, decimals)}</td>"
            f"<td>{_fmt_px(live, decimals)}</td>"
            f"<td style='color:{day_col};font-weight:700'>{_fmt_pct(day)}</td>"
            "</tr>"
        )
        previous_category = category
    body.append("</tbody></table>")
    st.markdown(
        f"<div class='rg'><div class='quote-board'>{''.join(body)}</div></div>",
        unsafe_allow_html=True,
    )


def _render_terminal(result, live: dict) -> None:
    """One native table (updates in place on each fragment tick — no reload)."""
    body = [
        "<thead><tr><th class='l'>Instrument</th><th>Prix</th>"
        "<th>Perf jour</th><th>Sentiment</th></tr></thead><tbody>"
    ]
    for s in result.global_regime.children:
        if not isinstance(s, GroupResult):
            continue
        insts = [i for i in _all_instruments(s) if i.eligible]
        if not insts:
            continue
        stag, scls = _tag(s.score)
        scol = {"bull": UP, "bear": DOWN, "neut": FLAT}[scls]
        perfs = []
        inst_rows = []
        for i in insts:
            live_px = live.get(i.symbol, i.price)
            chg = _live_change(i, live)
            if chg is not None:
                perfs.append(chg)
            itag, icls = _tag(i.score)
            icol = {"bull": UP, "bear": DOWN, "neut": FLAT}[icls]
            chg_s = "—" if chg is None else f"{chg:+.2f}%"
            inst_rows.append(
                f"<tr><td class='l'>{html.escape(i.name)}</td>"
                f"<td>{_fmt_px(live_px)}</td>"
                f"<td style='color:{_cell_color(chg)}'>{chg_s}</td>"
                f"<td class='tagcell' style='color:{icol}'>{itag}</td></tr>"
            )
        sperf = sum(perfs) / len(perfs) if perfs else None
        sperf_s = "—" if sperf is None else f"{sperf:+.2f}%"
        body.append(
            f"<tr class='cat'><td class='l' colspan='2'>"
            f"<span class='catname'>{html.escape(s.name)}</span></td>"
            f"<td style='color:{_cell_color(sperf)};font-weight:700'>{sperf_s}</td>"
            f"<td class='tagcell' style='color:{scol}'>{stag}</td></tr>"
        )
        body.extend(inst_rows)
    body.append("</tbody>")
    st.markdown(
        f"<div class='rg'><table class='term2'>{''.join(body)}</table></div>",
        unsafe_allow_html=True,
    )


@st.fragment(run_every=10)
def _terminal_fragment(result, provider: str, intraday: bool) -> None:
    now = pd.Timestamp.utcnow()
    symbols = tuple(
        i.symbol for i in _all_instruments(result.global_regime) if i.eligible
    )
    live = _load_live(provider, intraday, symbols, int(now.timestamp() // 10))
    quotes = _load_market_board_lse(int(now.timestamp() // 10))
    _render_status(result, live)
    _render_market_board(quotes)
    for w in result.warnings:
        if "LSE_API_KEY" in w or "fallback" in w.lower():
            st.markdown(
                f"<div class='rg'><div class='stale'>ℹ {html.escape(w)}</div></div>",
                unsafe_allow_html=True)
            break


def _render_instrument_drawer(inst: InstrumentScore) -> None:
    comps = inst.components
    rows = []
    for key, lab in (("trend", "Trend"), ("momentum", "Momentum"),
                     ("intraday", "Intraday"), ("breakout", "Breakout")):
        v = comps.get(key)
        if v is None:
            continue
        col = color_for(v)
        rows.append(
            f"<div class='drow'><div class='dlab'>{lab}</div>"
            f"<div class='dval' style='color:{col}'>{v:+.0f}</div>"
            f"{component_bar(v)}</div>"
        )
    price = "—" if inst.price is None else (
        f"{inst.price:,.2f}" if abs(inst.price) >= 1 else f"{inst.price:.4f}")
    day = "—" if inst.daily_change_pct is None else f"{inst.daily_change_pct:+.2f}%"
    contrib = "—" if inst.contribution is None else f"{inst.contribution:+.1f}"
    st.markdown(
        f"<div class='rg drawer'>{''.join(rows)}"
        f"<div class='kv'>Price {price} · Today {day} · "
        f"Contribution {contrib} · Agreement {agreement_of(comps)}</div></div>",
        unsafe_allow_html=True,
    )


def _render_sector_detail(result) -> None:
    sectors = [s for s in result.global_regime.children
               if isinstance(s, GroupResult)]
    if not sectors:
        return
    st.markdown("<div class='rg'><div class='eyebrow'>Sector detail</div></div>",
                unsafe_allow_html=True)

    names = [s.name for s in sectors]
    if st.session_state.get("rg_sector") not in names:
        st.session_state["rg_sector"] = names[0]

    cols = st.columns(len(names) + 1)
    for i, nm in enumerate(names):
        with cols[i]:
            active = st.session_state["rg_sector"] == nm
            if st.button(nm, key=f"rg_sec_{nm}", use_container_width=True,
                         type="primary" if active else "secondary"):
                st.session_state["rg_sector"] = nm
                st.rerun()

    sector = next(s for s in sectors if s.name == st.session_state["rg_sector"])
    col = color_for(sector.score)
    st.markdown(
        f"<div class='rg' style='margin-top:0.6rem'>"
        f"<span style='font-size:1.1rem;font-weight:600'>{html.escape(sector.name)}"
        f"</span> <span style='color:{col};font-weight:700;font-size:1.1rem'>"
        f"{sector.score:+.0f}</span> "
        f"<span style='color:{DIM}'>· {html.escape(short_regime(sector.regime, sector.score))}"
        f" · confidence {sector.confidence:.0f}%</span></div>",
        unsafe_allow_html=True,
    )

    for cl in sector.children:
        if not isinstance(cl, GroupResult):
            continue
        ccol = color_for(cl.score)
        st.markdown(
            f"<div class='rg'><div class='cl-head'>{html.escape(cl.name)} "
            f"<span style='color:{ccol}'>{cl.score:+.0f}</span></div></div>",
            unsafe_allow_html=True,
        )
        for inst in cl.children:
            if not isinstance(inst, InstrumentScore):
                continue
            if not inst.eligible:
                st.markdown(
                    f"<div class='rg' style='color:{FAINT};font-size:0.82rem;"
                    f"margin:0.2rem 0 0.2rem 1rem'>{html.escape(inst.name)} — excluded"
                    f"</div>", unsafe_allow_html=True)
                continue
            day = ("" if inst.daily_change_pct is None
                   else f"{inst.daily_change_pct:+.2f}%")
            agree = agreement_of(inst.components)
            stale = " ⚠" if inst.stale and _stale_note(result) and \
                "/" in (_stale_note(result) or "") else ""
            lab = (f"{inst.name}   `{label_bar(inst.score)}`   {inst.score:+.0f}   "
                   f"· {agree}   · {day}{stale}")
            with st.expander(lab, expanded=False):
                _render_instrument_drawer(inst)


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
def render() -> None:
    st.markdown(CSS, unsafe_allow_html=True)

    provider = "lse"
    intraday = True
    show_map = False

    try:
        salt = int(pd.Timestamp.utcnow().timestamp() // 300)
        result = _load(provider, "1d", intraday, salt)
    except Exception as exc:
        st.error(f"Impossible de charger Régime Matrix depuis l'API LSE : {exc}")
        return

    _terminal_fragment(result, provider, intraday)

    if show_map:
        _render_visual(result)

    ts = result.timestamp
    try:
        paris = (ts.tz_localize("UTC") if ts.tzinfo is None else ts) \
            .tz_convert("Europe/Paris")
        stamp = paris.strftime("%H:%M")
    except Exception:
        stamp = str(ts)
    prov = "LSE" if result.provider == "lse" else "Yahoo Finance"
    st.markdown(
        f"<div class='rg'><div class='foot'>{prov} · Updated {stamp} Paris · "
        f"{result.n_instruments} instruments</div></div>",
        unsafe_allow_html=True,
    )
