import { useCallback, useEffect, useState } from 'react'
import { api } from './api.js'
import Sidebar from './components/Sidebar.jsx'
import PortfolioView from './components/PortfolioView.jsx'

export default function App() {
  const [portfolios, setPortfolios] = useState([])
  const [activeId, setActiveId] = useState(null)

  const refresh = useCallback(async () => {
    const list = await api.listPortfolios()
    setPortfolios(list)
    setActiveId((current) => {
      if (current && list.some((p) => p.id === current)) return current
      return list.length ? list[0].id : null
    })
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const handleCreate = async (name, cash) => {
    const p = await api.createPortfolio(name, cash)
    await refresh()
    setActiveId(p.id)
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this portfolio and all its trades?')) return
    await api.deletePortfolio(id)
    await refresh()
  }

  return (
    <div className="app">
      <Sidebar
        portfolios={portfolios}
        activeId={activeId}
        onSelect={setActiveId}
        onCreate={handleCreate}
        onDelete={handleDelete}
      />
      <main className="main">
        {activeId ? (
          <PortfolioView key={activeId} portfolioId={activeId} />
        ) : (
          <div className="empty-state">
            <h2>No portfolios yet</h2>
            <p>Create your first paper portfolio from the sidebar — name it and give it starting cash.</p>
          </div>
        )}
      </main>
    </div>
  )
}
