from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

import analytics
import market
import models
import schemas
from database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Portfolio Simulator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # single-user app; tighten if you ever share it
    allow_methods=["*"],
    allow_headers=["*"],
)

BENCHMARKS = {"sp500": "^GSPC", "nasdaq": "^IXIC"}


def _holdings(portfolio: models.Portfolio) -> tuple[list[dict], float]:
    """Current holdings with live quotes + fundamentals, and remaining cash."""
    shares: dict[str, float] = {}
    cost: dict[str, float] = {}
    cash = float(portfolio.starting_cash)
    cash += sum(f.amount for f in portfolio.cash_flows)
    for t in sorted(portfolio.transactions, key=lambda x: x.trade_date):
        if t.side == "BUY":
            shares[t.symbol] = shares.get(t.symbol, 0) + t.shares
            cost[t.symbol] = cost.get(t.symbol, 0) + t.shares * t.price
            cash -= t.shares * t.price
        else:
            held = shares.get(t.symbol, 0)
            if held > 0:
                cost[t.symbol] = cost.get(t.symbol, 0) * max(held - t.shares, 0) / held
            shares[t.symbol] = held - t.shares
            cash += t.shares * t.price

    holdings = []
    for symbol, qty in shares.items():
        if qty <= 1e-9:
            continue
        quote = market.get_quote(symbol)
        fund = market.get_fundamentals(symbol)
        price = quote["price"] if quote else 0.0
        holdings.append(
            {
                "symbol": symbol,
                "shares": qty,
                "price": price,
                "day_change_pct": quote.get("change_pct") if quote else None,
                "market_value": qty * price,
                "cost_basis": cost.get(symbol, 0.0),
                "pe": fund["pe"],
                "peg": fund["peg"],
                "beta": fund["beta"],
                "sector": fund["sector"],
            }
        )
    holdings.sort(key=lambda h: -h["market_value"])
    return holdings, cash


def _get_portfolio(db: Session, portfolio_id: int) -> models.Portfolio:
    p = db.get(models.Portfolio, portfolio_id)
    if not p:
        raise HTTPException(404, "Portfolio not found")
    return p


# ---------- Portfolios ----------

@app.get("/api/portfolios", response_model=list[schemas.PortfolioOut])
def list_portfolios(db: Session = Depends(get_db)):
    return db.query(models.Portfolio).order_by(models.Portfolio.created_at).all()


@app.post("/api/portfolios", response_model=schemas.PortfolioOut)
def create_portfolio(body: schemas.PortfolioCreate, db: Session = Depends(get_db)):
    p = models.Portfolio(name=body.name, starting_cash=body.starting_cash)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@app.delete("/api/portfolios/{portfolio_id}")
def delete_portfolio(portfolio_id: int, db: Session = Depends(get_db)):
    db.delete(_get_portfolio(db, portfolio_id))
    db.commit()
    return {"ok": True}


# ---------- Transactions ----------

@app.post("/api/portfolios/{portfolio_id}/transactions", response_model=schemas.TransactionOut)
def add_transaction(
    portfolio_id: int, body: schemas.TransactionCreate, db: Session = Depends(get_db)
):
    p = _get_portfolio(db, portfolio_id)
    symbol = body.symbol.upper().strip()

    quote = market.get_quote(symbol)
    if quote is None:
        raise HTTPException(400, f"Could not find a price for '{symbol}'. Check the ticker.")

    trade_date = body.trade_date or date.today()
    if trade_date > date.today():
        raise HTTPException(400, "Trade date cannot be in the future.")

    # Price priority: explicit price > historical close for backdated trades > live quote
    if body.price:
        price = body.price
    elif trade_date < date.today():
        price = market.get_close_on(symbol, trade_date)
        if price is None:
            raise HTTPException(400, f"No price data for {symbol} on {trade_date}. It may predate the stock's listing.")
    else:
        price = quote["price"]

    # Fractional shares: derive from a dollar amount if given
    shares = body.shares if body.shares is not None else round(body.amount / price, 6)
    if shares <= 0:
        raise HTTPException(400, "Trade is too small.")

    holdings, cash = _holdings(p)

    if body.side == "BUY" and shares * price > cash + 1e-6:
        raise HTTPException(400, f"Not enough cash: this buy costs ${shares * price:,.2f} but only ${cash:,.2f} is available.")
    if body.side == "SELL":
        held = next((h["shares"] for h in holdings if h["symbol"] == symbol), 0.0)
        if shares > held + 1e-9:
            raise HTTPException(400, f"Cannot sell {shares:g} shares of {symbol}: only {held:g} held.")

    t = models.Transaction(
        portfolio_id=p.id,
        symbol=symbol,
        side=body.side,
        shares=shares,
        price=price,
        trade_date=trade_date,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@app.delete("/api/transactions/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    t = db.get(models.Transaction, transaction_id)
    if not t:
        raise HTTPException(404, "Transaction not found")
    db.delete(t)
    db.commit()
    return {"ok": True}


@app.get("/api/portfolios/{portfolio_id}/transactions", response_model=list[schemas.TransactionOut])
def list_transactions(portfolio_id: int, db: Session = Depends(get_db)):
    p = _get_portfolio(db, portfolio_id)
    return sorted(p.transactions, key=lambda t: (t.trade_date, t.id), reverse=True)


# ---------- Wallet deposits ----------

@app.post("/api/portfolios/{portfolio_id}/deposits")
def add_deposit(portfolio_id: int, body: schemas.DepositCreate, db: Session = Depends(get_db)):
    p = _get_portfolio(db, portfolio_id)
    flow_date = body.flow_date or date.today()
    if flow_date > date.today():
        raise HTTPException(400, "Deposit date cannot be in the future.")
    f = models.CashFlow(portfolio_id=p.id, amount=body.amount, flow_date=flow_date)
    db.add(f)
    db.commit()
    return {"ok": True, "amount": body.amount, "flow_date": flow_date.isoformat()}


# ---------- Summary / history / analytics ----------

@app.get("/api/portfolios/{portfolio_id}/summary")
def summary(portfolio_id: int, db: Session = Depends(get_db)):
    p = _get_portfolio(db, portfolio_id)
    holdings, cash = _holdings(p)
    invested = sum(h["market_value"] for h in holdings)
    contributed = p.starting_cash + sum(f.amount for f in p.cash_flows)
    return {
        "id": p.id,
        "name": p.name,
        "starting_cash": p.starting_cash,
        "contributed": contributed,
        "cash": cash,
        "invested": invested,
        "total_value": cash + invested,
        "holdings": holdings,
    }


RANGE_DAYS = {"1m": 30, "3m": 91, "6m": 182, "1y": 365, "3y": 365 * 3, "5y": 365 * 5}


@app.get("/api/portfolios/{portfolio_id}/history")
def history(portfolio_id: int, range: str = "max", db: Session = Depends(get_db)):
    import pandas as pd

    p = _get_portfolio(db, portfolio_id)
    values = analytics.build_value_series(p, p.transactions)
    if values is None or len(values) == 0:
        return {"points": []}

    # Chart window: requested range back from today, capped at 'max' = portfolio start
    if range in RANGE_DAYS:
        window_start = pd.Timestamp(date.today()) - pd.Timedelta(days=RANGE_DAYS[range])
    else:
        window_start = values.index[0]

    idx = pd.bdate_range(start=min(window_start, values.index[0]), end=date.today())
    idx = idx[idx >= window_start] if range in RANGE_DAYS else idx

    # Portfolio: slice to window, rebase at its first visible point
    pv = values[values.index >= window_start] if range in RANGE_DAYS else values
    series = {}
    if len(pv) > 0:
        series["portfolio_value"] = pv
        series["portfolio"] = analytics.rebase(pv)

    # Benchmarks: cover the whole window (even before the portfolio existed)
    for name, symbol in BENCHMARKS.items():
        b = analytics.benchmark_series(symbol, idx)
        if b is not None and len(b) > 0:
            series[name] = analytics.rebase(b)

    points = []
    for ts in idx:
        point = {"date": ts.strftime("%Y-%m-%d")}
        for key, s in series.items():
            v = s.get(ts)
            if v is not None and not pd.isna(v):
                point[key] = round(float(v), 2)
        if len(point) > 1:
            points.append(point)
    return {"points": points}


@app.get("/api/portfolios/{portfolio_id}/analytics")
def portfolio_analytics(portfolio_id: int, db: Session = Depends(get_db)):
    p = _get_portfolio(db, portfolio_id)
    holdings, cash = _holdings(p)
    values = analytics.build_value_series(p, p.transactions)

    result = {
        "cagr": None, "xirr": None, "sharpe": None, "beta": None,
        "pe": analytics.weighted_pe(holdings),
        "peg": analytics.weighted_peg(holdings),
        "sectors": analytics.sector_breakdown(holdings),
    }

    if values is not None and len(values) >= 2:
        result["cagr"] = analytics.cagr(values)
        result["sharpe"] = analytics.sharpe_ratio(values)
        bench = analytics.benchmark_series(BENCHMARKS["sp500"], values.index)
        if bench is not None:
            result["beta"] = analytics.portfolio_beta(values, bench)

    flows = [(t.trade_date, -t.shares * t.price if t.side == "BUY" else t.shares * t.price)
             for t in p.transactions]
    invested_value = sum(h["market_value"] for h in holdings)
    if invested_value > 0:
        flows.append((date.today(), invested_value))
    result["xirr"] = analytics.xirr(flows)
    return result


@app.get("/api/quote/{symbol}")
def quote(symbol: str):
    q = market.get_quote(symbol)
    if q is None:
        raise HTTPException(404, f"No quote found for '{symbol.upper()}'")
    return q


# ---------- Serve the built React frontend (single-service deploy) ----------

frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
