export default function TickerStrip({ holdings }) {
  const items = holdings.map((h) => {
    const chg = h.day_change_pct
    return (
      <span className="tick" key={h.symbol}>
        <span className="sym">{h.symbol}</span>
        <span className="px">{h.price?.toFixed(2)}</span>
        {chg != null && (
          <span className={`chg ${chg >= 0 ? 'up' : 'down'}`}>
            {chg >= 0 ? '▲' : '▼'} {Math.abs(chg).toFixed(2)}%
          </span>
        )}
      </span>
    )
  })

  // Duplicate the content so the loop is seamless
  return (
    <div className="ticker-strip" aria-label="Holdings ticker">
      <div className="ticker-track">
        {items}
        {items.map((el) => ({ ...el, key: el.key + '-b' }))}
      </div>
    </div>
  )
}
