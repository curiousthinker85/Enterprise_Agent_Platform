import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ full_name: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await register(form.full_name, form.email, form.password)
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-box card">
      <h1>Create account</h1>
      <form onSubmit={submit}>
        <label>Full name</label>
        <input value={form.full_name} onChange={set('full_name')} required autoFocus />
        <label>Email</label>
        <input type="email" value={form.email} onChange={set('email')} required />
        <label>Password</label>
        <input type="password" value={form.password} onChange={set('password')} required minLength={8} />
        {error && <div className="error">{error}</div>}
        <div style={{ marginTop: 16 }} className="flex">
          <button disabled={busy}>{busy ? 'Creating…' : 'Create account'}</button>
          <Link to="/login">Back to sign in</Link>
        </div>
      </form>
    </div>
  )
}
