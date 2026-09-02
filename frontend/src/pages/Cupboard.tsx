import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api'
import { useAuth } from '../auth'

type Item = { id: number; name: string; quantity: number; unit: string; source: string }

export default function Cupboard() {
  const { user } = useAuth()
  const [items, setItems] = useState<Item[]>([])
  const [ingredients, setIngredients] = useState<string[]>([])
  const [name, setName] = useState('Reis')
  const [qty, setQty] = useState('500')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [blocked, setBlocked] = useState(false)

  async function load() {
    try {
      const data = await api<{ items: Item[] }>('/api/cupboard/')
      setItems(data.items)
      const meta = await api<{ ingredients: string[] }>('/api/meta')
      setIngredients(meta.ingredients)
      if (meta.ingredients[0]) setName((current) => current || meta.ingredients[0])
    } catch (err) {
      if (err instanceof ApiError && err.status === 402) setBlocked(true)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  if (!user?.is_pro || blocked) {
    return (
      <div className="text-center space-y-3">
        <p className="text-ink-muted">Der Vorratsschrank mit Kassenbon-Scan ist Teil von NutriMatch Pro.</p>
        <Link to="/pro" className="text-brand font-bold text-sm">Zu Pro</Link>
      </div>
    )
  }

  async function add(e: FormEvent) {
    e.preventDefault()
    await api('/api/cupboard/', { method: 'POST', json: { name, quantity: Number(qty) } })
    setQty('500')
    await load()
  }

  async function remove(id: number) {
    await api(`/api/cupboard/${id}`, { method: 'DELETE' })
    await load()
  }

  async function scan(file: File) {
    setBusy(true)
    setMessage('')
    try {
      const body = new FormData()
      body.append('file', file)
      const res = await fetch('/api/cupboard/scan', { method: 'POST', credentials: 'include', body })
      const data = await res.json()
      if (res.status === 503) setMessage('OCR ist nicht konfiguriert (XAI_API_KEY).')
      else if (!res.ok) setMessage('Bon konnte nicht gelesen werden.')
      else setMessage(`${data.count} Artikel aus dem Bon übernommen.`)
      await load()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold">Vorratsschrank</h1>
        <p className="text-sm text-ink-muted">Was du schon hast, kauft der Plan nicht nochmal. Kassenbon → Pro.</p>
      </div>

      <label className="block bg-stone-900 text-white rounded-2xl p-6 cursor-pointer text-center">
        <span className="font-bold text-sm">{busy ? 'Bon wird gelesen…' : 'Kassenbon fotografieren / hochladen'}</span>
        <input
          type="file"
          accept="image/jpeg,image/png"
          className="hidden"
          disabled={busy}
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) void scan(file)
          }}
        />
      </label>
      {message && <p className="text-sm text-brand font-semibold">{message}</p>}

      <form onSubmit={(e) => void add(e)} className="flex gap-2">
        <select value={name} onChange={(e) => setName(e.target.value)} className="flex-1 rounded-xl border border-stone-200 px-3 py-2 text-sm">
          {ingredients.map((ing) => (
            <option key={ing} value={ing}>{ing}</option>
          ))}
        </select>
        <input value={qty} onChange={(e) => setQty(e.target.value)} className="w-24 rounded-xl border border-stone-200 px-3 py-2 text-sm" />
        <button type="submit" className="px-4 rounded-xl bg-brand text-white text-xs font-bold">Hinzufügen</button>
      </form>

      <div className="bg-surface rounded-2xl border border-stone-200 divide-y divide-stone-100">
        {items.map((item) => (
          <div key={item.id} className="px-4 py-3 flex items-center justify-between text-sm">
            <div>
              <span className="font-semibold">{item.name}</span>
              <span className="text-ink-muted text-xs ml-2">{item.quantity} {item.unit} · {item.source}</span>
            </div>
            <button type="button" className="text-xs text-red-700 font-bold" onClick={() => void remove(item.id)}>Entfernen</button>
          </div>
        ))}
        {items.length === 0 && <p className="p-4 text-sm text-ink-muted">Noch leer. Scan oder manuell ergänzen.</p>}
      </div>
    </div>
  )
}
