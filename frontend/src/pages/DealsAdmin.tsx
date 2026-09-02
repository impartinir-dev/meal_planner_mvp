import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'

type Deal = {
  ingredient: string
  offer_price: number
  regular_price: number
  unit: string
  discount_percent: number
  badge: string
}

export default function DealsAdmin() {
  const { user } = useAuth()
  const [week, setWeek] = useState('')
  const [stores, setStores] = useState<Record<string, Deal[]>>({})
  const [saved, setSaved] = useState('')

  useEffect(() => {
    if (!user?.is_admin) return
    void (async () => {
      const data = await api<{ deals: { week: string; stores: Record<string, Deal[]> } }>('/api/admin/deals')
      setWeek(data.deals.week)
      setStores(data.deals.stores)
    })()
  }, [user?.is_admin])

  if (!user?.is_admin) return <p className="text-sm text-ink-muted">Nur für Admins.</p>

  async function save(e: FormEvent) {
    e.preventDefault()
    await api('/api/admin/deals', { method: 'PUT', json: { week, stores } })
    setSaved('Gespeichert. Neue Pläne nutzen diese KW.')
  }

  function updateDeal(store: string, idx: number, field: keyof Deal, value: string) {
    setStores((prev) => {
      const list = [...(prev[store] || [])]
      const row = { ...list[idx] }
      if (field === 'offer_price' || field === 'regular_price' || field === 'discount_percent') {
        row[field] = Number(value)
      } else {
        row[field] = value as never
      }
      list[idx] = row
      return { ...prev, [store]: list }
    })
  }

  return (
    <form onSubmit={(e) => void save(e)} className="space-y-6 max-w-3xl mx-auto">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold">Wochenangebote</h1>
          <p className="text-sm text-ink-muted">Zehn Minuten, jede Woche. KW-Label sichtbar in der App.</p>
        </div>
        <label className="text-xs font-bold uppercase tracking-wider text-ink-muted">
          KW
          <input value={week} onChange={(e) => setWeek(e.target.value)} className="mt-1 block rounded-xl border border-stone-200 px-3 py-2 font-mono" />
        </label>
      </div>
      {Object.entries(stores).map(([store, deals]) => (
        <div key={store} className="bg-surface rounded-2xl border border-stone-200 p-4 space-y-2">
          <h2 className="font-bold">{store}</h2>
          {deals.map((deal, idx) => (
            <div key={`${store}-${idx}`} className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
              <input className="border rounded-lg px-2 py-1" value={deal.ingredient} onChange={(e) => updateDeal(store, idx, 'ingredient', e.target.value)} />
              <input className="border rounded-lg px-2 py-1" value={deal.offer_price} onChange={(e) => updateDeal(store, idx, 'offer_price', e.target.value)} />
              <input className="border rounded-lg px-2 py-1" value={deal.regular_price} onChange={(e) => updateDeal(store, idx, 'regular_price', e.target.value)} />
              <input className="border rounded-lg px-2 py-1" value={deal.badge} onChange={(e) => updateDeal(store, idx, 'badge', e.target.value)} />
              <input className="border rounded-lg px-2 py-1" value={deal.discount_percent} onChange={(e) => updateDeal(store, idx, 'discount_percent', e.target.value)} />
            </div>
          ))}
        </div>
      ))}
      <button type="submit" className="px-5 py-3 rounded-xl bg-brand text-white text-sm font-bold">Angebote speichern</button>
      {saved && <p className="text-sm text-brand font-semibold">{saved}</p>}
    </form>
  )
}
