import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, Copy, Printer } from 'lucide-react'
import { api, ApiError } from '../api'
import { useAuth } from '../auth'
import type { PlanPayload, ShoppingItem } from '../types'

function itemLine(item: ShoppingItem) {
  return `${item.packs} × ${item.pack_size} ${item.pack_unit}`
}

export default function Shopping() {
  const { user } = useAuth()
  const [payload, setPayload] = useState<PlanPayload | null>(null)
  const [missing, setMissing] = useState(false)
  const [copied, setCopied] = useState(false)
  const [checked, setChecked] = useState<Record<string, boolean>>({})

  useEffect(() => {
    void (async () => {
      try {
        const data = await api<PlanPayload>('/api/plan')
        setPayload(data)
        const key = `nutrimatch.checked.${user?.id}.${data.updated_at}`
        const raw = localStorage.getItem(key)
        if (raw) setChecked(JSON.parse(raw))
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) setMissing(true)
      }
    })()
  }, [user?.id])

  const storageKey = useMemo(
    () => (payload && user ? `nutrimatch.checked.${user.id}.${payload.updated_at}` : null),
    [payload, user],
  )

  function toggle(name: string) {
    const next = { ...checked, [name]: !checked[name] }
    setChecked(next)
    if (storageKey) localStorage.setItem(storageKey, JSON.stringify(next))
  }

  if (missing) {
    return (
      <div className="text-center">
        <Link to="/setup" className="text-brand font-bold text-sm">Zuerst einen Plan erstellen</Link>
      </div>
    )
  }
  if (!payload) return <p className="text-sm text-ink-muted">Lade Einkaufszettel…</p>

  const plan = payload.plan

  function listText() {
    let text = `🛒 Mein Einkaufszettel (${plan.store}) - NutriMatch\nGesamtkosten: ${plan.total_cost.toFixed(2)} € (Ersparnis: ${plan.combined_savings.toFixed(2)} €)\n\n`
    plan.shopping_list.to_buy.forEach((aisle) => {
      text += `📍 ${aisle.aisle}:\n`
      aisle.items.forEach((item) => {
        const tag = item.is_deal ? ' (Angebot)' : ''
        text += `  • [ ] ${item.name} — ${itemLine(item)} - ${item.cost.toFixed(2)} €${tag}\n`
      })
      text += '\n'
    })
    if (plan.shopping_list.already_at_home.length) {
      text += '🏠 Schon im Vorrat:\n'
      plan.shopping_list.already_at_home.forEach((item) => {
        text += `  • ${item.name}\n`
      })
    }
    return text
  }

  async function copyList() {
    const text = listText()
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  function whatsapp() {
    window.open(`https://wa.me/?text=${encodeURIComponent(listText())}`, '_blank')
  }

  return (
    <div className="space-y-8 max-w-3xl mx-auto">
      <div className="bg-surface rounded-2xl p-6 sm:p-8 border border-stone-200/80 flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-muted">Einkaufsliste</span>
            <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-stone-100">{plan.store}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Dein Einkaufszettel</h1>
          <p className="text-xs text-ink-muted">Packungsgrößen, nach Gängen bei {plan.store}.</p>
        </div>
        <div className="flex items-center gap-2 no-print">
          <button type="button" onClick={() => void copyList()} className="px-4 py-2.5 rounded-xl bg-brand text-white text-xs font-bold flex items-center gap-1.5">
            <Copy className="w-3.5 h-3.5" /> {copied ? 'Kopiert' : 'Kopieren'}
          </button>
          <button type="button" onClick={whatsapp} className="px-4 py-2.5 rounded-xl border border-stone-200 text-xs font-bold">
            In WhatsApp öffnen
          </button>
          <button type="button" onClick={() => window.print()} className="px-3.5 py-2.5 rounded-xl border border-stone-200">
            <Printer className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {plan.shopping_list.to_buy.map((aisle) => (
        <div key={aisle.aisle} className="bg-surface rounded-2xl p-6 border border-stone-200/80 space-y-3">
          <div className="flex items-center justify-between border-b border-stone-100 pb-3">
            <span className="font-bold text-base">{aisle.aisle}</span>
            <span className="text-xs text-ink-muted">{aisle.items.length} Artikel</span>
          </div>
          <div className="divide-y divide-stone-100">
            {aisle.items.map((item) => (
              <label key={item.name} className="flex items-center justify-between py-3 cursor-pointer">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={!!checked[item.name]}
                    onChange={() => toggle(item.name)}
                    className="w-5 h-5 accent-brand"
                  />
                  <div>
                    <span className={`text-sm font-semibold block ${checked[item.name] ? 'line-through text-ink-muted' : ''}`}>
                      {item.name}
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-ink-muted">{itemLine(item)}</span>
                      {item.is_deal && (
                        <span className="text-[10px] font-bold px-2 rounded-full bg-amber-50 text-amber-800 border border-amber-200/60">Angebot</span>
                      )}
                    </div>
                  </div>
                </div>
                <span className="text-sm font-extrabold font-mono">{item.cost.toFixed(2)} €</span>
              </label>
            ))}
          </div>
        </div>
      ))}

      {plan.shopping_list.already_at_home.length > 0 && (
        <div className="bg-surface rounded-2xl p-6 border border-stone-200/80 space-y-3">
          <h2 className="font-bold text-base">Schon im Vorrat</h2>
          <ul className="text-sm text-ink-muted space-y-1">
            {plan.shopping_list.already_at_home.map((item) => (
              <li key={item.name}>{item.name}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="bg-surface rounded-2xl p-6 border border-stone-200/80 flex items-center justify-between">
        <div>
          <span className="text-xs text-ink-muted block font-medium">Gesamtsumme an der Kasse</span>
          <span className="text-xs text-brand font-bold">Du sparst {plan.combined_savings.toFixed(2)} € gegenüber Normalpreis</span>
        </div>
        <span className={`text-3xl font-black font-mono ${plan.over_budget ? 'text-red-700' : ''}`}>{plan.total_cost.toFixed(2)} €</span>
      </div>

      <div className="text-center pt-2 no-print">
        <Link to="/plan" className="text-xs font-bold text-brand hover:underline inline-flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" /> Zurück zum Wochenplan
        </Link>
      </div>
    </div>
  )
}
