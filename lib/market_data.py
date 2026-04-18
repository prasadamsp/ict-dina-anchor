import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

SYMBOLS = {
    "GOLD":   {"yahoo": "GC=F",      "label": "Gold",   "unit": "USD/oz",  "decimals": 2},
    "SILVER": {"yahoo": "SI=F",      "label": "Silver", "unit": "USD/oz",  "decimals": 3},
    "US100":  {"yahoo": "NQ=F",      "label": "US100",  "unit": "pts",     "decimals": 2},
    "US30":   {"yahoo": "YM=F",      "label": "US30",   "unit": "pts",     "decimals": 0},
    "OIL":    {"yahoo": "CL=F",      "label": "Oil",    "unit": "USD/bbl", "decimals": 2},
    "DXY":    {"yahoo": "DX-Y.NYB",  "label": "DXY",    "unit": "",        "decimals": 3},
}

TV_SYMBOLS = {
    "GOLD":   "COMEX:GC1!",
    "SILVER": "COMEX:SI1!",
    "US100":  "CME_MINI:NQ1!",
    "US30":   "CBOT_MINI:YM1!",
    "OIL":    "NYMEX:CL1!",
}

@st.cache_data(ttl=60, show_spinner=False)
def get_candles(symbol: str, interval: str, period: str) -> pd.DataFrame:
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return pd.DataFrame()
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=30, show_spinner=False)
def get_quotes() -> dict:
    quotes = {}
    for key, cfg in SYMBOLS.items():
        try:
            t = yf.Ticker(cfg["yahoo"])
            info = t.fast_info
            price = info.last_price or 0
            prev = info.previous_close or price
            change = price - prev
            pct = (change / prev * 100) if prev else 0
            quotes[key] = {"price": price, "change": change, "pct": pct}
        except Exception:
            quotes[key] = {"price": 0, "change": 0, "pct": 0}
    return quotes
