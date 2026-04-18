import streamlit as st
import numpy as np
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from lib.market_data import SYMBOLS, get_candles, get_quotes
from lib.ict_analysis import (
    get_session, find_equal_hl, detect_gap_fib,
    find_imbalances, find_fvg, pearson, returns, who_leads
)

def make_chart(key: str, price: float, dec: int) -> go.Figure:
    cfg = SYMBOLS[key]
    df  = get_candles(cfg["yahoo"], "15m", "5d")
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data", x=0.5, y=0.5, showarrow=False,
                           font=dict(color="#9ca3af", size=16))
        fig.update_layout(paper_bgcolor="#080810", plot_bgcolor="#080810", height=480)
        return fig

    df15 = df
    df1h = get_candles(cfg["yahoo"], "1h", "15d")

    levels = find_equal_hl(df15, "15m", price) + find_equal_hl(df1h, "1h", price)
    levels.sort(key=lambda x: x["dist_pct"])
    levels = levels[:8]

    fvgs = find_fvg(df15, "15m", price) + find_fvg(df1h, "1h", price)
    fvgs.sort(key=lambda x: x["dist_pct"])
    fvgs = fvgs[:6]

    fig = go.Figure()

    # FVG shading (behind candles)
    for f in fvgs:
        color = "rgba(34,197,94,0.08)" if f["type"] == "bull" else "rgba(239,68,68,0.08)"
        border = "rgba(34,197,94,0.3)" if f["type"] == "bull" else "rgba(239,68,68,0.3)"
        fig.add_hrect(y0=f["lo"], y1=f["hi"],
                      fillcolor=color, line=dict(color=border, width=1), layer="below")

    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        increasing=dict(fillcolor="#22c55e", line=dict(color="#22c55e", width=1)),
        decreasing=dict(fillcolor="#ef4444", line=dict(color="#ef4444", width=1)),
        name=cfg["label"], showlegend=False,
    ))

    # EQH/EQL lines
    for lv in levels:
        col = "#ef4444" if lv["type"] == "EQH" else "#22c55e"
        fig.add_hline(y=lv["price"], line=dict(color=col, width=1, dash="dot"),
                      annotation_text=f"{lv['type']} {lv['timeframe']}",
                      annotation_font=dict(color=col, size=10),
                      annotation_position="right")

    # Current price line
    fig.add_hline(y=price, line=dict(color="#f59e0b", width=1.5, dash="dash"))

    fig.update_layout(
        height=480,
        paper_bgcolor="#080810",
        plot_bgcolor="#0d0d1a",
        margin=dict(l=10, r=80, t=10, b=10),
        xaxis=dict(
            showgrid=True, gridcolor="#1e1e32", color="#6b7280",
            rangeslider=dict(visible=False),
            type="category", tickangle=-45,
            nticks=10,
        ),
        yaxis=dict(showgrid=True, gridcolor="#1e1e32", color="#6b7280",
                   tickformat=f".{dec}f", side="right"),
        hoverlabel=dict(bgcolor="#0f0f1a", font_color="#e2e2f0"),
    )
    return fig

st.set_page_config(
    page_title="ICT Dina Anchor",
    page_icon="anchor",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Auto-refresh every 60s ────────────────────────────────────────────────────
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60_000, key="refresh")
except ImportError:
    pass

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .block-container { padding-top: 1rem; padding-bottom: 1rem; }
  .stTabs [data-baseweb="tab-list"] { gap: 2px; }
  .stTabs [data-baseweb="tab"] {
    padding: 8px 22px; border-radius: 6px 6px 0 0;
    font-weight: 600; font-size: 13px;
  }
  .metric-card {
    background: #0f0f1a; border: 1px solid #1e1e32;
    border-radius: 10px; padding: 10px 14px; margin-bottom: 6px;
  }
  .level-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 4px 8px; border-radius: 5px; margin-bottom: 2px; font-size: 12px;
  }
  .level-above { background: #ef444412; border: 1px solid #ef444430; }
  .level-below { background: #22c55e12; border: 1px solid #22c55e30; }
  .level-current { background: #ffffff12; border: 1px solid #ffffff30;
                   text-align:center; padding: 4px 8px; border-radius: 5px;
                   margin: 4px 0; font-weight: 700; font-size: 13px; }
  .fvg-bull { background: #22c55e0d; border: 1px solid #22c55e25;
              border-radius: 5px; padding: 4px 8px; margin-bottom: 2px; font-size: 12px; }
  .fvg-bear { background: #ef44440d; border: 1px solid #ef444425;
              border-radius: 5px; padding: 4px 8px; margin-bottom: 2px; font-size: 12px; }
  .tag { padding: 1px 5px; border-radius: 3px; font-size: 10px; font-weight: 700; }
  .tag-eqh { background:#ef444420; color:#ef4444; }
  .tag-eql { background:#22c55e20; color:#22c55e; }
  .tag-fvg-bull { background:#22c55e20; color:#22c55e; }
  .tag-fvg-bear { background:#ef444420; color:#ef4444; }
  .tag-bull { background:#22c55e20; color:#22c55e; }
  .tag-bear { background:#ef444420; color:#ef4444; }
  .chart-levels-panel {
    background: #0a0a14; border: 1px solid #1e1e32; border-top: none;
    border-radius: 0 0 10px 10px; padding: 8px 10px;
  }
  .levels-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
  .section-label {
    font-size: 10px; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #6b7280; margin-bottom: 4px;
  }
  .cor-card { background: #0f0f1a; border: 1px solid #1e1e32;
              border-radius: 8px; padding: 12px; margin-bottom: 10px; }
  .gap-card { background: #f59e0b08; border: 1px solid #f59e0b30;
              border-radius: 8px; padding: 12px; margin-bottom: 10px; }
  h1,h2,h3 { margin-top: 0 !important; }
</style>
""", unsafe_allow_html=True)

# ── Data fetch ────────────────────────────────────────────────────────────────
session = get_session()
quotes  = get_quotes()

# ── Header ────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns([2, 3, 3, 2])

with c1:
    st.markdown("## ICT Dina Anchor")
    st.caption("Gold · Silver · US100 · US30 · Oil")

with c2:
    border_col = session["color"]
    st.markdown(f"""
    <div class="metric-card" style="border-color:{border_col}50">
      <div style="color:{border_col}; font-weight:700; font-size:14px">{session['label']}</div>
      <div style="font-size:12px; color:#9ca3af; margin-top:2px">{session['desc']}</div>
    </div>""", unsafe_allow_html=True)

with c3:
    mins = session["next_mins"]
    time_str = f"{mins}m" if mins < 60 else f"{mins//60}h {mins%60}m"
    st.markdown(f"""
    <div class="metric-card">
      <div style="color:#f59e0b; font-weight:700; font-size:13px">{session['next_label']}</div>
      <div style="font-size:12px; color:#9ca3af">in {time_str}</div>
    </div>""", unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="metric-card" style="text-align:center">
      <div style="font-size:10px; color:#6b7280; letter-spacing:.05em">NY TIME</div>
      <div style="font-size:22px; font-weight:700; font-family:monospace">{session['ny_time']}</div>
    </div>""", unsafe_allow_html=True)

st.divider()

# ── Price Strip ───────────────────────────────────────────────────────────────
inst_order = ["GOLD", "SILVER", "US100", "US30", "OIL"]
cols = st.columns(5)
for i, key in enumerate(inst_order):
    q   = quotes.get(key, {})
    cfg = SYMBOLS[key]
    p   = q.get("price", 0)
    pct = q.get("pct", 0)
    chg = q.get("change", 0)
    color = "#22c55e" if pct >= 0 else "#ef4444"
    sign  = "+" if pct >= 0 else ""
    dec   = cfg["decimals"]
    with cols[i]:
        st.markdown(f"""
        <div class="metric-card" style="text-align:center">
          <div style="font-size:11px; color:#9ca3af; font-weight:700; letter-spacing:.05em">{cfg['label']}</div>
          <div style="font-size:18px; font-weight:700; font-family:monospace">{p:.{dec}f}</div>
          <div style="font-size:12px; color:{color}">{sign}{chg:.{dec}f} ({sign}{pct:.2f}%)</div>
        </div>""", unsafe_allow_html=True)

st.divider()

# ── Helper: render levels+FVG panel ──────────────────────────────────────────

def render_levels_fvg(key: str, price: float, dec: int):
    """Compact levels + FVG panel shown under each chart."""
    df15 = get_candles(SYMBOLS[key]["yahoo"], "15m", "5d")
    df1h = get_candles(SYMBOLS[key]["yahoo"], "1h",  "15d")

    levels = (find_equal_hl(df15, "15m", price) + find_equal_hl(df1h, "1h", price))
    levels.sort(key=lambda x: x["dist_pct"])
    levels = levels[:6]

    fvgs = (find_fvg(df15, "15m", price) + find_fvg(df1h, "1h", price))
    fvgs.sort(key=lambda x: x["dist_pct"])
    fvgs = fvgs[:6]

    above_liq = sorted([l for l in levels if l["is_above"]],  key=lambda x: x["price"])
    below_liq = sorted([l for l in levels if not l["is_above"]], key=lambda x: -x["price"])
    above_fvg = sorted([f for f in fvgs if f["is_above"]],  key=lambda x: x["lo"])
    below_fvg = sorted([f for f in fvgs if not f["is_above"]], key=lambda x: -x["hi"])

    def liq_rows(items, css_class, tag_cls, sign):
        html = ""
        for l in items:
            t = f" x{l['touches']}" if l["touches"] > 2 else ""
            html += f"""<div class="level-row {css_class}">
              <span><span class="tag {tag_cls}">{l['type']}</span>
              &nbsp;<b style="font-family:monospace">{l['price']:.{dec}f}</b>
              <span style="color:#4b5563;font-size:10px"> {l['timeframe']}{t}</span></span>
              <span style="color:#6b7280;font-size:11px">{sign}{l['dist_pct']:.2f}%</span>
            </div>"""
        return html

    def fvg_rows(items, css_class, tag_cls, sign):
        html = ""
        for f in items:
            html += f"""<div class="{css_class}">
              <div style="display:flex;justify-content:space-between;align-items:center">
                <span><span class="tag {tag_cls}">{'B.FVG' if f['type']=='bull' else 'S.FVG'}</span>
                &nbsp;<b style="font-family:monospace">{f['mid']:.{dec}f}</b>
                <span style="color:#4b5563;font-size:10px"> {f['timeframe']}</span></span>
                <span style="color:#6b7280;font-size:11px">{sign}{f['dist_pct']:.2f}%</span>
              </div>
              <div style="color:#374151;font-size:10px">{f['lo']:.{dec}f} – {f['hi']:.{dec}f}</div>
            </div>"""
        return html

    liq_html = (liq_rows(above_liq, "level-above", "tag-eqh", "+") +
                f'<div class="level-current">▶ {price:.{dec}f}</div>' +
                liq_rows(below_liq, "level-below", "tag-eql", "-"))

    fvg_html = (fvg_rows(above_fvg, "fvg-bear", "tag-fvg-bear", "+") +
                f'<div class="level-current">▶ {price:.{dec}f}</div>' +
                fvg_rows(below_fvg, "fvg-bull", "tag-fvg-bull", "-"))

    if not levels and not fvgs:
        liq_html = "<p style='color:#374151;font-size:12px'>No levels detected</p>"
        fvg_html = "<p style='color:#374151;font-size:12px'>No FVGs detected</p>"

    st.markdown(f"""
    <div class="chart-levels-panel">
      <div class="levels-grid">
        <div>
          <div class="section-label">Liquidity Levels (EQH / EQL)</div>
          {liq_html}
        </div>
        <div>
          <div class="section-label">Fair Value Gaps (FVG)</div>
          {fvg_html}
        </div>
      </div>
    </div>""", unsafe_allow_html=True)


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_charts, tab_liq, tab_gaps, tab_cor, tab_imb = st.tabs([
    "Charts", "Liquidity", "Gaps + Fib", "Correlations", "Imbalances"
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — CHARTS  (Plotly 15m candles + EQH/EQL + FVG overlaid)
# ─────────────────────────────────────────────────────────────────────────────
with tab_charts:
    col_left, col_right = st.columns(2)
    for idx, key in enumerate(inst_order):
        cfg   = SYMBOLS[key]
        q     = quotes.get(key, {})
        price = q.get("price", 0)
        dec   = cfg["decimals"]

        with (col_left if idx % 2 == 0 else col_right):
            st.markdown(f"**{cfg['label']}** — 15m")
            if price > 0:
                st.plotly_chart(make_chart(key, price, dec),
                                use_container_width=True, config={"displayModeBar": False})
                render_levels_fvg(key, price, dec)
            else:
                st.warning("No price data")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — LIQUIDITY
# ─────────────────────────────────────────────────────────────────────────────
with tab_liq:
    st.info(
        "**Equal Highs (EQH) / Equal Lows (EQL) — Liquidity Pools**  \n"
        "Before **8:00am NY**: mark equal H/L on 5m/15m/1h — these are buy/sell-side liquidity pools.  \n"
        "Tapped in the **8:30–9:30am news-to-open window**, or attacked after 10am (Silver Bullet / 2022 model).  \n"
        "Red EQH above = sell-side (longs get hunted).  Green EQL below = buy-side (shorts get hunted)."
    )
    cols = st.columns(3)
    for idx, key in enumerate(inst_order):
        cfg   = SYMBOLS[key]
        q     = quotes.get(key, {})
        price = q.get("price", 0)
        dec   = cfg["decimals"]

        with cols[idx % 3]:
            st.markdown(f"**{cfg['label']}**")
            if price == 0:
                st.warning("No price data")
                continue

            df15 = get_candles(cfg["yahoo"], "15m", "5d")
            df1h = get_candles(cfg["yahoo"], "1h",  "30d")
            levels = find_equal_hl(df15, "15m", price) + find_equal_hl(df1h, "1h", price)
            levels.sort(key=lambda x: x["dist_pct"])
            levels = levels[:8]

            above = sorted([l for l in levels if l["is_above"]],  key=lambda x: x["price"])
            below = sorted([l for l in levels if not l["is_above"]], key=lambda x: -x["price"])

            html = ""
            for l in above:
                t = f" x{l['touches']}" if l["touches"] > 2 else ""
                html += f"""<div class="level-row level-above">
                  <span><span class="tag tag-eqh">{l['type']}</span>&nbsp;
                  <b style="font-family:monospace">{l['price']:.{dec}f}</b>
                  <small style="color:#4b5563"> {l['timeframe']}{t}</small></span>
                  <span style="color:#6b7280;font-size:11px">+{l['dist_pct']:.2f}%</span>
                </div>"""
            html += f'<div class="level-current">▶ {price:.{dec}f} current</div>'
            for l in below:
                t = f" x{l['touches']}" if l["touches"] > 2 else ""
                html += f"""<div class="level-row level-below">
                  <span><span class="tag tag-eql">{l['type']}</span>&nbsp;
                  <b style="font-family:monospace">{l['price']:.{dec}f}</b>
                  <small style="color:#4b5563"> {l['timeframe']}{t}</small></span>
                  <span style="color:#6b7280;font-size:11px">-{l['dist_pct']:.2f}%</span>
                </div>"""
            if not levels:
                html = "<p style='color:#6b7280;font-size:12px'>No equal H/L detected</p>"
            st.markdown(html, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — GAPS + FIB
# ─────────────────────────────────────────────────────────────────────────────
with tab_gaps:
    st.info(
        "**RTH/ETH Gap + 0.5 Fibonacci**  \n"
        "Prior day **ETH close (4:15pm NY)** vs today's **RTH open (9:30am NY)**.  \n"
        "Plot fib from lower to higher price — **the 0.5 fib fills in the first hour of RTH opening.**  \n"
        "5-day zones act as strong support/resistance and FVGs going forward."
    )
    col1, col2 = st.columns(2)
    for colidx, key in enumerate(["US100", "US30"]):
        cfg   = SYMBOLS[key]
        q     = quotes.get(key, {})
        price = q.get("price", 0)
        dec   = cfg["decimals"]

        with (col1 if colidx == 0 else col2):
            st.markdown(f"**{cfg['label']} — Gap Fib Zones**")
            daily = get_candles(cfg["yahoo"], "1d",  "10d")
            intra = get_candles(cfg["yahoo"], "15m", "5d")
            gaps  = detect_gap_fib(daily, intra)

            if not gaps:
                st.warning("No gap detected (market may be closed or gap < 0.05%)")
            else:
                for g in gaps:
                    dist = abs(price - g["fib50"]) / price * 100 if price else 0
                    filled_badge = "FILLED" if g["filled"] else f"{dist:.2f}% away"
                    dir_color = "#22c55e" if g["direction"] == "up" else "#ef4444"
                    dir_label = "Gap Up" if g["direction"] == "up" else "Gap Down"
                    opacity = "opacity:0.45;" if g["filled"] else ""
                    st.markdown(f"""
                    <div class="gap-card" style="{opacity}">
                      <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                        <b style="color:#f59e0b">{g['date']}</b>
                        <span>
                          <span style="background:{dir_color}20;color:{dir_color};padding:2px 7px;border-radius:4px;font-size:11px;font-weight:700">{dir_label}</span>
                          &nbsp;<span style="background:#ffffff10;color:#9ca3af;padding:2px 7px;border-radius:4px;font-size:11px">{filled_badge}</span>
                        </span>
                      </div>
                      <div style="font-size:13px;line-height:2.0">
                        <div style="display:flex;justify-content:space-between"><span style="color:#6b7280">ETH Close</span><b style="font-family:monospace">{g['eth_close']:.{dec}f}</b></div>
                        <div style="display:flex;justify-content:space-between"><span style="color:#6b7280">RTH Open</span><b style="font-family:monospace">{g['rth_open']:.{dec}f}</b></div>
                        <div style="display:flex;justify-content:space-between"><span style="color:#6b7280">Fib 0.382</span><b style="font-family:monospace">{g['fib382']:.{dec}f}</b></div>
                        <div style="display:flex;justify-content:space-between;background:#f59e0b18;padding:2px 6px;border-radius:4px">
                          <span style="color:#f59e0b;font-weight:700">Fib 0.500 (target)</span>
                          <b style="font-family:monospace;color:#f59e0b">{g['fib50']:.{dec}f}</b>
                        </div>
                        <div style="display:flex;justify-content:space-between"><span style="color:#6b7280">Fib 0.618</span><b style="font-family:monospace">{g['fib618']:.{dec}f}</b></div>
                      </div>
                      <div style="font-size:11px;color:#374151;margin-top:6px">Gap: {g['gap_size']:.{dec}f} pts</div>
                    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — CORRELATIONS
# ─────────────────────────────────────────────────────────────────────────────
with tab_cor:
    st.info(
        "**Cross-Asset Correlations** (hourly returns, last 5 days)  \n"
        "Gold & Silver move together — watch for divergence as an early signal.  \n"
        "Oil follows DXY **directly** (strong dollar = strong oil) — opposite to metals.  \n"
        "Correlation: +1.0 = perfect positive · 0 = none · -1.0 = perfect inverse"
    )

    with st.spinner("Loading..."):
        dfs = {}
        for k in ["GOLD", "SILVER", "OIL", "DXY"]:
            df = get_candles(SYMBOLS[k]["yahoo"], "1h", "5d")
            if not df.empty:
                dfs[k] = df["Close"].values

    def cor_card(label, r, note, leading=""):
        bar_pct = int((r + 1) / 2 * 100)
        bar_color = "#22c55e" if r > 0.3 else "#ef4444" if r < -0.3 else "#f59e0b"
        r_color = "#22c55e" if r > 0 else "#ef4444"
        sign = "+" if r > 0 else ""
        lead_html = f"<div style='font-size:12px;color:#f59e0b;margin-bottom:4px'>{leading}</div>" if leading else ""
        st.markdown(f"""
        <div class="cor-card">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <b style="font-size:14px">{label}</b>
            <span style="font-family:monospace;font-size:22px;font-weight:700;color:{r_color}">{sign}{r:.2f}</span>
          </div>
          <div style="background:#1e1e3a;border-radius:3px;height:5px;margin-bottom:8px;position:relative;overflow:hidden">
            <div style="position:absolute;top:0;height:100%;width:{abs(bar_pct-50)}%;
                        {'right:0;left:auto' if r < 0 else 'left:50%'};
                        background:{bar_color};border-radius:3px"></div>
            <div style="position:absolute;top:0;left:50%;width:1px;height:100%;background:#374151"></div>
          </div>
          {lead_html}
          <div style="font-size:12px;color:#6b7280">{note}</div>
        </div>""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if "GOLD" in dfs and "SILVER" in dfs:
            n = min(len(dfs["GOLD"]), len(dfs["SILVER"]))
            gr, sr = returns(dfs["GOLD"][-n:]), returns(dfs["SILVER"][-n:])
            r    = pearson(gr, sr)
            lead = who_leads(gr, sr)
            lead_str = "Gold leading Silver" if lead == "first leads" else "Silver leading Gold" if lead == "second leads" else "Moving in sync"
            cor_card("Gold vs Silver", r, "Move in conjunction — divergence = early directional signal", lead_str)
        if "GOLD" in dfs and "DXY" in dfs:
            n = min(len(dfs["GOLD"]), len(dfs["DXY"]))
            r = pearson(returns(dfs["GOLD"][-n:]), returns(dfs["DXY"][-n:]))
            cor_card("Gold vs DXY", r, "Gold moves inverse to DXY — strong dollar = bearish metals")

    with col2:
        if "OIL" in dfs and "DXY" in dfs:
            n = min(len(dfs["OIL"]), len(dfs["DXY"]))
            r = pearson(returns(dfs["OIL"][-n:]), returns(dfs["DXY"][-n:]))
            cor_card("Oil vs DXY", r, "Oil follows DXY directly — strong dollar = bullish oil (not inverse!)")
        if "GOLD" in dfs and "OIL" in dfs:
            n = min(len(dfs["GOLD"]), len(dfs["OIL"]))
            r = pearson(returns(dfs["GOLD"][-n:]), returns(dfs["OIL"][-n:]))
            cor_card("Gold vs Oil", r, "Gold and Oil typically move opposite to each other")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — IMBALANCES
# ─────────────────────────────────────────────────────────────────────────────
with tab_imb:
    st.info(
        "**Volume Imbalances (Body Gaps)**  \n"
        "Gaps between candle bodies (open/close, not wicks) on the 1h chart — act as magnets.  \n"
        "Price will return to fill them. Especially reliable in **Gold and Oil**.  \n"
        "Oil also respects trend lines very well — combine these zones with trend structure."
    )

    imb_order = ["GOLD", "OIL", "SILVER", "US100", "US30"]
    cols = st.columns(3)
    for idx, key in enumerate(imb_order[:3]):
        cfg   = SYMBOLS[key]
        q     = quotes.get(key, {})
        price = q.get("price", 0)
        dec   = cfg["decimals"]
        priority = key in ("GOLD", "OIL")

        with cols[idx]:
            badge = " — HIGH PRIORITY" if priority else ""
            st.markdown(f"**{cfg['label']}{badge}**")
            df1h = get_candles(cfg["yahoo"], "1h", "10d")
            imbs = find_imbalances(df1h, "1h", price)
            if not imbs:
                st.markdown("<p style='color:#6b7280;font-size:12px'>No unfilled imbalances nearby</p>", unsafe_allow_html=True)
            else:
                html = ""
                for imp in imbs:
                    bull = imp["direction"] == "bull"
                    tag_cls = "tag-bull" if bull else "tag-bear"
                    lbl = "BULL VI" if bull else "BEAR VI"
                    bg  = "#22c55e10" if bull else "#ef444410"
                    bdr = "#22c55e25" if bull else "#ef444425"
                    d   = f"+{imp['dist_pct']:.2f}%" if imp["is_above"] else f"-{imp['dist_pct']:.2f}%"
                    html += f"""<div style="background:{bg};border:1px solid {bdr};border-radius:5px;padding:7px 9px;margin-bottom:5px;font-size:12px">
                      <div style="display:flex;justify-content:space-between">
                        <span><span class="tag {tag_cls}">{lbl}</span>&nbsp;<b style="font-family:monospace">{imp['price']:.{dec}f}</b> <small style="color:#4b5563">{imp['timeframe']}</small></span>
                        <span style="color:#6b7280;font-size:11px">{d}</span>
                      </div>
                      <div style="color:#374151;font-size:10px;margin-top:2px">{imp['lo']:.{dec}f} – {imp['hi']:.{dec}f} · {imp['size_pct']:.3f}%</div>
                    </div>"""
                st.markdown(html, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    for colidx, key in enumerate(["US100", "US30"]):
        cfg   = SYMBOLS[key]
        q     = quotes.get(key, {})
        price = q.get("price", 0)
        dec   = cfg["decimals"]
        with (col1 if colidx == 0 else col2):
            st.markdown(f"**{cfg['label']}**")
            df1h = get_candles(cfg["yahoo"], "1h", "10d")
            imbs = find_imbalances(df1h, "1h", price)
            if not imbs:
                st.markdown("<p style='color:#6b7280;font-size:12px'>No unfilled imbalances nearby</p>", unsafe_allow_html=True)
            else:
                html = ""
                for imp in imbs:
                    bull = imp["direction"] == "bull"
                    tag_cls = "tag-bull" if bull else "tag-bear"
                    lbl = "BULL VI" if bull else "BEAR VI"
                    bg  = "#22c55e10" if bull else "#ef444410"
                    bdr = "#22c55e25" if bull else "#ef444425"
                    d   = f"+{imp['dist_pct']:.2f}%" if imp["is_above"] else f"-{imp['dist_pct']:.2f}%"
                    html += f"""<div style="background:{bg};border:1px solid {bdr};border-radius:5px;padding:7px 9px;margin-bottom:5px;font-size:12px">
                      <div style="display:flex;justify-content:space-between">
                        <span><span class="tag {tag_cls}">{lbl}</span>&nbsp;<b style="font-family:monospace">{imp['price']:.{dec}f}</b> <small style="color:#4b5563">{imp['timeframe']}</small></span>
                        <span style="color:#6b7280;font-size:11px">{d}</span>
                      </div>
                      <div style="color:#374151;font-size:10px;margin-top:2px">{imp['lo']:.{dec}f} – {imp['hi']:.{dec}f} · {imp['size_pct']:.3f}%</div>
                    </div>"""
                st.markdown(html, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("ICT Dina Anchor · Refreshes every 60s · Educational use only · Not financial advice")
