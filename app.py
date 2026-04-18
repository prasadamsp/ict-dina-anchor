import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from lib.market_data import SYMBOLS, TV_SYMBOLS, get_candles, get_quotes
from lib.ict_analysis import (
    get_session, find_equal_hl, detect_gap_fib,
    find_imbalances, pearson, returns, who_leads
)

st.set_page_config(
    page_title="ICT Dina Anchor",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .block-container { padding-top: 1rem; padding-bottom: 1rem; }
  .stTabs [data-baseweb="tab-list"] { gap: 4px; }
  .stTabs [data-baseweb="tab"] { padding: 8px 20px; border-radius: 6px 6px 0 0; }
  .metric-card {
    background: #0f0f1a; border: 1px solid #1a1a2e;
    border-radius: 10px; padding: 12px 16px; margin-bottom: 8px;
  }
  .price-up   { color: #22c55e !important; font-weight: 700; }
  .price-down { color: #ef4444 !important; font-weight: 700; }
  .tag-eqh    { background: #ef444420; color: #ef4444; padding: 1px 6px; border-radius: 4px; font-size: 11px; font-weight: 700; }
  .tag-eql    { background: #22c55e20; color: #22c55e; padding: 1px 6px; border-radius: 4px; font-size: 11px; font-weight: 700; }
  .tag-bull   { background: #22c55e20; color: #22c55e; padding: 1px 6px; border-radius: 4px; font-size: 11px; font-weight: 700; }
  .tag-bear   { background: #ef444420; color: #ef4444; padding: 1px 6px; border-radius: 4px; font-size: 11px; font-weight: 700; }
  .level-row  { display: flex; justify-content: space-between; align-items: center;
                padding: 5px 8px; border-radius: 6px; margin-bottom: 3px; font-size: 13px; }
  .level-above { background: #ef444412; border: 1px solid #ef444425; }
  .level-below { background: #22c55e12; border: 1px solid #22c55e25; }
  .current-price { background: #ffffff15; border: 1px solid #ffffff30;
                   text-align: center; padding: 4px 8px; border-radius: 6px; margin: 4px 0; font-weight: 700; }
  .gap-card   { background: #f59e0b08; border: 1px solid #f59e0b30;
                border-radius: 8px; padding: 12px; margin-bottom: 10px; }
  .cor-card   { background: #0f0f1a; border: 1px solid #1a1a2e;
                border-radius: 8px; padding: 12px; }
  .session-hot { animation: pulse 1.5s infinite; }
  @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:.6; } }
  h1, h2, h3 { margin-top: 0 !important; }
  div[data-testid="stHorizontalBlock"] { align-items: center; }
</style>
""", unsafe_allow_html=True)

# ── Auto-refresh ──────────────────────────────────────────────────────────────
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60_000, key="refresh")
except ImportError:
    pass

# ── Header ────────────────────────────────────────────────────────────────────
session = get_session()
quotes  = get_quotes()

col_logo, col_session, col_next, col_time = st.columns([2, 3, 3, 2])

with col_logo:
    st.markdown("## ⚓ ICT Dina Anchor")
    st.caption("Gold · Silver · US100 · US30 · Oil")

with col_session:
    hot_style = "session-hot" if session["is_hot"] else ""
    st.markdown(f"""
    <div class="metric-card {hot_style}" style="border-color: {session['color']}40">
      <div style="color:{session['color']}; font-weight:700; font-size:15px">{session['label']}</div>
      <div style="font-size:12px; color:#9ca3af; margin-top:2px">{session['desc']}</div>
    </div>
    """, unsafe_allow_html=True)

with col_next:
    mins = session["next_mins"]
    time_str = f"{mins}m" if mins < 60 else f"{mins//60}h {mins%60}m"
    st.markdown(f"""
    <div class="metric-card">
      <div style="color:#f59e0b; font-weight:700">{session['next_label']}</div>
      <div style="font-size:12px; color:#9ca3af">in {time_str}</div>
    </div>
    """, unsafe_allow_html=True)

with col_time:
    st.markdown(f"""
    <div class="metric-card" style="text-align:center">
      <div style="font-size:11px; color:#6b7280">NY TIME</div>
      <div style="font-size:22px; font-weight:700; font-family:monospace">{session['ny_time']}</div>
    </div>
    """, unsafe_allow_html=True)

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
          <div style="font-size:11px; color:#9ca3af; font-weight:700">{cfg['label']}</div>
          <div style="font-size:18px; font-weight:700; font-family:monospace">{p:.{dec}f}</div>
          <div style="font-size:12px; color:{color}">{sign}{chg:.{dec}f} ({sign}{pct:.2f}%)</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_charts, tab_liq, tab_gaps, tab_cor, tab_imb = st.tabs([
    "📊 Charts", "🔫 Liquidity", "🧨 Gaps + Fib", "🧲 Correlations", "💣 Imbalances"
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: CHARTS
# ─────────────────────────────────────────────────────────────────────────────
with tab_charts:
    cols = st.columns(2)
    for idx, key in enumerate(inst_order):
        sym = TV_SYMBOLS[key]
        widget_html = f"""
        <div class="tradingview-widget-container" style="height:380px">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
          {{
            "autosize": true,
            "symbol": "{sym}",
            "interval": "15",
            "timezone": "America/New_York",
            "theme": "dark",
            "style": "1",
            "locale": "en",
            "backgroundColor": "rgba(8,8,16,1)",
            "gridColor": "rgba(26,26,46,1)",
            "hide_top_toolbar": false,
            "allow_symbol_change": false,
            "save_image": false,
            "calendar": false,
            "support_host": "https://www.tradingview.com"
          }}
          </script>
        </div>
        """
        with cols[idx % 2]:
            st.markdown(f"**{SYMBOLS[key]['label']}** — {SYMBOLS[key].get('unit','')}")
            components.html(widget_html, height=390)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: LIQUIDITY
# ─────────────────────────────────────────────────────────────────────────────
with tab_liq:
    st.info("""
    **🔫 Equal Highs (EQH) & Equal Lows (EQL) — Liquidity Pools**
    Before **8:00am NY**: mark equal H/L on 5m/15m/1h — these are buy/sell-side liquidity pools.
    They get tapped in the **8:30–9:30am news-to-open window 🔫**, or attacked after 10am (Silver Bullet / 2022 model).
    🔴 EQH above = sell-side (shorts get hunted) · 🟢 EQL below = buy-side (longs get hunted)
    """)

    cols = st.columns(3)
    for idx, key in enumerate(inst_order):
        cfg = SYMBOLS[key]
        q   = quotes.get(key, {})
        price = q.get("price", 0)

        with cols[idx % 3]:
            st.markdown(f"### {cfg['label']}")
            if price == 0:
                st.warning("No price data")
                continue

            df15 = get_candles(cfg["yahoo"], "15m", "5d")
            df1h = get_candles(cfg["yahoo"], "1h",  "30d")

            levels = find_equal_hl(df15, "15m", price) + find_equal_hl(df1h, "1h", price)
            levels.sort(key=lambda x: x["dist_pct"])
            levels = levels[:6]

            above = sorted([l for l in levels if l["is_above"]], key=lambda x: x["price"])
            below = sorted([l for l in levels if not l["is_above"]], key=lambda x: -x["price"])

            html = ""
            for l in above:
                touches = f" ×{l['touches']}" if l["touches"] > 2 else ""
                html += f"""<div class="level-row level-above">
                  <span><span class="tag-eqh">{l['type']}</span>&nbsp; {l['price']:.{cfg['decimals']}f} <small style="color:#6b7280">{l['timeframe']}{touches}</small></span>
                  <span style="color:#6b7280;font-size:12px">+{l['dist_pct']:.2f}%</span>
                </div>"""

            html += f"""<div class="current-price">▶ {price:.{cfg['decimals']}f} current</div>"""

            for l in below:
                touches = f" ×{l['touches']}" if l["touches"] > 2 else ""
                html += f"""<div class="level-row level-below">
                  <span><span class="tag-eql">{l['type']}</span>&nbsp; {l['price']:.{cfg['decimals']}f} <small style="color:#6b7280">{l['timeframe']}{touches}</small></span>
                  <span style="color:#6b7280;font-size:12px">-{l['dist_pct']:.2f}%</span>
                </div>"""

            if not levels:
                html = "<p style='color:#6b7280; font-size:13px'>No equal H/L detected in recent data</p>"

            st.markdown(html, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: GAPS + FIB
# ─────────────────────────────────────────────────────────────────────────────
with tab_gaps:
    st.info("""
    **🧨 RTH/ETH Gap + 0.5 Fibonacci**
    Prior day **ETH close (4:15pm NY)** vs today's **RTH open (9:30am NY)**.
    Plot fib from the lower to higher price — **the 0.5 fib fills in the first hour of opening.**
    5-day zones act as strong support/resistance and FVGs going forward.
    """)

    col1, col2 = st.columns(2)
    for colidx, key in enumerate(["US100", "US30"]):
        cfg   = SYMBOLS[key]
        q     = quotes.get(key, {})
        price = q.get("price", 0)
        dec   = cfg["decimals"]

        with (col1 if colidx == 0 else col2):
            st.markdown(f"### {cfg['label']} — Gap Fib Zones")
            daily   = get_candles(cfg["yahoo"], "1d",  "10d")
            intra   = get_candles(cfg["yahoo"], "15m", "5d")
            gaps    = detect_gap_fib(daily, intra)

            if not gaps:
                st.warning("No gap detected (market may be closed or gap < 0.05%)")
            else:
                for g in gaps:
                    dist_fib50 = abs(price - g["fib50"]) / price * 100 if price else 0
                    filled_badge = "✅ FILLED" if g["filled"] else f"🎯 {dist_fib50:.2f}% away"
                    dir_color = "#22c55e" if g["direction"] == "up" else "#ef4444"
                    dir_label = "▲ Gap Up" if g["direction"] == "up" else "▼ Gap Down"

                    st.markdown(f"""
                    <div class="gap-card" style="{'opacity:0.5' if g['filled'] else ''}">
                      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px">
                        <b style="color:#f59e0b">{g['date']}</b>
                        <span>
                          <span style="background:{dir_color}20; color:{dir_color}; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:700">{dir_label}</span>
                          &nbsp;<span style="background:#ffffff15; color:#9ca3af; padding:2px 8px; border-radius:4px; font-size:12px">{filled_badge}</span>
                        </span>
                      </div>
                      <div style="font-size:13px; line-height:2">
                        <div style="display:flex;justify-content:space-between"><span style="color:#6b7280">ETH Close</span><b style="font-family:monospace">{g['eth_close']:.{dec}f}</b></div>
                        <div style="display:flex;justify-content:space-between"><span style="color:#6b7280">RTH Open</span><b style="font-family:monospace">{g['rth_open']:.{dec}f}</b></div>
                        <div style="display:flex;justify-content:space-between"><span style="color:#6b7280">Fib 0.382</span><b style="font-family:monospace">{g['fib382']:.{dec}f}</b></div>
                        <div style="display:flex;justify-content:space-between; background:#f59e0b18; padding:2px 4px; border-radius:4px">
                          <span style="color:#f59e0b; font-weight:700">🎯 Fib 0.500</span>
                          <b style="font-family:monospace; color:#f59e0b">{g['fib50']:.{dec}f}</b>
                        </div>
                        <div style="display:flex;justify-content:space-between"><span style="color:#6b7280">Fib 0.618</span><b style="font-family:monospace">{g['fib618']:.{dec}f}</b></div>
                      </div>
                      <div style="font-size:11px; color:#4b5563; margin-top:6px">Gap: {g['gap_size']:.{dec}f} pts · 0.5 fib fills in first RTH hour</div>
                    </div>
                    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4: CORRELATIONS
# ─────────────────────────────────────────────────────────────────────────────
with tab_cor:
    st.info("""
    **🧲 Cross-Asset Correlations** (based on hourly returns, last 5 days)
    📌 **Gold & Silver** move together — Silver leads Gold at times, Gold leads Silver at times. Divergence = early signal.
    📌 **Oil follows DXY directly** (strong dollar = strong oil). *Not* inversely like metals.
    📌 **Gold/Silver move inverse to DXY** (strong dollar = bearish metals).
    """)

    # Fetch 1h data for correlation
    with st.spinner("Loading correlation data..."):
        dfs = {}
        for key in ["GOLD", "SILVER", "OIL", "DXY"]:
            df = get_candles(SYMBOLS[key]["yahoo"], "1h", "5d")
            if not df.empty:
                dfs[key] = df["Close"].values

    def corr_card(label: str, r: float, note: str, leading: str = ""):
        bar_pct = int((r + 1) / 2 * 100)
        bar_color = "#22c55e" if r > 0.3 else "#ef4444" if r < -0.3 else "#f59e0b"
        r_color   = "#22c55e" if r > 0 else "#ef4444"
        sign      = "+" if r > 0 else ""
        st.markdown(f"""
        <div class="cor-card" style="margin-bottom:12px">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px">
            <b>{label}</b>
            <span style="font-family:monospace; font-size:20px; font-weight:700; color:{r_color}">{sign}{r:.2f}</span>
          </div>
          <div style="background:#1e1e3a; border-radius:4px; height:6px; margin-bottom:8px; position:relative; overflow:hidden">
            <div style="position:absolute; top:0; left:50%; height:100%; width:{abs(bar_pct-50)}%;
                        {'right:0' if r < 0 else 'left:50%'}; background:{bar_color}; border-radius:4px"></div>
            <div style="position:absolute; top:0; left:50%; width:1px; height:100%; background:#4b5563"></div>
          </div>
          {"<div style='font-size:12px; color:#f59e0b; margin-bottom:4px'>📊 " + leading + "</div>" if leading else ""}
          <div style="font-size:12px; color:#6b7280">{note}</div>
        </div>
        """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if "GOLD" in dfs and "SILVER" in dfs:
            n = min(len(dfs["GOLD"]), len(dfs["SILVER"]))
            gr, sr = returns(dfs["GOLD"][-n:]), returns(dfs["SILVER"][-n:])
            r = pearson(gr, sr)
            lead = who_leads(gr, sr)
            lead_str = "Gold leading Silver" if lead == "first leads" else "Silver leading Gold" if lead == "second leads" else "Moving in sync"
            corr_card("Gold ↔ Silver", r,
                      "Move in conjunction — watch for divergence as early signal",
                      lead_str)
        if "GOLD" in dfs and "DXY" in dfs:
            n = min(len(dfs["GOLD"]), len(dfs["DXY"]))
            gr, dr = returns(dfs["GOLD"][-n:]), returns(dfs["DXY"][-n:])
            r = pearson(gr, dr)
            corr_card("Gold ↔ DXY", r,
                      "Gold moves inverse to DXY — strong dollar = bearish gold")

    with col2:
        if "OIL" in dfs and "DXY" in dfs:
            n = min(len(dfs["OIL"]), len(dfs["DXY"]))
            or_, dr = returns(dfs["OIL"][-n:]), returns(dfs["DXY"][-n:])
            r = pearson(or_, dr)
            corr_card("Oil ↔ DXY", r,
                      "Oil follows DXY DIRECTLY (not inversely!) — strong dollar = bullish oil")
        if "GOLD" in dfs and "OIL" in dfs:
            n = min(len(dfs["GOLD"]), len(dfs["OIL"]))
            gr, or_ = returns(dfs["GOLD"][-n:]), returns(dfs["OIL"][-n:])
            r = pearson(gr, or_)
            corr_card("Gold ↔ Oil", r,
                      "Gold and Oil typically move opposite to each other")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5: IMBALANCES
# ─────────────────────────────────────────────────────────────────────────────
with tab_imb:
    st.info("""
    **💣 Volume Imbalances (Body Gaps)**
    Gaps between candle **bodies** (open/close, not wicks) on 1h chart.
    These act as magnets — price **will** return to fill them, it just takes patience.
    Especially powerful in **Gold and Oil**. Oil also respects trend lines very well.
    """)

    imb_order = ["GOLD", "OIL", "SILVER", "US100", "US30"]
    cols = st.columns(3)
    for idx, key in enumerate(imb_order[:3]):
        cfg   = SYMBOLS[key]
        q     = quotes.get(key, {})
        price = q.get("price", 0)
        dec   = cfg["decimals"]
        priority = key in ("GOLD", "OIL")

        with cols[idx]:
            badge = "🔥 PRIORITY" if priority else ""
            st.markdown(f"### {cfg['label']} {badge}")
            if price == 0:
                st.warning("No price data")
                continue

            df1h = get_candles(cfg["yahoo"], "1h", "10d")
            imbs = find_imbalances(df1h, "1h", price)

            if not imbs:
                st.markdown("<p style='color:#6b7280; font-size:13px'>No unfilled imbalances nearby</p>", unsafe_allow_html=True)
            else:
                html = ""
                for imp in imbs:
                    is_bull  = imp["direction"] == "bull"
                    tag_cls  = "tag-bull" if is_bull else "tag-bear"
                    tag_lbl  = "▲ BULL VI" if is_bull else "▼ BEAR VI"
                    bg       = "#22c55e10" if is_bull else "#ef444410"
                    border   = "#22c55e25" if is_bull else "#ef444425"
                    dist_dir = f"+{imp['dist_pct']:.2f}%" if imp["is_above"] else f"-{imp['dist_pct']:.2f}%"
                    html += f"""
                    <div style="background:{bg}; border:1px solid {border}; border-radius:6px; padding:8px 10px; margin-bottom:6px; font-size:13px">
                      <div style="display:flex; justify-content:space-between; align-items:center">
                        <span><span class="{tag_cls}">{tag_lbl}</span>&nbsp; <b style="font-family:monospace">{imp['price']:.{dec}f}</b> <small style="color:#6b7280">{imp['timeframe']}</small></span>
                        <span style="color:#6b7280; font-size:12px">{dist_dir}</span>
                      </div>
                      <div style="color:#4b5563; font-size:11px; margin-top:3px">
                        Range {imp['lo']:.{dec}f} – {imp['hi']:.{dec}f} · size {imp['size']:.{dec}f} ({imp['size_pct']:.3f}%) 🧲
                      </div>
                    </div>"""
                st.markdown(html, unsafe_allow_html=True)

    # US100 + US30 below
    col1, col2 = st.columns(2)
    for colidx, key in enumerate(["US100", "US30"]):
        cfg   = SYMBOLS[key]
        q     = quotes.get(key, {})
        price = q.get("price", 0)
        dec   = cfg["decimals"]

        with (col1 if colidx == 0 else col2):
            st.markdown(f"### {cfg['label']}")
            df1h = get_candles(cfg["yahoo"], "1h", "10d")
            imbs = find_imbalances(df1h, "1h", price)
            if not imbs:
                st.markdown("<p style='color:#6b7280; font-size:13px'>No unfilled imbalances nearby</p>", unsafe_allow_html=True)
            else:
                html = ""
                for imp in imbs:
                    is_bull  = imp["direction"] == "bull"
                    tag_cls  = "tag-bull" if is_bull else "tag-bear"
                    tag_lbl  = "▲ BULL VI" if is_bull else "▼ BEAR VI"
                    bg       = "#22c55e10" if is_bull else "#ef444410"
                    border   = "#22c55e25" if is_bull else "#ef444425"
                    dist_dir = f"+{imp['dist_pct']:.2f}%" if imp["is_above"] else f"-{imp['dist_pct']:.2f}%"
                    html += f"""
                    <div style="background:{bg}; border:1px solid {border}; border-radius:6px; padding:8px 10px; margin-bottom:6px; font-size:13px">
                      <div style="display:flex; justify-content:space-between; align-items:center">
                        <span><span class="{tag_cls}">{tag_lbl}</span>&nbsp; <b style="font-family:monospace">{imp['price']:.{dec}f}</b> <small style="color:#6b7280">{imp['timeframe']}</small></span>
                        <span style="color:#6b7280; font-size:12px">{dist_dir}</span>
                      </div>
                      <div style="color:#4b5563; font-size:11px; margin-top:3px">
                        Range {imp['lo']:.{dec}f} – {imp['hi']:.{dec}f} · size {imp['size']:.{dec}f} ({imp['size_pct']:.3f}%)
                      </div>
                    </div>"""
                st.markdown(html, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("ICT Dina Anchor · Data refreshes every 60s · Educational purposes only · Not financial advice")
