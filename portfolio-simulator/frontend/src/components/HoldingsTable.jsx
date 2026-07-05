import { api } from '../api.js'

const money = (v) =>
  v == null ? '—' : v.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

export default function HoldingsTable({ holdings, cash, totalValue, portfolioId, onDone }) {
  const sellAll = async (h) => {
    if (!window.confirm(`Sell all ${h.shares.toLocaleString()} shares of ${h.symbol} at market?`)) return
    await api.trade(portfolioId, { symbol: h.symbol, side: 'SELL', shares: h.shares })
    onDone()
  }

  return (
    <div className="card">
      <h2>Holdings</h2>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Sector</th>
            <th className="num">Shares</th>
            <th className="num">Price</th>
            <th className="num">Day %</th>
            <th className="num">Market value</th>
            <th className="num">Gain / loss</th>
            <th className="num">Weight</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h) => {
            const gl = h.market_value - h.cost_basis
            return (
              <tr key={h.symbol}>
                <td><span className="sym">{h.symbol}</span></td>
                <td>{h.sector || '—'}</td>
                <td className="num">{h.shares.toLocaleString()}</td>
                <td className="num">{h.price?.toFixed(2)}</td>
                <td className={`num ${h.day_change_pct >= 0 ? 'up' : 'down'}`}>
                  {h.day_change_pct == null ? '—' : `${h.day_change_pct.toFixed(2)}%`}
                </td>
                <td className="num">{money(h.market_value)}</td>
                <td className={`num ${gl >= 0 ? 'up' : 'down'}`}>{money(gl)}</td>
                <td className="num">
                  {totalValue > 0 ? `${((h.market_value / totalValue) * 100).toFixed(1)}%` : '—'}
                </td>
                <td className="num">
                  <button className="sell-link" onClick={() => sellAll(h)}>Sell all</button>
                </td>
              </tr>
            )
          })}
          <tr>
            <td><span className="sym">Cash</span></td>
            <td>—</td>
            <td className="num">—</td>
            <td className="num">—</td>
            <td className="num">—</td>
            <td className="num">{money(cash)}</td>
            <td className="num">—</td>
            <td className="num">
              {totalValue > 0 ? `${((cash / totalValue) * 100).toFixed(1)}%` : '—'}
            </td>
            <td></td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}
