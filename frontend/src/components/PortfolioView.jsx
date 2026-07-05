import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'
import TickerStrip from './TickerStrip.jsx'
import PerformanceChart from './PerformanceChart.jsx'
import AnalyticsGrid from './AnalyticsGrid.jsx'
import HoldingsTable from './HoldingsTable.jsx'
import TradeForm from './TradeForm.jsx'

const REFRESH_MS = 15 * 60 * 1000 // quotes are ~15-min delayed; match that

const money = (v) =>
  v == null ? '—' : v.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

export default function PortfolioView({ portfolioId }) {
  const [summary, setSummary] = useState(null)
  const [analytics, setAnalytics] = useState(null)
  const [error, setError] = useState(null)
  const [version, setVersion] = useState(0) // bumped after trades/deposits so the chart refetches

  const load = useCallback(async () => {
    setError(null)
    try {
      const s = await api.summary(portfolioId)
      setSummary(s)
      setVersion((v) => v + 1)
      const a = await api.analytics(portfolioId)
      setAnalytics(a)
    } catch (e) {
      setError(e.message)
    }
  }, [portfolioId])

  useEffect(() => {
    load()
    const timer = setInterval(load, REFRESH_MS)
    return () => clearInterval(timer)
  }, [load])

  if (!summary) return <div className="loading">Loading portfolio…</div>

  const contributed = summary.contributed ?? summary.starting_cash
  const gain = summary.total_value - contributed
  const gainPct = (gain / contributed) * 100

  return (
    <>
      <div className="page-header">
        <h1>{summary.name}</h1>
        <div className="value-line">
          {money(summary.total_value)}
          <span className={`sub ${gain >= 0 ? 'up' : 'down'}`}>
            {gain >= 0 ? '+' : ''}{money(gain).replace('$-', '-$')} ({gainPct.toFixed(2)}%) all time
          </span>
        </div>
      </div>

      {summary.holdings.length > 0 && <TickerStrip holdings={summary.holdings} />}
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <TradeForm portfolioId={portfolioId} cash={summary.cash} onDone={load} />
      </div>

      <PerformanceChart portfolioId={portfolioId} version={version} />
      <AnalyticsGrid analytics={analytics} />
      <HoldingsTable
        holdings={summary.holdings}
        cash={summary.cash}
        totalValue={summary.total_value}
        portfolioId={portfolioId}
        onDone={load}
      />
    </>
  )
}
