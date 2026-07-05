import { useState } from 'react'

export default function Sidebar({ portfolios, activeId, onSelect, onCreate, onDelete }) {
  const [name, setName] = useState('')
  const [cash, setCash] = useState('')
  const [busy, setBusy] = useState(false)

  const create = async () => {
    const amount = parseFloat(cash)
    if (!name.trim() || !amount || amount <= 0) return
    setBusy(true)
    try {
      await onCreate(name.trim(), amount)
      setName('')
      setCash('')
    } finally {
      setBusy(false)
    }
  }

  return (
    <aside className="sidebar">
      <div className="logo">Paper<span>Desk</span></div>
      <div className="tagline">US equity portfolio simulator</div>

      <div className="section-label">Portfolios</div>
      {portfolios.map((p) => (
        <button
          key={p.id}
          className={`portfolio-item ${p.id === activeId ? 'active' : ''}`}
          onClick={() => onSelect(p.id)}
        >
          <span>{p.name}</span>
          <span
            className="delete"
            role="button"
            aria-label={`Delete ${p.name}`}
            onClick={(e) => { e.stopPropagation(); onDelete(p.id) }}
          >
            ×
          </span>
        </button>
      ))}

      <div className="new-portfolio">
        <div className="section-label">New portfolio</div>
        <input
          placeholder="Name (e.g. Tech Tilt)"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          placeholder="Starting cash (USD)"
          type="number"
          min="1"
          value={cash}
          onChange={(e) => setCash(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && create()}
        />
        <button className="btn-primary" onClick={create} disabled={busy}>
          Create portfolio
        </button>
      </div>
    </aside>
  )
}
