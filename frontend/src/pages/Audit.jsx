import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function Audit() {
  const [logs, setLogs] = useState([])
  const [workspaces, setWorkspaces] = useState([])
  const [filter, setFilter] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api.listWorkspaces().then(setWorkspaces).catch(() => {})
  }, [])

  useEffect(() => {
    api.auditLogs(filter || undefined).then(setLogs).catch((e) => setError(e.message))
  }, [filter])

  return (
    <div>
      <h1>Audit Logs</h1>
      <div className="card">
        <label>Filter by workspace</label>
        <select value={filter} onChange={(e) => setFilter(e.target.value)} style={{ maxWidth: 300 }}>
          <option value="">All workspaces</option>
          {workspaces.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
        </select>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="card">
        {logs.length === 0 ? (
          <p className="muted">No audit entries yet.</p>
        ) : (
          <table>
            <thead>
              <tr><th>Time</th><th>Action</th><th>User</th><th>Workspace</th><th>Resource</th><th>Details</th></tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id}>
                  <td>{new Date(l.created_at).toLocaleString()}</td>
                  <td><span className="badge">{l.action}</span></td>
                  <td>{l.user_id ?? '—'}</td>
                  <td>{l.workspace_id ?? '—'}</td>
                  <td>{l.resource_type ? `${l.resource_type} #${l.resource_id}` : '—'}</td>
                  <td className="muted">{l.details ? JSON.stringify(l.details) : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
