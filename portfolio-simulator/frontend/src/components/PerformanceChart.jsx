import { useState } from 'react'
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

const SERIES = [
  { key: 'portfolio', label: 'Portfolio', color: '#2743e0', cls: 'lg-portfolio' },
  { key: 'sp500', label: 'S&P 500', color: '#b26a00', cls: 'lg-sp500' },
  { key: 'nasdaq', label: 'Nasdaq', color: '#6d28d9', cls: 'lg-nasdaq' },
]

export default function PerformanceChart({ history }) {
  const [visible, setVisible] = useState({ portfolio: true, sp500: true, nasdaq: true })
  const points = history?.points || []

  return (
    <div className="card">
      <div className="card-header-row">
        <h2>Performance vs benchmarks (growth of 100)</h2>
        <div className="legend-toggles">
          {SERIES.map((s) => (
            <button
              key={s.key}
              className={`${s.cls} ${visible[s.key] ? 'on' : ''}`}
              onClick={() => setVisible((v) => ({ ...v, [s.key]: !v[s.key] }))}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {points.length < 2 ? (
        <div className="loading">
          The chart appears once there are at least two trading days of history. Make a trade to get started.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={points} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
            <CartesianGrid stroke="#eef1f4" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fontFamily: 'IBM Plex Mono' }}
              minTickGap={48}
              tickLine={false}
              axisLine={{ stroke: '#dbe1e8' }}
            />
            <YAxis
              tick={{ fontSize: 11, fontFamily: 'IBM Plex Mono' }}
              domain={['auto', 'auto']}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={{ fontFamily: 'IBM Plex Mono', fontSize: 12, borderRadius: 8, border: '1px solid #dbe1e8' }}
              formatter={(value, name) => [Number(value).toFixed(2), SERIES.find((s) => s.key === name)?.label || name]}
            />
            {SERIES.filter((s) => visible[s.key]).map((s) => (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                stroke={s.color}
                strokeWidth={s.key === 'portfolio' ? 2.4 : 1.6}
                dot={false}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
