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
    """Trailing P/E, PEG, beta, and sector for a symbol (best effort).

    Uses yfinance's `.info`, which hits Yahoo's quoteSummary endpoint. That
    endpoint is far more likely to be rate-limited/blocked from cloud-hosting
    IPs (Render, AWS, etc.) than the quote/history endpoints elsewhere in this
    module, so failures here are common in production even when live quotes
    work fine.
    """
    symbol = symbol.upper()
    key = ("fund", symbol)
    cached = _get_cached(key, FUNDAMENTALS_TTL)
    if cached is not None:
        return cached
    try:
        info = yf.Ticker(symbol).info or {}
        result = {
            "pe": info.get("trailingPE"),
            "peg": info.get("pegRatio") or info.get("trailingPegRatio"),
            "beta": info.get("beta"),
            "sector": info.get("sector"),
        }
    except Exception as e:
        print(f"[market] fundamentals fetch failed for {symbol}: {e!r}")
        # Serve the last known-good value instead of blanking it out on what
        # is often a transient block, rather than caching an empty result.
        with _lock:
            stale = _cache.get(key)
        return stale[1] if stale is not None else {"pe": None, "peg": None, "beta": None, "sector": None}
    _set_cached(key, result)
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
