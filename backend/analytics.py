"""Portfolio valuation and analytics.

Portfolio value on any day = cash on that day + sum(shares held * close price).
All return metrics are computed from that daily value series; beta is computed
against the S&P 500's daily returns over the same window.
"""
import os
from datetime import date, timedelta

import numpy as np
import pandas as pd

import market

RISK_FREE_RATE = float(os.getenv("RISK_FREE_RATE", "0.045"))  # annual, for Sharpe
TRADING_DAYS = 252


def build_value_series(portfolio, transactions) -> pd.Series | None:
    """Daily total value (cash + holdings) since the portfolio's first activity."""
    flows = getattr(portfolio, "cash_flows", []) or []
    start = min(
        [t.trade_date for t in transactions] + [f.flow_date for f in flows],
        default=portfolio.created_at.date(),
    )
    start = min(start, portfolio.created_at.date())
    idx = pd.bdate_range(start=start, end=date.today())
    if len(idx) == 0:
        idx = pd.DatetimeIndex([pd.Timestamp(date.today())])

    cash = pd.Series(float(portfolio.starting_cash), index=idx)
    for f in flows:
        cash[cash.index >= pd.Timestamp(f.flow_date)] += f.amount
    total = pd.Series(0.0, index=idx)

    symbols = sorted({t.symbol for t in transactions})
    for symbol in symbols:
        # cumulative shares held over time
        shares = pd.Series(0.0, index=idx)
        for t in transactions:
            if t.symbol != symbol:
                continue
            delta = t.shares if t.side == "BUY" else -t.shares
            ts = pd.Timestamp(t.trade_date)
            shares[shares.index >= ts] += delta
            cash_delta = -t.shares * t.price if t.side == "BUY" else t.shares * t.price
            cash[cash.index >= ts] += cash_delta

        closes = market.get_daily_closes(symbol, start - timedelta(days=7))
        if closes is None:
            continue
        prices = closes.reindex(idx, method="ffill").bfill()
        total += shares * prices

    values = (total + cash).dropna()
    return values if not values.empty else None


def benchmark_series(symbol: str, idx: pd.DatetimeIndex) -> pd.Series | None:
    if len(idx) == 0:
        return None
    closes = market.get_daily_closes(symbol, idx[0].date() - timedelta(days=7))
    if closes is None:
        return None
    return closes.reindex(idx, method="ffill").bfill()


def rebase(series: pd.Series, to: float = 100.0) -> pd.Series:
    first = series.iloc[0]
    if first == 0:
        return series * 0
    return series / first * to


def cagr(values: pd.Series) -> float | None:
    if len(values) < 2 or values.iloc[0] <= 0:
        return None
    days = (values.index[-1] - values.index[0]).days
    if days < 1:
        return None
    return (values.iloc[-1] / values.iloc[0]) ** (365.25 / days) - 1


def xirr(cashflows: list[tuple[date, float]]) -> float | None:
    """Money-weighted annual return. Buys are outflows (-), sells and the
    current market value of holdings are inflows (+)."""
    if len(cashflows) < 2:
        return None
    if not (any(a < 0 for _, a in cashflows) and any(a > 0 for _, a in cashflows)):
        return None
    t0 = min(d for d, _ in cashflows)
    years = np.array([(d - t0).days / 365.25 for d, _ in cashflows])
    amounts = np.array([a for _, a in cashflows])

    def npv(rate):
        return float(np.sum(amounts / (1 + rate) ** years))

    lo, hi = -0.9999, 100.0
    if npv(lo) * npv(hi) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        v = npv(mid)
        if abs(v) < 1e-8:
            break
        if npv(lo) * v < 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def sharpe_ratio(values: pd.Series) -> float | None:
    rets = values.pct_change().dropna()
    if len(rets) < 5 or rets.std() == 0:
        return None
    excess_annual = rets.mean() * TRADING_DAYS - RISK_FREE_RATE
    vol_annual = rets.std() * np.sqrt(TRADING_DAYS)
    return float(excess_annual / vol_annual)


def portfolio_beta(values: pd.Series, bench: pd.Series) -> float | None:
    df = pd.concat([values.pct_change(), bench.pct_change()], axis=1).dropna()
    if len(df) < 10:
        return None
    p, b = df.iloc[:, 0], df.iloc[:, 1]
    var = b.var()
    if var == 0:
        return None
    return float(p.cov(b) / var)


def weighted_pe(holdings: list[dict]) -> float | None:
    """Portfolio P/E as total value / total implied earnings (harmonic weighting)."""
    value, earnings = 0.0, 0.0
    for h in holdings:
        pe = h.get("pe")
        if pe and pe > 0:
            value += h["market_value"]
            earnings += h["market_value"] / pe
    return value / earnings if earnings > 0 else None


def weighted_peg(holdings: list[dict]) -> float | None:
    total, acc = 0.0, 0.0
    for h in holdings:
        peg = h.get("peg")
        if peg and peg > 0:
            total += h["market_value"]
            acc += peg * h["market_value"]
    return acc / total if total > 0 else None


def sector_breakdown(holdings: list[dict]) -> list[dict]:
    total = sum(h["market_value"] for h in holdings)
    if total <= 0:
        return []
    sectors: dict[str, float] = {}
    for h in holdings:
        sector = h.get("sector") or "Unknown"
        sectors[sector] = sectors.get(sector, 0.0) + h["market_value"]
    return sorted(
        [{"sector": s, "weight": v / total * 100} for s, v in sectors.items()],
        key=lambda x: -x["weight"],
    )
