import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'

type InviteRow = { code: string; used: boolean; used_by_email: string | null }
type AdminUser = { id: number; email: string; is_admin: boolean; is_pro: boolean }

export default function Invites() {
  const { user } = useAuth()
  const [invites, setInvites] = useState<InviteRow[]>([])
  const [users, setUsers] = useState<AdminUser[]>([])
  const [copied, setCopied] = useState('')
  const [notice, setNotice] = useState('')

  async function load() {
    const data = await api<{ invites: InviteRow[] }>('/api/invites')
    setInvites(data.invites)
    const u = await api<{ users: AdminUser[] }>('/api/admin/users')
    setUsers(u.users)
  }

  useEffect(() => {
    if (user?.is_admin) void load()
  }, [user?.is_admin])

  if (!user?.is_admin) {
    return <p className="text-sm text-ink-muted">Nur für Admins.</p>
  }

  async function createCode() {
    const res = await api<{ code: string }>('/api/invites', { method: 'POST' })
    await navigator.clipboard.writeText(res.code)
    setCopied(res.code)
    await load()
  }

  async function resetPassword(id: number, email: string) {
    const password = window.prompt(`Neues Passwort für ${email} (min. 8 Zeichen)`)
    if (!password) return
    await api(`/api/admin/users/${id}/password`, { method: 'POST', json: { password } })
    setNotice(`Passwort für ${email} gesetzt.`)
  }

  async function togglePro(u: AdminUser) {
    await api(`/api/admin/users/${u.id}/pro`, { method: 'POST', json: { is_pro: !u.is_pro } })
    await load()
  }

  return (
    <div className="max-w-xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-extrabold">Admin</h1>
          <p className="text-sm text-ink-muted">Einladungen, Passwörter, Pro-Freischaltung.</p>
        </div>
        <button type="button" onClick={() => void createCode()} className="px-4 py-2.5 rounded-xl bg-brand text-white text-xs font-bold">
          Code erzeugen
        </button>
      </div>
      {copied && <p className="text-xs text-brand font-semibold">Kopiert: {copied}</p>}
      {notice && <p className="text-xs text-brand font-semibold">{notice}</p>}
      <div className="bg-surface rounded-2xl border border-zinc-200/80 divide-y divide-zinc-100">
        {invites.map((inv) => (
          <div key={inv.code} className="px-4 py-3 flex items-center justify-between text-sm">
            <span className="font-mono font-bold tracking-widest">{inv.code}</span>
            <span className="text-xs text-ink-muted">{inv.used ? `genutzt von ${inv.used_by_email}` : 'frei'}</span>
          </div>
        ))}
      </div>
      <div>
        <h2 className="font-bold mb-2">Nutzer</h2>
        <div className="bg-surface rounded-2xl border border-zinc-200/80 divide-y divide-zinc-100">
          {users.map((u) => (
            <div key={u.id} className="px-4 py-3 flex flex-wrap items-center justify-between gap-2 text-sm">
              <span>{u.email} {u.is_admin && <span className="text-[10px] uppercase text-ink-muted">admin</span>}</span>
              <div className="flex gap-2">
                <button type="button" className="text-xs font-bold text-brand" onClick={() => void togglePro(u)}>
                  {u.is_pro ? 'Pro an' : 'Free'}
                </button>
                <button type="button" className="text-xs font-bold" onClick={() => void resetPassword(u.id, u.email)}>
                  Passwort
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
