import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Layout() {
  const { user, logout } = useAuth()
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">⚡ Agent Portal</div>
        <nav>
          <NavLink to="/" end>Workspaces</NavLink>
          <NavLink to="/chat">AI Chat</NavLink>
          <NavLink to="/audit">Audit Logs</NavLink>
        </nav>
        <div style={{ marginTop: 'auto' }}>
          <div className="muted" style={{ marginBottom: 8 }}>{user?.full_name || user?.email}</div>
          <button className="danger small" onClick={logout}>Log out</button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
