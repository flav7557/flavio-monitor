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
    div[data-testid="stHorizontalBlock"] .stButton > button {{ border-radius:999px; }}
</style>
"""


# --------------------------------------------------------------------------- #
# data loading (cached)
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=300, show_spinner=False)
def _load(provider: str, timeframe: str, intraday: bool, salt: int):
    cfg = replace(DEFAULT_CONFIG, provider=provider,
                  primary_timeframe=timeframe, intraday_enabled=intraday)
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


def _fmt_px(v) -> str:
    if v is None:
        return "—"
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
    cfg = replace(DEFAULT_CONFIG, provider=provider, intraday_enabled=intraday)
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


def _render_terminal(result, live: dict) -> None:
    cols = []
    max_rows = 1
    for s in result.global_regime.children:
        if not isinstance(s, GroupResult):
            continue
        stag, scls = _tag(s.score)
        insts = [i for i in _all_instruments(s) if i.eligible]
        max_rows = max(max_rows, len(insts))
        rows = []
        sec_perfs = []
        for i in insts:
            live_px = live.get(i.symbol, i.price)
            chg = _live_change(i, live)
            if chg is not None:
                sec_perfs.append(chg)
            chg_c = "bull" if (chg or 0) > 0 else "bear" if (chg or 0) < 0 else "neut"
            chg_s = "—" if chg is None else f"{chg:+.2f}%"
            itag, icls = _tag(i.score)
            stale = " ·" if i.stale else ""
            rows.append(
                f"<div class='row'><span class='nm'>{html.escape(i.name)}{stale}</span>"
                f"<span class='px'>{_fmt_px(live_px)}</span>"
                f"<span class='chg {chg_c}'>{chg_s}</span>"
                f"<span class='tag {icls}'>{itag}</span></div>"
            )
        sperf = sum(sec_perfs) / len(sec_perfs) if sec_perfs else None
        sperf_c = "bull" if (sperf or 0) > 0 else "bear" if (sperf or 0) < 0 else "neut"
        sperf_s = "—" if sperf is None else f"{sperf:+.2f}%"
        cols.append(
            f"<div class='col'><h3><span class='cat'>{html.escape(s.name)}</span>"
            f"<span class='hgrp'><span class='st {scls}'>{stag}</span>"
            f"<span class='hp {sperf_c}'>{sperf_s}</span></span></h3>"
            f"{''.join(rows)}</div>"
        )
    doc = f"<style>{TERMINAL_CSS}</style><div class='term'>{''.join(cols)}</div>"
    height = 52 + max_rows * 29 + 40
    components.html(doc, height=height, scrolling=False)


@st.fragment(run_every=10)
def _terminal_fragment(provider: str, intraday: bool) -> None:
    now = pd.Timestamp.utcnow()
    result = _load(provider, "1d", intraday, int(now.timestamp() // 300))
    symbols = tuple(
        i.symbol for i in _all_instruments(result.global_regime) if i.eligible
    )
    live = _load_live(provider, intraday, symbols, int(now.timestamp() // 10))
    _render_status(result, live)
    _render_terminal(result, live)
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


def _render_methodology(result) -> None:
    cfg = DEFAULT_CONFIG
    with st.expander("Methodology", expanded=False):
        st.markdown(
            f"""
**Instrument score** &nbsp; −100 … +100
- {cfg.w_trend:.0%} Trend · {cfg.w_momentum:.0%} Momentum · \
{cfg.w_intraday:.0%} Intraday · {cfg.w_breakout:.0%} Breakout
- Missing components are dropped and the rest renormalised.

**Trend** MA{cfg.sma_fast} / MA{cfg.sma_slow}, slope, ATR-normalised
**Momentum** {' / '.join(map(str, cfg.momentum_horizons))} periods, \
{cfg.zscore_window}-period Z-score (volatility-adjusted)
**Breakout** {cfg.donchian_period}-period Donchian channel

**Regime thresholds**
- Strong Bullish > +{cfg.t_strong_bull:.0f} · Bullish > +{cfg.t_bull:.0f}
- Neutral {cfg.t_bear:.0f} → +{cfg.t_bull:.0f}
- Bearish < {cfg.t_bear:.0f} · Strong Bearish < {cfg.t_strong_bear:.0f}

**Aggregation** clusters are the confirmation unit (correlated instruments do \
not inflate breadth); groups use a median-based center (4+ children) so one \
outlier cannot flip a sector.

**Persistence** {cfg.persistence_length} observations before a regime switch.
""")
        if st.toggle("Developer / raw config", value=False, key="rg_devcfg"):
            st.json({
                "provider": result.provider,
                "weights": cfg.component_weights(),
                "thresholds": {
                    "strong_bull": cfg.t_strong_bull, "bull": cfg.t_bull,
                    "bear": cfg.t_bear, "strong_bear": cfg.t_strong_bear},
                "sector_weights": cfg.sector_weights,
            })


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
def render() -> None:
    st.markdown(CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("<div class='rg eyebrow' style='margin-top:0'>Regime data</div>",
                    unsafe_allow_html=True)
        source = st.selectbox("Source", ["Auto (LSE → Yahoo)", "Yahoo Finance"],
                              index=0, label_visibility="collapsed")
        intraday = st.toggle("Use intraday impulse", value=True)
        if st.button("Refresh data", use_container_width=True):
            _load.clear()

    provider = "yfinance" if source == "Yahoo Finance" else "lse"

    with st.sidebar:
        show_map = st.toggle("Show market map & scale", value=False,
                             key="rg_showmap")

    try:
        salt = int(pd.Timestamp.utcnow().timestamp() // 300)
        result = _load(provider, "1d", intraday, salt)
    except Exception as exc:
        st.error(f"Regime engine could not load market data: {exc}")
        return

    # Live terminal — sector columns, auto-refreshing every 30s
    _terminal_fragment(provider, intraday)

    if show_map:
        _render_visual(result)

    _render_sector_detail(result)
    _render_methodology(result)

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
