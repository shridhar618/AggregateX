// Thin client for the local VeriSketch API. No provider credentials ever pass
// through the browser: hosted providers are configured on the backend only.
const BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(status, message, data) {
    super(message)
    this.status = status
    this.data = data || {}
  }

  get isProviderError() {
    return Boolean(this.data?.provider_error)
  }

  get isOffline() {
    return this.status === 0
  }
}

async function request(path, { method = 'GET', body, signal, raw = false } = {}) {
  let res
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      signal,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch (err) {
    if (err?.name === 'AbortError') throw err
    throw new ApiError(0, 'The local VeriSketch engine is not reachable. Start it with “npm run dev:api”.')
  }
  if (!res.ok) {
    let data = {}
    try {
      data = await res.json()
    } catch {
      /* non-JSON error body */
    }
    const detail = typeof data.detail === 'string' ? data.detail : `Request failed (${res.status})`
    throw new ApiError(res.status, detail, data)
  }
  if (raw) return res
  if (res.status === 204) return null
  return res.json()
}

/** Resolve an API-relative asset path (e.g. image URLs returned by the API). */
export const assetUrl = (path) => {
  if (!path) return null
  if (BASE === '/api') return path
  return BASE.replace(/\/api$/, '') + path
}

export const api = {
  health: (signal) => request('/health', { signal }),
  catalog: () => request('/catalog'),
  stats: () => request('/stats'),
  activity: (limit = 20) => request(`/activity?limit=${limit}`),
  storage: () => request('/storage'),

  extract: (description) => request('/traits/extract', { method: 'POST', body: { description } }),
  merge: (descriptions) => request('/witnesses/merge', { method: 'POST', body: { descriptions } }),
  parseRefine: (instruction, profile) => request('/refine/parse', { method: 'POST', body: { instruction, profile } }),
  applyRefine: (profile, changes) => request('/refine/apply', { method: 'POST', body: { profile, changes } }),

  render: (profile, caption, signal) => request('/render', { method: 'POST', body: { profile, caption }, signal }),
  renderPng: async (profile, caption) => {
    const res = await request('/render.png', { method: 'POST', body: { profile, caption }, raw: true })
    return res.blob()
  },

  listSketches: (q) => request(`/sketches${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  getSketch: (id) => request(`/sketches/${encodeURIComponent(id)}`),
  generate: (payload) => request('/sketches/generate', { method: 'POST', body: payload }),
  addRevision: (id, payload) => request(`/sketches/${encodeURIComponent(id)}/revisions`, { method: 'POST', body: payload }),
  updateSketch: (id, patch) => request(`/sketches/${encodeURIComponent(id)}`, { method: 'PATCH', body: patch }),
  deleteSketch: (id) => request(`/sketches/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  deleteAll: () => request('/data/delete-all', { method: 'POST', body: { confirm: 'DELETE' } }),

  exportJsonUrl: (id) => `${BASE}/sketches/${encodeURIComponent(id)}/export.json?download=true`,
  reportUrl: (id) => `${BASE}/sketches/${encodeURIComponent(id)}/report`,
  pngDownloadUrl: (id, n) => `${BASE}/sketches/${encodeURIComponent(id)}/revisions/${n}/image.png?download=true`,
}
