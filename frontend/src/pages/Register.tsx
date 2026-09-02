import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { ApiError } from '../api'

export default function Register() {
  const { register } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [invite, setInvite] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await register(email, password, invite)
      nav('/setup')
    } catch (err) {
      if (err instanceof ApiError) {
        const code = (err.body as { error?: string })?.error
        if (code === 'invalid_invite') setError('Dieser Einladungscode ist ungültig oder schon benutzt.')
        else if (code === 'email_taken') setError('Diese E-Mail ist bereits registriert.')
        else if (code === 'password_too_short') setError('Passwort mindestens 8 Zeichen.')
        else setError('Registrierung fehlgeschlagen.')
      } else setError('Registrierung fehlgeschlagen.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-full flex items-center justify-center px-4 py-16 bg-canvas font-sans">
      <form onSubmit={onSubmit} className="w-full max-w-md bg-surface rounded-3xl p-8 border border-stone-200/80 space-y-5">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-brand">NutriMatch</p>
          <h1 className="text-2xl font-extrabold mt-1">Registrieren</h1>
          <p className="text-sm text-ink-muted mt-1">Du brauchst einen Einladungscode von jemandem, der schon dabei ist.</p>
        </div>
        {error && <p className="text-sm text-red-700 bg-red-50 rounded-xl px-3 py-2">{error}</p>}
        <label className="block text-xs font-bold uppercase tracking-wider text-ink-muted">
          Einladungscode
          <input
            required
            value={invite}
            onChange={(e) => setInvite(e.target.value.toUpperCase())}
            className="mt-1 w-full rounded-xl border border-stone-200 px-3 py-2.5 text-sm font-mono tracking-widest uppercase"
          />
        </label>
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
          Passwort (min. 8 Zeichen)
          <input
            type="password"
            required
            minLength={8}
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
          {busy ? '…' : 'Konto erstellen'}
        </button>
        <p className="text-xs text-ink-muted text-center">
          Schon registriert? <Link to="/login" className="text-brand font-semibold">Zum Login</Link>
        </p>
      </form>
    </div>
  )
}
