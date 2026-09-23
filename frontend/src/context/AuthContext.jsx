import { createContext, useContext, useEffect, useState } from 'react'
import { api, getToken, setToken } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(!!getToken())

  useEffect(() => {
    const onUnauthorized = () => setUser(null)
    window.addEventListener('unauthorized', onUnauthorized)
    return () => window.removeEventListener('unauthorized', onUnauthorized)
  }, [])

  useEffect(() => {
    if (!getToken()) {
      setUser(null)
      setLoading(false)
      return
    }
    api.me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = async (email, password) => {
    const data = await api.login({ email, password })
    setToken(data.access_token)
    const me = await api.me()
    setUser(me)
    return me
  }

  const register = async (full_name, email, password) => {
    await api.register({ full_name, email, password })
    return login(email, password)
  }

  const logout = () => {
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
