import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Lock, Moon, RefreshCw, ShoppingBag, Sun, Tag, Unlock, Utensils } from 'lucide-react'
import { api, ApiError } from '../api'
import type { Meal, Plan, PlanPayload } from '../types'

const RELAX: Record<string, string> = {
  variety: 'Mehr Abwechslung war mit diesem Rezeptbestand nicht möglich',
  budget: 'Budget konnte nicht eingehalten werden',
  macros: 'Kalorien/Protein-Ziel nur näherungsweise',
}

const SLOT_META: Record<string, { label: string; Icon: typeof Sun; when: string }> = {
  Frühstück: { label: 'Frühstück', Icon: Sun, when: 'Morgen' },
  Mittagessen: { label: 'Mittagessen', Icon: Utensils, when: 'Mittag' },
  Abendessen: { label: 'Abendessen', Icon: Moon, when: 'Abend' },
}

function formatQty(qty: number, unit: string) {
  if (unit === 'Stück') {
    const rounded = Math.round(qty * 10) / 10
    return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1)
  }
  return String(Math.max(1, Math.round(qty)))
}

function MealRow({
  meal,
  onSwap,
  onLock,
  onLog,
  onNever,
  swapping,
}: {
  meal: Meal
  onSwap: () => void
  onLock: () => void
  onLog: (status: 'cooked' | 'skipped' | null) => void
  onNever: () => void
  swapping: boolean
}) {
  const meta = SLOT_META[meal.category] || SLOT_META.Mittagessen
  const Icon = meta.Icon
  const steps = Array.isArray(meal.instructions) ? meal.instructions : meal.instructions ? [meal.instructions] : []
  const cooked = meal.status === 'cooked'
  const skipped = meal.status === 'skipped'

  return (
    <article className={`relative pl-12 ${cooked ? 'opacity-80' : ''} ${skipped ? 'opacity-60' : ''}`}>
      <div className="absolute left-0 top-1 w-9 h-9 rounded-full bg-brand text-white flex items-center justify-center">
        <Icon className="w-4 h-4" />
      </div>
      <div className="absolute left-[17px] top-11 bottom-[-28px] w-px bg-stone-200 last:hidden" />
      <div className="bg-surface rounded-3xl border border-stone-200/80 p-5 sm:p-6 space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-ink-muted">
              <span>{meta.when}</span>
              <span>·</span>
              <span>{meal.prep_time}</span>
              {meal.has_deal && (
                <span className="inline-flex items-center gap-1 bg-amber-50 text-amber-800 border border-amber-200 px-2 py-0.5 rounded-full normal-case">
                  <Tag className="w-3 h-3" /> Angebot
                </span>
              )}
              {cooked && <span className="text-brand normal-case">Gekocht</span>}
              {skipped && <span className="normal-case">Übersprungen</span>}
            </div>
            <h3 className="text-xl font-extrabold tracking-tight mt-1">{meal.name}</h3>
            <p className="text-sm text-brand font-bold mt-0.5">{meal.cost.toFixed(2)} € · {meal.macros.calories} kcal · {meal.macros.protein}g Protein · {meal.macros.carbs}g KH · {meal.macros.fat}g Fett</p>
          </div>
          <div className="flex flex-wrap gap-1.5">
            <button type="button" onClick={onLock} className={`px-3 py-1.5 rounded-full border text-xs font-semibold flex items-center gap-1 ${meal.locked ? 'border-brand text-brand' : 'border-stone-200'}`}>
              {meal.locked ? <Lock className="w-3.5 h-3.5" /> : <Unlock className="w-3.5 h-3.5" />}
              {meal.locked ? 'Fixiert' : 'Fixieren'}
            </button>
            <button type="button" disabled={swapping || !!meal.locked} onClick={onSwap} className="px-3 py-1.5 rounded-full border border-stone-200 text-xs font-semibold flex items-center gap-1 disabled:opacity-50">
              <RefreshCw className={`w-3.5 h-3.5 ${swapping ? 'animate-spin' : ''}`} /> Tauschen
            </button>
          </div>
        </div>

        {steps.length > 0 && (
          <ol className="space-y-2">
            {steps.map((step, i) => (
              <li key={i} className="flex gap-3 text-sm leading-relaxed">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-stone-900 text-white text-xs font-bold flex items-center justify-center">{i + 1}</span>
                <span className="pt-0.5">{step}</span>
              </li>
            ))}
          </ol>
        )}

        <div className="flex flex-wrap gap-1.5">
          {meal.ingredients.map((ing) => (
            <span
              key={ing.name}
              className={`text-[11px] px-2 py-0.5 rounded-md ${
                ing.in_pantry
                  ? 'bg-brand/10 text-brand font-semibold'
                  : ing.is_deal
                    ? 'bg-amber-50 text-amber-800 font-semibold border border-amber-200/60'
                    : 'bg-stone-100 text-ink-muted'
              }`}
            >
              {ing.name} {formatQty(ing.quantity, ing.unit)} {ing.unit}
              {ing.in_pantry ? ' · Vorrat' : ''}
            </span>
          ))}
        </div>

        <div className="flex flex-wrap gap-1.5 pt-1">
          <button type="button" onClick={() => onLog(cooked ? null : 'cooked')} className={`text-[11px] font-bold px-3 py-1.5 rounded-full border ${cooked ? 'bg-brand text-white border-brand' : 'border-stone-200'}`}>Gekocht</button>
          <button type="button" onClick={() => onLog(skipped ? null : 'skipped')} className={`text-[11px] font-bold px-3 py-1.5 rounded-full border ${skipped ? 'bg-stone-800 text-white border-stone-800' : 'border-stone-200'}`}>Übersprungen</button>
          <button type="button" onClick={onNever} className="text-[11px] font-bold px-3 py-1.5 rounded-full border border-red-200 text-red-800">Nie wieder</button>
        </div>
      </div>
    </article>
  )
}

export default function PlanPage() {
  const [payload, setPayload] = useState<PlanPayload | null>(null)
  const [day, setDay] = useState(0)
  const [swapKey, setSwapKey] = useState<string | null>(null)
  const [missing, setMissing] = useState(false)
  const [swapped, setSwapped] = useState(false)

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
  const active = plan.days_plan[day]

  async function swap(meal: Meal) {
    setSwapKey(`${day}-${meal.category}`)
    try {
      const data = await api<PlanPayload>('/api/plan/swap', {
        method: 'POST',
        json: { day_index: day, category: meal.category, current_id: meal.id },
      })
      setPayload(data)
      setSwapped(true)
    } finally {
      setSwapKey(null)
    }
  }

  async function logStatus(meal: Meal, status: 'cooked' | 'skipped' | null) {
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
    setSwapped(true)
  }

  async function lock(meal: Meal) {
    const data = await api<PlanPayload>('/api/plan/lock', {
      method: 'POST',
      json: { day_index: day, category: meal.category, locked: !meal.locked },
    })
    setPayload(data)
  }

  return (
    <div className="space-y-8 max-w-3xl mx-auto">
      <div className="bg-surface rounded-2xl p-6 border border-stone-200/80 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-muted">Dein Wochenplan</span>
            <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-stone-100">{plan.store}</span>
            <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-stone-100">{plan.diet}</span>
            <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-stone-100">{plan.portions} Port.</span>
            {plan.deal_week && <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-brand/10 text-brand">{plan.deal_week}</span>}
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Kochen diese Woche</h1>
          {!!plan.members?.length && (
            <div className="flex flex-wrap gap-2 pt-1">
              {plan.members.map((m) => (
                <span key={m.id} className="text-[11px] bg-stone-50 border border-stone-200 rounded-full px-2 py-0.5">
                  {m.name}: {m.calories} kcal / {m.protein}g
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center gap-4 sm:gap-6 divide-x divide-stone-200">
          <div>
            <span className="text-xs text-ink-muted block">An der Kasse</span>
            <span className={`text-2xl font-black font-mono ${plan.over_budget ? 'text-red-700' : 'text-ink'}`}>
              {(plan.checkout_cost ?? plan.total_cost).toFixed(2)} €
            </span>
            <span className="text-[10px] text-ink-muted">von {plan.budget.toFixed(0)} € Budget</span>
          </div>
          <div className="pl-4 sm:pl-6 hidden sm:block">
            <span className="text-xs text-ink-muted block">Ø Tag</span>
            <span className="text-lg font-black font-mono">{plan.daily_avg.calories} kcal</span>
            <span className="text-xs text-brand font-bold block">{plan.daily_avg.protein}g Protein</span>
          </div>
        </div>
      </div>

      {swapped && (
        <div className="bg-brand/10 border border-brand/20 rounded-2xl px-4 py-3 text-sm flex items-center justify-between gap-3">
          <span>Einkaufszettel wurde neu berechnet.</span>
          <Link to="/einkaufszettel" className="font-bold text-brand text-xs flex items-center gap-1">
            Zum Einkaufszettel <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {plan.relaxations.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {plan.relaxations.map((r) => (
            <span key={r} className="text-xs bg-amber-50 text-amber-900 border border-amber-200 px-3 py-1 rounded-full">
              {RELAX[r] || r}
            </span>
          ))}
        </div>
      )}

      <div className="flex gap-2 overflow-x-auto pb-1">
        {plan.days_plan.map((d, idx) => (
          <button
            key={d.day_index}
            type="button"
            onClick={() => setDay(idx)}
            className={`min-w-[148px] flex-1 text-left rounded-2xl border px-3 py-3 transition-all ${
              idx === day ? 'bg-stone-900 text-white border-stone-900' : 'bg-surface text-ink border-stone-200 hover:border-stone-400'
            }`}
          >
            <div className="text-xs font-extrabold">{d.day_name}</div>
            <div className={`mt-1 space-y-0.5 text-[11px] leading-snug ${idx === day ? 'text-stone-300' : 'text-ink-muted'}`}>
              {d.meals.map((m) => (
                <div key={m.category} className="truncate">{m.name}</div>
              ))}
            </div>
          </button>
        ))}
      </div>

      <div className="flex items-end justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-ink-muted">Heute kochen</p>
          <h2 className="text-2xl font-extrabold">{active.day_name}</h2>
          <p className="text-sm text-ink-muted">{active.calories} kcal · {active.protein}g Protein · {active.cost.toFixed(2)} €</p>
        </div>
        <Link to="/einkaufszettel" className="text-xs font-bold text-brand hover:underline flex items-center gap-1">
          Einkaufszettel <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      <div className="space-y-6">
        {active.meals.map((meal, idx) => (
          <div key={`${day}-${meal.category}-${meal.id}`} className={idx === active.meals.length - 1 ? '[&>article>div:nth-child(2)]:hidden' : ''}>
            <MealRow
              meal={meal}
              swapping={swapKey === `${day}-${meal.category}`}
              onSwap={() => void swap(meal)}
              onLock={() => void lock(meal)}
              onLog={(s) => void logStatus(meal, s)}
              onNever={() => void neverAgain(meal)}
            />
          </div>
        ))}
      </div>

      <div className="bg-stone-900 text-white rounded-2xl p-6 sm:p-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold">Einkaufen für {plan.days} verschiedene Tage</h3>
          <p className="text-xs text-stone-300 mt-1">Jedes Rezept höchstens einmal in der Woche — sortiert nach Gängen bei {plan.store}.</p>
        </div>
        <Link to="/einkaufszettel" className="px-6 py-3 rounded-xl bg-white text-stone-900 font-bold text-sm flex items-center justify-center gap-2">
          <ShoppingBag className="w-4 h-4" />
          Zum Einkaufszettel
        </Link>
      </div>
    </div>
  )
}
