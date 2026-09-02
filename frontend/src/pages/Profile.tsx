import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import HouseholdEditor, { DEFAULT_MEMBER } from '../components/HouseholdEditor'
import type { HouseholdMember, Meta, Profile as ProfilePayload } from '../types'

export default function Profile() {
  const [meta, setMeta] = useState<Meta | null>(null)
  const [email, setEmail] = useState('')
  const [tier, setTier] = useState('free')
  const [members, setMembers] = useState<HouseholdMember[]>([DEFAULT_MEMBER])
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    void (async () => {
      const m = await api<Meta>('/api/meta')
      setMeta(m)
      const profile = await api<ProfilePayload>('/api/profile')
      setEmail(profile.email)
      setTier(profile.plan_tier)
      setMembers(profile.members?.length ? profile.members : [DEFAULT_MEMBER])
    })()
  }, [])

  async function persist(next: HouseholdMember[]) {
    setMembers(next)
    setSaved(false)
    setError('')
    try {
      const data = await api<ProfilePayload>('/api/profile', { method: 'PUT', json: { members: next } })
      setMembers(data.members)
      setSaved(true)
    } catch {
      setError('Haushalt konnte nicht gespeichert werden.')
    }
  }

  if (!meta) return <p className="text-sm text-ink-muted">Lade Profil…</p>

  const tierLabel = tier === 'premium' ? 'Premium' : tier === 'plus' ? 'Plus' : 'Free'

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <div>
        <p className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">Profil</p>
        <h1 className="text-3xl font-extrabold tracking-tight mt-1">Wer isst mit?</h1>
        <p className="text-sm text-ink-muted mt-1">
          Partner, Kinder, Mitbewohner. Der Wochenplan skaliert auf diese Personen.
        </p>
      </div>
      <div className="rounded-2xl border border-zinc-200 bg-surface px-4 py-3 text-sm flex items-center justify-between gap-3">
        <span className="truncate">{email}</span>
        <span className="text-[10px] font-extrabold uppercase tracking-wider bg-brand text-white px-1.5 py-0.5 rounded">{tierLabel}</span>
      </div>
      <div className="rounded-3xl border border-zinc-200 bg-surface p-6 space-y-4">
        <HouseholdEditor members={members} onChange={(next) => void persist(next)} meta={meta} />
        {saved && <p className="text-xs font-semibold text-brand">Gespeichert.</p>}
        {error && <p className="text-xs text-red-700">{error}</p>}
      </div>
      <p className="text-sm text-ink-muted">
        Nächster Plan nimmt diesen Haushalt.{' '}
        <Link to="/setup" className="text-brand font-bold">
          Neuen Plan rechnen
        </Link>
      </p>
    </div>
  )
}
