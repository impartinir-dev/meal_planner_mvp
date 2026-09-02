import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, ApiError } from './api'
import type { User } from './types'

type AuthCtx = {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, invite_code: string) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<void>
}

const Ctx = createContext<AuthCtx | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  async function refresh() {
    try {
      const me = await api<User>('/api/auth/me')
      setUser(me)
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) setUser(null)
      else setUser(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
  }, [])

  async function login(email: string, password: string) {
    const res = await api<{ user: User }>('/api/auth/login', { method: 'POST', json: { email, password } })
    setUser(res.user)
  }

  async function register(email: string, password: string, invite_code: string) {
    const res = await api<{ user: User }>('/api/auth/register', {
      method: 'POST',
      json: { email, password, invite_code },
    })
    setUser(res.user)
  }

  async function logout() {
    await api('/api/auth/logout', { method: 'POST' })
    setUser(null)
  }

  return (
    <Ctx.Provider value={{ user, loading, login, register, logout, refresh }}>
      {children}
    </Ctx.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useAuth outside provider')
  return ctx
}
