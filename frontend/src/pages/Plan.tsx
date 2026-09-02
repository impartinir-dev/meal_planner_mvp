import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Lock, Moon, RefreshCw, ShoppingBag, Sun, Tag, Unlock, Utensils, X } from 'lucide-react'
import { api, ApiError } from '../api'
import type { Meal, Plan, PlanPayload } from '../types'

const RELAX: Record<string, string> = {
  variety: 'Katalog zu klein — einzelne Gerichte wiederholen sich',
  budget: 'Budget konnte nicht eingehalten werden',
  macros: 'Kalorien/Protein-Ziel nur näherungsweise',
  catalog_short: 'Zu wenige Rezepte in einem Slot für 7 einzigartige Tage',
  diet: 'Ernährungsziel aufgeweicht, damit der Plan füllbar bleibt',
}

const SLOT_META: Record<string, { label: string; Icon: typeof Sun; short: string }> = {
  Frühstück: { label: 'Frühstück', Icon: Sun, short: 'Früh' },
  Mittagessen: { label: 'Mittagessen', Icon: Utensils, short: 'Mittag' },
  Abendessen: { label: 'Abendessen', Icon: Moon, short: 'Abend' },
}

const SLOTS = ['Frühstück', 'Mittagessen', 'Abendessen']

function formatQty(qty: number, unit: string) {
  if (unit === 'Stück') {
    const rounded = Math.round(qty * 10) / 10
    return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1)
  }
  return String(Math.max(1, Math.round(qty)))
}

function leftoverCount(plan: Plan) {
  return plan.shopping_list.already_at_home?.length || 0
}

export default function PlanPage() {
  const [payload, setPayload] = useState<PlanPayload | null>(null)
  const [open, setOpen] = useState<{ day: number; slot: string } | null>(null)
  const [swapKey, setSwapKey] = useState<string | null>(null)
  const [missing, setMissing] = useState(false)
  const [mobileDay, setMobileDay] = useState(0)

  useEffect(() => {
    void (async () => {
      try {
        const data = await api<PlanPayload>('/api/plan')
        setPayload(data)
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) setMissing(true)
      }
    })()
  }, [])

  if (missing) {
    return (
      <div className="text-center space-y-3">
        <p className="text-ink-muted">Noch kein Wochenplan.</p>
        <Link to="/setup" className="text-brand font-bold text-sm">Zum Konfigurator</Link>
      </div>
    )
  }
  if (!payload) return <p className="text-sm text-ink-muted">Lade Plan…</p>

  const plan: Plan = payload.plan

  function mealAt(day: number, slot: string) {
    return plan.days_plan[day]?.meals.find((m) => m.category === slot)
  }

  async function swap(day: number, meal: Meal) {
    setSwapKey(`${day}-${meal.category}`)
    try {
      const data = await api<PlanPayload>('/api/plan/swap', {
        method: 'POST',
        json: { day_index: day, category: meal.category, current_id: meal.id },
      })
      setPayload(data)
    } finally {
      setSwapKey(null)
    }
  }

  async function logStatus(day: number, meal: Meal, status: 'cooked' | 'skipped' | null) {
    const data = await api<PlanPayload>('/api/plan/log', {
      method: 'POST',
      json: { day_index: day, category: meal.category, status: status || '' },
    })
    setPayload(data)
  }

  async function neverAgain(meal: Meal) {
    if (!window.confirm(`„${meal.name}“ nie wieder vorschlagen?`)) return
    const data = await api<PlanPayload & { ids: string[] }>(`/api/recipes/${meal.id}/never-again`, { method: 'POST' })
    if (data.plan) setPayload(data)
  }

  async function lock(day: number, meal: Meal) {
    const data = await api<PlanPayload>('/api/plan/lock', {
      method: 'POST',
      json: { day_index: day, category: meal.category, locked: !meal.locked },
    })
    setPayload(data)
  }

  const selected = open ? mealAt(open.day, open.slot) : null
  const selectedDayName = open ? plan.days_plan[open.day]?.day_name : ''

  return (
    <div className="space-y-6 max-w-[1120px] mx-auto">
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">Wochenplan · {plan.store} · {plan.deal_week}</p>
          <h1 className="text-3xl font-extrabold tracking-tight mt-1">Die Woche auf einen Blick</h1>
          <p className="text-sm text-ink-muted mt-1">{plan.portions} Person{plan.portions > 1 ? 'en' : ''} · {plan.diet}</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <div className="rounded-2xl border border-zinc-200 bg-surface px-4 py-3 min-w-[140px]">
            <p className="text-[10px] font-bold uppercase text-ink-muted">An der Kasse</p>
            <p className={`text-2xl font-black font-mono ${plan.over_budget ? 'text-red-700' : ''}`}>{(plan.checkout_cost ?? plan.total_cost).toFixed(2)} €</p>
            <p className="text-[11px] text-ink-muted">von {plan.budget.toFixed(0)} €</p>
          </div>
          <div className="rounded-2xl border border-brand/20 bg-brand/5 px-4 py-3 min-w-[160px]">
            <p className="text-[10px] font-bold uppercase text-brand">Zero Waste</p>
            <p className="text-2xl font-black font-mono text-brand">−{plan.pantry_savings.toFixed(2)} €</p>
            <p className="text-[11px] text-brand/80">{leftoverCount(plan)} Positionen aus dem Schrank</p>
          </div>
        </div>
      </div>

      {plan.relaxations.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {plan.relaxations.map((r) => (
            <span key={r} className="text-xs bg-amber-50 text-amber-900 border border-amber-200 px-3 py-1 rounded-full">
              {RELAX[r] || r}
            </span>
          ))}
        </div>
      )}

      <div className="lg:hidden flex gap-1 overflow-x-auto">
        {plan.days_plan.map((d, idx) => (
          <button
            key={d.day_index}
            type="button"
            onClick={() => setMobileDay(idx)}
            className={`px-3 py-1.5 rounded-full text-xs font-bold shrink-0 ${mobileDay === idx ? 'bg-zinc-900 text-white' : 'border border-zinc-200'}`}
          >
            {d.day_name.slice(0, 2)}
          </button>
        ))}
      </div>

      <div className="hidden lg:block overflow-x-auto">
        <table className="w-full border-separate border-spacing-2 min-w-[860px]">
          <thead>
            <tr>
              <th className="w-16" />
              {plan.days_plan.map((d) => (
                <th key={d.day_index} className="text-left text-[11px] font-bold uppercase tracking-wider text-ink-muted px-1">
                  {d.day_name}
                  <span className="block font-mono font-semibold normal-case text-ink">{d.calories} kcal</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {SLOTS.map((slot) => {
              const meta = SLOT_META[slot]
              const Icon = meta.Icon
              return (
                <tr key={slot}>
                  <td className="align-top pt-3 pr-1">
                    <div className="flex flex-col items-center gap-1 text-brand">
                      <Icon className="w-4 h-4" />
                      <span className="text-[10px] font-bold uppercase writing-vertical">{meta.short}</span>
                    </div>
                  </td>
                  {plan.days_plan.map((d) => {
                    const meal = mealAt(d.day_index, slot)
                    if (!meal) return <td key={d.day_index} />
                    const swapping = swapKey === `${d.day_index}-${slot}`
                    return (
                      <td key={d.day_index} className="align-top">
                        <button
                          type="button"
                          onClick={() => setOpen({ day: d.day_index, slot })}
                          className={`w-full text-left rounded-2xl border bg-surface p-3 min-h-[118px] hover:border-brand/40 transition-colors ${
                            meal.status === 'skipped' ? 'opacity-50' : 'border-zinc-200'
                          } ${meal.status === 'cooked' ? 'border-brand/40 bg-brand/5' : ''}`}
                        >
                          <div className="flex items-start justify-between gap-1">
                            <p className="text-sm font-extrabold leading-snug">{meal.name}</p>
                            {meal.has_deal && <Tag className="w-3.5 h-3.5 text-amber-700 shrink-0" />}
                          </div>
                          <p className="text-[11px] text-ink-muted mt-1">{meal.prep_time} · {meal.macros.calories} kcal</p>
                          <div className="flex gap-1 mt-2">
                            <span
                              role="button"
                              onClick={(e) => {
                                e.stopPropagation()
                                void lock(d.day_index, meal)
                              }}
                              className="p-1 rounded-md border border-zinc-200 text-ink-muted"
                            >
                              {meal.locked ? <Lock className="w-3 h-3" /> : <Unlock className="w-3 h-3" />}
                            </span>
                            <span
                              role="button"
                              onClick={(e) => {
                                e.stopPropagation()
                                if (!meal.locked) void swap(d.day_index, meal)
                              }}
                              className={`p-1 rounded-md border border-zinc-200 text-ink-muted ${swapping ? 'animate-spin' : ''}`}
                            >
                              <RefreshCw className="w-3 h-3" />
                            </span>
                          </div>
                        </button>
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="lg:hidden space-y-3">
        {SLOTS.map((slot) => {
          const meal = mealAt(mobileDay, slot)
          if (!meal) return null
          return (
            <button
              key={slot}
              type="button"
              onClick={() => setOpen({ day: mobileDay, slot })}
              className="w-full text-left rounded-2xl border border-zinc-200 bg-surface p-4"
            >
              <p className="text-[10px] font-bold uppercase text-ink-muted">{SLOT_META[slot].label}</p>
              <p className="font-extrabold">{meal.name}</p>
              <p className="text-xs text-ink-muted">{meal.prep_time} · {meal.macros.calories} kcal</p>
            </button>
          )
        })}
      </div>

      <div className="flex justify-end">
        <Link to="/einkaufszettel" className="px-5 py-3 rounded-xl bg-zinc-900 text-white text-sm font-bold inline-flex items-center gap-2">
          <ShoppingBag className="w-4 h-4" /> Einkaufszettel
        </Link>
      </div>

      {selected && open && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-zinc-900/40 p-0 sm:p-6" onClick={() => setOpen(null)}>
          <div
            className="bg-surface w-full sm:max-w-lg max-h-[90vh] overflow-y-auto rounded-t-3xl sm:rounded-3xl border border-zinc-200 p-6 space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[11px] font-bold uppercase text-ink-muted">{selectedDayName} · {selected.category}</p>
                <h2 className="text-xl font-extrabold">{selected.name}</h2>
                <p className="text-sm text-brand font-bold">{selected.cost.toFixed(2)} € · {selected.macros.calories} kcal · {selected.macros.protein}g Protein</p>
              </div>
              <button type="button" onClick={() => setOpen(null)} className="p-2 text-ink-muted"><X className="w-4 h-4" /></button>
            </div>
            <ol className="space-y-2">
              {(Array.isArray(selected.instructions) ? selected.instructions : [selected.instructions]).map((step, i) => (
                <li key={i} className="flex gap-3 text-sm">
                  <span className="w-6 h-6 rounded-full bg-zinc-900 text-white text-xs font-bold flex items-center justify-center shrink-0">{i + 1}</span>
                  <span className="pt-0.5">{step}</span>
                </li>
              ))}
            </ol>
            <div className="flex flex-wrap gap-1.5">
              {selected.ingredients.map((ing) => (
                <span key={ing.name} className={`text-[11px] px-2 py-0.5 rounded-md ${ing.in_pantry ? 'bg-brand/10 text-brand font-semibold' : ing.is_deal ? 'bg-amber-50 text-amber-800' : 'bg-zinc-100'}`}>
                  {ing.name} {formatQty(ing.quantity, ing.unit)} {ing.unit}
                </span>
              ))}
            </div>
            <div className="flex flex-wrap gap-2 pt-2">
              <button type="button" onClick={() => void logStatus(open.day, selected, selected.status === 'cooked' ? null : 'cooked')} className={`text-xs font-bold px-3 py-1.5 rounded-full border ${selected.status === 'cooked' ? 'bg-brand text-white border-brand' : 'border-zinc-200'}`}>Gekocht</button>
              <button type="button" onClick={() => void logStatus(open.day, selected, selected.status === 'skipped' ? null : 'skipped')} className={`text-xs font-bold px-3 py-1.5 rounded-full border ${selected.status === 'skipped' ? 'bg-zinc-800 text-white border-zinc-800' : 'border-zinc-200'}`}>Übersprungen</button>
              <button type="button" onClick={() => void neverAgain(selected)} className="text-xs font-bold px-3 py-1.5 rounded-full border border-red-200 text-red-800">Nie wieder</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
