import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

const TYPES = ['GENERAL', 'HR', 'FINANCE', 'AUDIT']

export default function Dashboard() {
  const [workspaces, setWorkspaces] = useState([])
  const [health, setHealth] = useState(null)
  const [modelConfig, setModelConfig] = useState(null)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ name: '', workspace_type: 'GENERAL' })
  const [busy, setBusy] = useState(false)

  const load = () =>
    api.listWorkspaces().then(setWorkspaces).catch((e) => setError(e.message))

  useEffect(() => {
    load()
    api.health().then(setHealth).catch(() => {})
    api.modelConfig().then(setModelConfig).catch(() => {})
  }, [])

  const create = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await api.createWorkspace(form)
      setForm({ name: '', workspace_type: 'GENERAL' })
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <h1>Workspaces</h1>

      {health && (
        <div className="card">
          <div className="flex" style={{ justifyContent: 'space-between', flexWrap: 'wrap' }}>
            <div>
              <strong>{health.app}</strong> <span className="muted">v{health.version} · {health.environment}</span>
              <div className="success" style={{ margin: '4px 0 0' }}>● API healthy</div>
            </div>
            {modelConfig && (
              <div className="muted" style={{ textAlign: 'right' }}>
                Model: {modelConfig.default_provider} / {modelConfig.default_model || 'not set'}
                <br />
                API key {modelConfig.api_key_configured ? 'configured ✓' : 'missing ✗'}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="card">
        <h2>New workspace</h2>
        <form onSubmit={create} className="flex" style={{ alignItems: 'flex-end' }}>
          <div className="grow">
            <label>Name</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. HR Policies" required />
          </div>
          <div>
            <label>Type</label>
            <select value={form.workspace_type} onChange={(e) => setForm({ ...form, workspace_type: e.target.value })}>
              {TYPES.map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
          <button disabled={busy}>{busy ? 'Creating…' : 'Create'}</button>
        </form>
      </div>

      {error && <div className="error">{error}</div>}

      {workspaces.length === 0 ? (
        <p className="muted">No workspaces yet — create one above.</p>
      ) : (
        <div className="grid">
          {workspaces.map((w) => (
            <Link key={w.id} to={`/workspaces/${w.id}`} className="card" style={{ color: 'inherit' }}>
              <h2>{w.name}</h2>
              <span className="badge">{w.workspace_type}</span>
              <div className="muted" style={{ marginTop: 8 }}>
                Created {new Date(w.created_at).toLocaleDateString()}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
