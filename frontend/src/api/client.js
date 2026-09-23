const BASE = '/api/v1'

export function getToken() {
  return localStorage.getItem('token')
}

export function setToken(token) {
  if (token) localStorage.setItem('token', token)
  else localStorage.removeItem('token')
}

async function request(path, { method = 'GET', body, isForm = false } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (body && !isForm) headers['Content-Type'] = 'application/json'

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  })

  if (res.status === 401) {
    setToken(null)
    window.dispatchEvent(new Event('unauthorized'))
  }

  let data = null
  const text = await res.text()
  if (text) {
    try { data = JSON.parse(text) } catch { data = text }
  }
  if (!res.ok) {
    const detail = data && data.detail
      ? (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))
      : `Request failed (${res.status})`
    throw new Error(detail)
  }
  return data
}

export const api = {
  // auth
  register: (payload) => request('/auth/register', { method: 'POST', body: payload }),
  login: (payload) => request('/auth/login', { method: 'POST', body: payload }),
  me: () => request('/auth/me'),

  // health / models
  health: () => request('/health'),
  modelConfig: () => request('/models/config'),
  testModel: () => request('/models/test', { method: 'POST' }),
  chat: (payload) => request('/models/chat', { method: 'POST', body: payload }),

  // workspaces
  listWorkspaces: () => request('/workspaces'),
  createWorkspace: (payload) => request('/workspaces', { method: 'POST', body: payload }),
  getWorkspace: (id) => request(`/workspaces/${id}`),
  searchWorkspace: (id, q, topK = 5) =>
    request(`/workspaces/${id}/search?q=${encodeURIComponent(q)}&top_k=${topK}`),
  askWorkspace: (id, payload) => request(`/workspaces/${id}/ask`, { method: 'POST', body: payload }),

  // members
  listMembers: (id) => request(`/workspaces/${id}/members`),
  addMember: (id, payload) => request(`/workspaces/${id}/members`, { method: 'POST', body: payload }),

  // documents
  listDocuments: (id) => request(`/workspaces/${id}/documents`),
  uploadDocument: (id, file) => {
    const form = new FormData()
    form.append('file', file)
    return request(`/workspaces/${id}/documents`, { method: 'POST', body: form, isForm: true })
  },
  processDocument: (docId) => request(`/documents/${docId}/process`, { method: 'POST' }),
  indexDocument: (docId) => request(`/documents/${docId}/index`, { method: 'POST' }),
  documentChunks: (docId) => request(`/documents/${docId}/chunks`),

  // audit
  auditLogs: (workspaceId) =>
    request(`/audit-logs?limit=100${workspaceId ? `&workspace_id=${workspaceId}` : ''}`),
}
