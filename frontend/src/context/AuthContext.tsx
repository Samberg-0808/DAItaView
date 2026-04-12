import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import api from '@/api/client'
import type { User } from '@/types'

interface AuthContextValue {
  user: User | null
  token: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  isAdmin: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

function decodeUserFromToken(token: string): User | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    if (!payload.sub || !payload.role) return null
    return { id: payload.sub, email: '', username: payload.username ?? '', role: payload.role, is_active: true, created_at: '' }
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(sessionStorage.getItem('access_token'))
  const [user, setUser] = useState<User | null>(() => {
    const stored = sessionStorage.getItem('access_token')
    return stored ? decodeUserFromToken(stored) : null
  })

  const login = useCallback(async (username: string, password: string) => {
    const { data } = await api.post('/auth/login', { username, password })
    sessionStorage.setItem('access_token', data.access_token)
    setToken(data.access_token)
    const decoded = decodeUserFromToken(data.access_token)
    // username may not be in old tokens yet — fall back to the form value
    setUser(decoded ? { ...decoded, username: decoded.username || username } : null)
  }, [])

  const logout = useCallback(async () => {
    try { await api.post('/auth/logout') } catch {}
    sessionStorage.removeItem('access_token')
    setToken(null)
    setUser(null)
  }, [])

  const isAdmin = user?.role === 'super_admin' || user?.role === 'data_admin'

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isAdmin }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
