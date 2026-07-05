import { useState } from 'react'
import { api } from '../api.js'

export default function TradeForm({ portfolioId, cash, onDone }) {
  const [symbol, setSymbol] = useState('')
  const [side, setSide] = useState('BUY')
  const [mode, setMode] = useState('shares') // 'shares' | 'amount'
  const [qty, setQty] = useState('')
  const [tradeDate, setTradeDate] = useState('')
  const [deposit, setDeposit] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const submit = async () => {
    const n = parseFloat(qty)
    if (!symbol.trim() || !n || n <= 0) return
    setBusy(true)
    setError(null)
    try {
      const payload = { symbol: symbol.trim(), side }
      if (mode === 'shares') payload.shares = n
      else payload.amount = n
      if (tradeDate) payload.trade_date = tradeDate
      await api.trade(portfolioId, payload)
      setSymbol('')
      setQty('')
      onDone()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const addFunds = async () => {
    const n = parseFloat(deposit)
    if (!n || n <= 0) return
    setBusy(true)
    setError(null)
    try {
      await api.deposit(portfolioId, n)
      setDeposit('')
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
          <label htmlFor="tf-mode">Order by</label>
          <select id="tf-mode" value={mode} onChange={(e) => { setMode(e.target.value); setQty('') }}>
            <option value="shares">Shares</option>
            <option value="amount">Amount (USD)</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="tf-qty">{mode === 'shares' ? 'Shares' : 'Amount ($)'}</label>
          <input
            id="tf-qty"
            type="number"
            min="0"
            step="any"
            placeholder={mode === 'shares' ? '10' : '1000'}
            value={qty}
            onChange={(e) => setQty(e.target.value)}
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
          {busy ? 'Working…' : 'Place trade'}
        </button>

        <div className="wallet-block">
          <div className="field">
            <label>Cash available</label>
            <span className="cash-figure">
              {cash?.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
            </span>
          </div>
          <div className="field">
            <label htmlFor="tf-deposit">Add funds ($)</label>
            <input
              id="tf-deposit"
              type="number"
              min="0"
              step="any"
              placeholder="5000"
              value={deposit}
              onChange={(e) => setDeposit(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addFunds()}
            />
          </div>
          <button className="btn-secondary" onClick={addFunds} disabled={busy}>
            Add to wallet
          </button>
        </div>
      </div>
      <div className="form-hint">
        Backdated trades fill at that date's closing price. Ordering by amount buys fractional shares.
      </div>
      {error && <div className="error-banner">{error}</div>}
    </>
  )
}
