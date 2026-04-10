import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react'
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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(sessionStorage.getItem('access_token'))
  const [user, setUser] = useState<User | null>(null)

  const login = useCallback(async (username: string, password: string) => {
    const { data } = await api.post('/auth/login', { username, password })
    sessionStorage.setItem('access_token', data.access_token)
    setToken(data.access_token)
    // Decode user from JWT payload (base64)
    const payload = JSON.parse(atob(data.access_token.split('.')[1]))
    setUser({ id: payload.sub, email: '', username, role: payload.role, is_active: true, created_at: '' })
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
