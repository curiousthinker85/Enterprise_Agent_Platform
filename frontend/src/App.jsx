import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import WorkspaceDetail from './pages/WorkspaceDetail'
import Chat from './pages/Chat'
import Audit from './pages/Audit'
import { useAuth } from './context/AuthContext'

function Protected({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="muted" style={{ padding: 40 }}>Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={<Protected><Layout /></Protected>}>
        <Route index element={<Dashboard />} />
        <Route path="workspaces/:id" element={<WorkspaceDetail />} />
        <Route path="chat" element={<Chat />} />
        <Route path="audit" element={<Audit />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
