import { useState } from 'react'
import { api } from '../api.js'

export default function TradeForm({ portfolioId, cash, onDone }) {
  const [symbol, setSymbol] = useState('')
  const [side, setSide] = useState('BUY')
  const [shares, setShares] = useState('')
  const [tradeDate, setTradeDate] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const submit = async () => {
    const qty = parseFloat(shares)
    if (!symbol.trim() || !qty || qty <= 0) return
    setBusy(true)
    setError(null)
    try {
      const payload = { symbol: symbol.trim(), side, shares: qty }
      if (tradeDate) payload.trade_date = tradeDate
      await api.trade(portfolioId, payload)
      setSymbol('')
      setShares('')
      onDone()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="trade-form">
        <div className="field">
          <label htmlFor="tf-side">Action</label>
          <select id="tf-side" value={side} onChange={(e) => setSide(e.target.value)}>
            <option value="BUY">Buy</option>
            <option value="SELL">Sell</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="tf-symbol">Ticker</label>
          <input
            id="tf-symbol"
            placeholder="e.g. AAPL"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          />
        </div>
        <div className="field">
          <label htmlFor="tf-shares">Shares</label>
          <input
            id="tf-shares"
            type="number"
            min="0"
            step="any"
            placeholder="10"
            value={shares}
            onChange={(e) => setShares(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submit()}
          />
        </div>
        <div className="field">
          <label htmlFor="tf-date">Trade date (optional)</label>
          <input
            id="tf-date"
            type="date"
            value={tradeDate}
            onChange={(e) => setTradeDate(e.target.value)}
          />
        </div>
        <button className="btn-primary" onClick={submit} disabled={busy}>
          {busy ? 'Placing…' : 'Place trade'}
        </button>
        <div className="field" style={{ marginLeft: 'auto' }}>
          <label>Cash available</label>
          <span style={{ fontFamily: 'var(--mono)', fontWeight: 600, padding: '9px 0' }}>
            {cash?.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
          </span>
        </div>
      </div>
      {error && <div className="error-banner">{error}</div>}
    </>
  )
}
