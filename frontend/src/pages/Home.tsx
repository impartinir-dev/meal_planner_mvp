import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { api, ApiError } from '../api'

export default function Home() {
  const [to, setTo] = useState<string | null>(null)
  useEffect(() => {
    void (async () => {
      try {
        await api('/api/plan')
        setTo('/plan')
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) setTo('/setup')
        else setTo('/setup')
      }
    })()
  }, [])
  if (!to) return <p className="text-sm text-ink-muted">Lade…</p>
  return <Navigate to={to} replace />
}
