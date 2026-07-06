async function request(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (body.detail) detail = typeof body.detail === 'string' ? body.detail : detail
    } catch { /* keep default */ }
    throw new Error(detail)
  }
  return res.json()
}

export const api = {
  listPortfolios: () => request('/portfolios'),
  createPortfolio: (name, starting_cash) =>
    request('/portfolios', { method: 'POST', body: JSON.stringify({ name, starting_cash }) }),
  deletePortfolio: (id) => request(`/portfolios/${id}`, { method: 'DELETE' }),
  summary: (id) => request(`/portfolios/${id}/summary`),
  history: (id, range = 'max') => request(`/portfolios/${id}/history?range=${range}`),
  deposit: (id, amount) =>
    request(`/portfolios/${id}/deposits`, { method: 'POST', body: JSON.stringify({ amount }) }),
  analytics: (id) => request(`/portfolios/${id}/analytics`),
  trade: (id, payload) =>
    request(`/portfolios/${id}/transactions`, { method: 'POST', body: JSON.stringify(payload) }),
  removeHolding: (id, symbol) =>
    request(`/portfolios/${id}/holdings/${symbol}`, { method: 'DELETE' }),
}
