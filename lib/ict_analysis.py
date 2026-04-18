import numpy as np
import pandas as pd
from datetime import datetime
import pytz

NY_TZ = pytz.timezone("America/New_York")

# ── Session ──────────────────────────────────────────────────────────────────

SESSION_PHASES = [
    (0,   3*60,       "asian",         "🌙 Asian Session",                "#6366f1", "Building liquidity"),
    (3*60, 8*60,      "london",        "🇬🇧 London Session",               "#8b5cf6", "London sweep in play"),
    (8*60, 8*60+30,   "pre_news",      "⏰ Pre-News",                      "#f59e0b", "Mark equal H/L on 5m/15m/1h now"),
    (8*60+30, 9*60+30,"news_to_open",  "🔫 Liquidity Sweep Zone",         "#ef4444", "8:30–9:30 NY — equal H/L targets active"),
    (9*60+30, 10*60,  "opening_range", "📈 Opening Range",                 "#f97316", "Mark RTH open — first 30min range"),
    (10*60, 11*60,    "silver_bullet", "🎯 Silver Bullet / 2022 Model",    "#22c55e", "After 10am — attack remaining liquidity"),
    (11*60, 14*60,    "ny_midday",     "😴 NY Midday",                     "#64748b", "Low volatility — avoid overtrading"),
    (14*60, 16*60+15, "ny_close",      "🔔 NY Close",                      "#94a3b8", "Mark 4:15pm ETH close for tomorrow"),
    (16*60+15, 24*60, "after_hours",   "🌃 After Hours / ETH",             "#475569", "Electronic trading hours"),
]

KEY_TIMES = [
    (8*60+30,  "News Event (8:30 NY)"),
    (9*60+30,  "NY Open (9:30)"),
    (10*60,    "Silver Bullet (10:00)"),
    (11*60,    "SB End (11:00)"),
    (16*60+15, "ETH Close (16:15)"),
]

def get_session() -> dict:
    now_ny = datetime.now(NY_TZ)
    total_min = now_ny.hour * 60 + now_ny.minute

    phase_info = SESSION_PHASES[-1]
    for start, end, phase_id, label, color, desc in SESSION_PHASES:
        if start <= total_min < end:
            phase_info = (start, end, phase_id, label, color, desc)
            break

    _, _, phase_id, label, color, desc = phase_info

    next_label, next_mins = "Next session", 0
    for at, t_label in KEY_TIMES:
        if at > total_min:
            next_label = t_label
            next_mins = at - total_min
            break

    is_hot = phase_id in ("news_to_open", "silver_bullet")

    return {
        "ny_time": now_ny.strftime("%H:%M:%S"),
        "phase": phase_id,
        "label": label,
        "color": color,
        "desc": desc,
        "is_hot": is_hot,
        "next_label": next_label,
        "next_mins": next_mins,
    }

# ── Equal Highs / Equal Lows ─────────────────────────────────────────────────

def find_equal_hl(df: pd.DataFrame, timeframe: str, current_price: float, tolerance: float = 0.002) -> list:
    if df.empty or len(df) < 3:
        return []

    recent = df.tail(60)
    levels = []

    for col, ltype in [("High", "EQH"), ("Low", "EQL")]:
        vals = recent[col].values
        i = 0
        while i < len(vals):
            seed = vals[i]
            group = [seed]
            j = i + 1
            while j < len(vals) and abs(vals[j] - seed) / seed <= tolerance:
                group.append(vals[j])
                j += 1
            if len(group) >= 2:
                price = float(np.mean(group))
                dist_pct = abs(price - current_price) / current_price * 100
                levels.append({
                    "price": price,
                    "type": ltype,
                    "timeframe": timeframe,
                    "touches": len(group),
                    "dist_pct": dist_pct,
                    "is_above": price > current_price,
                })
            i = j

    levels.sort(key=lambda x: x["dist_pct"])
    return levels[:6]

# ── RTH/ETH Gap + Fib ─────────────────────────────────────────────────────────

def detect_gap_fib(daily_df: pd.DataFrame, intraday_df: pd.DataFrame) -> list:
    if daily_df.empty or len(daily_df) < 2:
        return []

    gaps = []
    daily = daily_df.tail(7)

    for i in range(1, min(6, len(daily))):
        prev = daily.iloc[-(i+1)]
        curr = daily.iloc[-i]

        eth_close = float(prev["Close"])
        rth_open  = float(curr["Open"])

        gap_size = abs(rth_open - eth_close)
        if gap_size / eth_close < 0.0005:
            continue

        direction = "up" if rth_open > eth_close else "down"
        lo = min(rth_open, eth_close)
        hi = max(rth_open, eth_close)
        fib50  = lo + gap_size * 0.500
        fib382 = lo + gap_size * 0.382
        fib618 = lo + gap_size * 0.618

        date_str = curr.name.strftime("%Y-%m-%d") if hasattr(curr.name, "strftime") else str(curr.name)[:10]

        # Check if filled
        day_candles = intraday_df[intraday_df.index.strftime("%Y-%m-%d") == date_str] if not intraday_df.empty else pd.DataFrame()
        filled = False
        if not day_candles.empty:
            filled = bool((day_candles["Low"] <= fib50).any() if direction == "up" else (day_candles["High"] >= fib50).any())

        gaps.append({
            "date": date_str,
            "eth_close": eth_close,
            "rth_open":  rth_open,
            "gap_size":  gap_size,
            "direction": direction,
            "fib50":  fib50,
            "fib382": fib382,
            "fib618": fib618,
            "lo": lo,
            "hi": hi,
            "filled": filled,
        })

    return gaps

# ── Volume Imbalances ─────────────────────────────────────────────────────────

def find_imbalances(df: pd.DataFrame, timeframe: str, current_price: float) -> list:
    if df.empty or len(df) < 3:
        return []

    imbalances = []
    for i in range(1, len(df)):
        prev = df.iloc[i-1]
        curr = df.iloc[i]
        pb_hi = max(prev["Open"], prev["Close"])
        pb_lo = min(prev["Open"], prev["Close"])
        cb_hi = max(curr["Open"], curr["Close"])
        cb_lo = min(curr["Open"], curr["Close"])

        if cb_lo > pb_hi:  # bullish gap
            size = cb_lo - pb_hi
            mid  = (pb_hi + cb_lo) / 2
            imbalances.append({"price": mid, "hi": cb_lo, "lo": pb_hi, "direction": "bull",
                                "size": size, "size_pct": size / current_price * 100,
                                "timeframe": timeframe,
                                "dist_pct": abs(mid - current_price) / current_price * 100,
                                "is_above": mid > current_price})

        if cb_hi < pb_lo:  # bearish gap
            size = pb_lo - cb_hi
            mid  = (pb_lo + cb_hi) / 2
            imbalances.append({"price": mid, "hi": pb_lo, "lo": cb_hi, "direction": "bear",
                                "size": size, "size_pct": size / current_price * 100,
                                "timeframe": timeframe,
                                "dist_pct": abs(mid - current_price) / current_price * 100,
                                "is_above": mid > current_price})

    # Keep unfilled only
    unfilled = [x for x in imbalances if
                (x["direction"] == "bull" and current_price < x["hi"]) or
                (x["direction"] == "bear" and current_price > x["lo"])]
    unfilled.sort(key=lambda x: x["dist_pct"])
    return unfilled[:5]

# ── Correlation ───────────────────────────────────────────────────────────────

def pearson(a: np.ndarray, b: np.ndarray) -> float:
    n = min(len(a), len(b))
    if n < 5:
        return 0.0
    a, b = a[:n], b[:n]
    with np.errstate(invalid="ignore"):
        r = float(np.corrcoef(a, b)[0, 1])
    return 0.0 if np.isnan(r) else r

def returns(closes: np.ndarray) -> np.ndarray:
    return np.diff(closes) / closes[:-1]

# ── Fair Value Gaps ───────────────────────────────────────────────────────────

def find_fvg(df: pd.DataFrame, timeframe: str, current_price: float) -> list:
    """3-candle FVG: gap between candle[i-2] wick and candle[i] wick."""
    if df.empty or len(df) < 3:
        return []

    fvgs = []
    for i in range(2, len(df)):
        c1 = df.iloc[i - 2]
        c3 = df.iloc[i]

        # Bullish FVG: c3 low > c1 high (gap up)
        if c3["Low"] > c1["High"]:
            lo  = float(c1["High"])
            hi  = float(c3["Low"])
            mid = (lo + hi) / 2
            fvgs.append({"type": "bull", "hi": hi, "lo": lo, "mid": mid,
                         "size": hi - lo, "timeframe": timeframe,
                         "dist_pct": abs(mid - current_price) / current_price * 100,
                         "is_above": mid > current_price})

        # Bearish FVG: c3 high < c1 low (gap down)
        if c3["High"] < c1["Low"]:
            lo  = float(c3["High"])
            hi  = float(c1["Low"])
            mid = (lo + hi) / 2
            fvgs.append({"type": "bear", "hi": hi, "lo": lo, "mid": mid,
                         "size": hi - lo, "timeframe": timeframe,
                         "dist_pct": abs(mid - current_price) / current_price * 100,
                         "is_above": mid > current_price})

    # Keep only unfilled (price hasn't traded back through)
    unfilled = [f for f in fvgs if
                (f["type"] == "bull" and current_price < f["hi"]) or
                (f["type"] == "bear" and current_price > f["lo"])]
    unfilled.sort(key=lambda x: x["dist_pct"])
    return unfilled[:6]


def who_leads(a: np.ndarray, b: np.ndarray) -> str:
    n = min(len(a), len(b))
    if n < 6:
        return "moving in sync"
    a_leads = abs(pearson(a[:n-1], b[1:n]))
    b_leads = abs(pearson(b[:n-1], a[1:n]))
    if a_leads > b_leads + 0.05:
        return "first leads"
    if b_leads > a_leads + 0.05:
        return "second leads"
    return "moving in sync"
