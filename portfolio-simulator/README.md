# PaperDesk — Portfolio Simulator

A single-user paper-trading portal for US stocks. Create multiple portfolios with
starting cash, buy and sell real tickers at live (15-min delayed) Yahoo Finance
prices, chart portfolio value against the S&P 500 and Nasdaq, and see analytics:
CAGR, XIRR, portfolio P/E, PEG, beta, Sharpe ratio, and sector allocation.

Stack: **FastAPI + yfinance + SQLAlchemy** backend, **React (Vite) + Recharts**
frontend. The backend serves the built frontend, so it deploys as one service.

## Data strategy (free, no API key)

All market data comes from Yahoo Finance via `yfinance`. To stay well within
what Yahoo tolerates for free use, everything is cached server-side in memory:

| Data | Refresh | Why |
|---|---|---|
| Live quotes | 15 min | Yahoo's free quotes are ~15-min delayed anyway |
| Daily closes (history) | 1 hour | Daily closes change once per day |
| Fundamentals (P/E, PEG, beta, sector) | 24 hours | These barely move |

The frontend also auto-refreshes on the same 15-minute cadence. Ten page loads
inside a window cost one Yahoo request, not ten.

## Run locally

```bash
# Terminal 1 — backend (http://localhost:8000)
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Terminal 2 — frontend dev server (http://localhost:5173, proxies /api)
cd frontend
npm install
npm run dev
```

Or run it exactly as deployed (one process):

```bash
cd frontend && npm install && npm run build && cd ..
cd backend && uvicorn main:app
# open http://localhost:8000
```

## Deploy (free)

**Recommended: Render free tier**

1. Push this folder to a GitHub repo.
2. On [render.com](https://render.com): New → Blueprint → pick the repo. The
   included `render.yaml` configures everything.
3. (Strongly recommended) Create a free Postgres database on
   [neon.tech](https://neon.tech) or [supabase.com](https://supabase.com), copy
   its connection string, and set it as the `DATABASE_URL` environment variable
   on the Render service. Without it, the app falls back to SQLite on Render's
   ephemeral disk, and **your portfolios will reset on every redeploy/restart**.

Notes on the free tier:

- The service sleeps after ~15 minutes of inactivity; the first request after
  that takes ~30 seconds while it wakes up. Normal for free hosting.
- Alternatives: Hugging Face Spaces (Docker) or Fly.io free allowances work the
  same way — one Python service, `DATABASE_URL` pointed at free Postgres.

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./portfolios.db` | Any SQLAlchemy URL; use free Neon/Supabase Postgres in production |
| `RISK_FREE_RATE` | `0.045` | Annual risk-free rate used in the Sharpe ratio |

## How the numbers are computed

- **Portfolio value (daily):** cash on that day + Σ(shares held × daily close),
  rebuilt from the transaction log. Benchmarks are rebased to 100 at your
  portfolio's start date for a fair comparison.
- **CAGR:** annualized growth of the daily value series since inception.
- **XIRR:** money-weighted return of invested capital — buys as outflows, sells
  as inflows, current holdings value as a final inflow (bisection solver).
- **Sharpe:** annualized excess return over `RISK_FREE_RATE` ÷ annualized
  volatility of daily returns.
- **Beta:** covariance of daily portfolio returns vs S&P 500 returns ÷ benchmark
  variance, over your portfolio's own history.
- **P/E:** total market value ÷ total implied earnings (harmonic weighting —
  the standard way to aggregate P/E).
- **PEG:** market-value-weighted average of holdings' PEG ratios.
- **Sectors:** market-value weights by Yahoo's sector classification.

## Notes & limits

- US-listed tickers only (by design, for now). Index benchmarks: `^GSPC`, `^IXIC`.
- yfinance is an unofficial library scraping Yahoo's public endpoints. It's the
  best keyless free source, but Yahoo can change things without notice; if data
  stops flowing, `pip install -U yfinance` usually fixes it.
- Backdated trades are supported (set the trade date when placing an order), and
  history is priced with real historical closes.
- This is a simulator: no dividends, splits are handled via adjusted closes for
  charting but not for share counts of backdated positions.
