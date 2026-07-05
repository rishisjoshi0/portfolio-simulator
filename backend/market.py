"""Market data via yfinance (free Yahoo Finance data, no API key).

Everything is cached in memory so the app hits Yahoo as little as possible:
  - live quotes:    15 min TTL (Yahoo's free quotes are ~15-min delayed anyway)
  - daily history:  1 hour TTL (daily closes only change once per day)
  - fundamentals:   24 hour TTL (P/E, PEG, beta, sector move slowly)
"""
import threading
import time
from datetime import date
from typing import Optional

import pandas as pd
import yfinance as yf

QUOTE_TTL = 15 * 60
HISTORY_TTL = 60 * 60
FUNDAMENTALS_TTL = 24 * 60 * 60

_cache: dict = {}
_lock = threading.Lock()


def _get_cached(key, ttl):
    with _lock:
        entry = _cache.get(key)
        if entry and time.time() - entry[0] < ttl:
            return entry[1]
    return None


def _set_cached(key, value):
    with _lock:
        _cache[key] = (time.time(), value)


def get_quote(symbol: str) -> Optional[dict]:
    """Latest price + day change for one symbol."""
    symbol = symbol.upper()
    cached = _get_cached(("quote", symbol), QUOTE_TTL)
    if cached is not None:
        return cached
    try:
        t = yf.Ticker(symbol)
        fi = t.fast_info
        price = fi.last_price
        prev = fi.previous_close
        if price is None:
            return None
        quote = {
            "symbol": symbol,
            "price": float(price),
            "prev_close": float(prev) if prev else None,
            "change_pct": (float(price) / float(prev) - 1) * 100 if prev else None,
        }
        _set_cached(("quote", symbol), quote)
        return quote
    except Exception:
        return None


def get_quotes(symbols: list[str]) -> dict[str, dict]:
    return {s: q for s in symbols if (q := get_quote(s)) is not None}


def get_daily_closes(symbol: str, start: date) -> Optional[pd.Series]:
    """Daily close prices from `start` to today, forward-filled over holidays."""
    symbol = symbol.upper()
    key = ("history", symbol, start.isoformat())
    cached = _get_cached(key, HISTORY_TTL)
    if cached is not None:
        return cached
    try:
        df = yf.Ticker(symbol).history(start=start.isoformat(), auto_adjust=True)
        if df.empty:
            return None
        closes = df["Close"]
        closes.index = closes.index.tz_localize(None).normalize()
        closes = closes[~closes.index.duplicated(keep="last")]
        _set_cached(key, closes)
        return closes
    except Exception:
        return None


def get_fundamentals(symbol: str) -> dict:
    """Trailing P/E, PEG, beta, and sector for a symbol (best effort)."""
    symbol = symbol.upper()
    cached = _get_cached(("fund", symbol), FUNDAMENTALS_TTL)
    if cached is not None:
        return cached
    result = {"pe": None, "peg": None, "beta": None, "sector": None}
    try:
        info = yf.Ticker(symbol).info or {}
        result["pe"] = info.get("trailingPE")
        result["peg"] = info.get("pegRatio") or info.get("trailingPegRatio")
        result["beta"] = info.get("beta")
        result["sector"] = info.get("sector")
    except Exception:
        pass
    _set_cached(("fund", symbol), result)
    return result


def get_close_on(symbol: str, d: date) -> Optional[float]:
    """Close price on date `d`, falling back to the most recent trading day
    before it (handles weekends/holidays)."""
    closes = get_daily_closes(symbol, d - pd.Timedelta(days=14).to_pytimedelta())
    if closes is None:
        return None
    ts = pd.Timestamp(d)
    eligible = closes[closes.index <= ts]
    if eligible.empty:
        return None
    return float(eligible.iloc[-1])


def validate_symbol(symbol: str) -> bool:
    return get_quote(symbol) is not None
