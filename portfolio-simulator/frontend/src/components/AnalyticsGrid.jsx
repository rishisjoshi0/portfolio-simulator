const pct = (v) => (v == null ? '—' : `${(v * 100).toFixed(2)}%`)
const num = (v) => (v == null ? '—' : v.toFixed(2))

export default function AnalyticsGrid({ analytics }) {
  if (!analytics) return null
  const metrics = [
    { label: 'CAGR', value: pct(analytics.cagr) },
    { label: 'XIRR', value: pct(analytics.xirr) },
    { label: 'P/E ratio', value: num(analytics.pe) },
    { label: 'PEG ratio', value: num(analytics.peg) },
    { label: 'Beta (vs S&P 500)', value: num(analytics.beta) },
    { label: 'Sharpe ratio', value: num(analytics.sharpe) },
  ]

  return (
    <div className="card">
      <h2>Analytics</h2>
      <div className="metrics-grid">
        {metrics.map((m) => (
          <div className="metric" key={m.label}>
            <div className="label">{m.label}</div>
            <div className="value">{m.value}</div>
          </div>
        ))}
      </div>

      {analytics.sectors?.length > 0 && (
        <>
          <h2 style={{ marginTop: 22 }}>Sector allocation</h2>
          {analytics.sectors.map((s) => (
            <div className="sector-row" key={s.sector}>
              <span className="name">{s.sector}</span>
              <div className="sector-bar">
                <div style={{ width: `${Math.min(s.weight, 100)}%` }} />
              </div>
              <span className="pct">{s.weight.toFixed(1)}%</span>
            </div>
          ))}
        </>
      )}
    </div>
  )
}
