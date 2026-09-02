import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { ApiError } from '../api'

export default function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(email, password)
      nav('/')
    } catch (err) {
      setError(err instanceof ApiError ? 'E-Mail oder Passwort stimmt nicht.' : 'Login fehlgeschlagen.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-full flex items-center justify-center px-4 py-16 bg-canvas font-sans">
      <form onSubmit={onSubmit} className="w-full max-w-md bg-surface rounded-3xl p-8 border border-stone-200/80 space-y-5">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-brand">NutriMatch</p>
          <h1 className="text-2xl font-extrabold mt-1">Anmelden</h1>
          <p className="text-sm text-ink-muted mt-1">Nur mit Einladung. Für dich und Menschen, die du einlädst.</p>
        </div>
        {error && <p className="text-sm text-red-700 bg-red-50 rounded-xl px-3 py-2">{error}</p>}
        <label className="block text-xs font-bold uppercase tracking-wider text-ink-muted">
          E-Mail
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-xl border border-stone-200 px-3 py-2.5 text-sm font-medium"
          />
        </label>
        <label className="block text-xs font-bold uppercase tracking-wider text-ink-muted">
          Passwort
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-xl border border-stone-200 px-3 py-2.5 text-sm font-medium"
          />
        </label>
        <button
          type="submit"
          disabled={busy}
          className="w-full py-3 rounded-xl bg-brand hover:bg-brand-light text-white font-bold text-sm disabled:opacity-60"
        >
          {busy ? '…' : 'Einloggen'}
        </button>
        <p className="text-xs text-ink-muted text-center">
          Noch kein Konto? <Link to="/register" className="text-brand font-semibold">Mit Einladungscode registrieren</Link>
        </p>
      </form>
    </div>
  )
}
