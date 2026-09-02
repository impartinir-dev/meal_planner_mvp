import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, BookOpen, Lock, RefreshCw, ShoppingBag, Tag, Unlock } from 'lucide-react'
import { api, ApiError } from '../api'
import type { Meal, Plan, PlanPayload } from '../types'

const RELAX: Record<string, string> = {
  variety: 'Mehr Abwechslung war mit diesem Rezeptbestand nicht möglich',
  budget: 'Budget konnte nicht eingehalten werden',
  macros: 'Kalorien/Protein-Ziel nur näherungsweise',
}

function formatQty(qty: number, unit: string) {
  if (unit === 'Stück') {
    const rounded = Math.round(qty * 10) / 10
    return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1)
  }
  return String(Math.max(1, Math.round(qty)))
}

function MealCard({
  meal,
  onSwap,
  onLock,
  swapping,
}: {
  meal: Meal
  onSwap: () => void
  onLock: () => void
  swapping: boolean
}) {
  const [open, setOpen] = useState(false)
  return (
    <div className="bg-surface rounded-2xl p-6 border border-stone-200/80 flex flex-col justify-between space-y-4">
      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs">
          <span className="font-bold uppercase tracking-wider text-ink-muted">{meal.category}</span>
          {meal.has_deal ? (
            <span className="inline-flex items-center gap-1 bg-amber-50 text-amber-800 border border-amber-200/80 text-[10px] font-bold px-2 py-0.5 rounded-full">
              <Tag className="w-3 h-3" /> Angebot
            </span>
          ) : (
            <span className="text-ink-muted text-[11px]">{meal.prep_time}</span>
          )}
        </div>
        <div>
          <h3 className="font-bold text-base leading-snug">{meal.name}</h3>
          <div className="text-xs font-extrabold text-brand mt-0.5">{meal.cost.toFixed(2)} € pro Portion</div>
        </div>
        <div className="grid grid-cols-4 gap-1 p-2 bg-stone-50 rounded-xl text-center text-xs">
          <div><div className="text-[10px] text-ink-muted">Kcal</div><div className="font-bold">{meal.macros.calories}</div></div>
          <div><div className="text-[10px] text-brand font-semibold">Protein</div><div className="font-bold text-brand">{meal.macros.protein}g</div></div>
          <div><div className="text-[10px] text-ink-muted">Carbs</div><div className="font-bold">{meal.macros.carbs}g</div></div>
          <div><div className="text-[10px] text-ink-muted">Fett</div><div className="font-bold">{meal.macros.fat}g</div></div>
        </div>
        <div className="flex flex-wrap gap-1">
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
              {ing.name} ({formatQty(ing.quantity, ing.unit)}){ing.in_pantry ? ' • Vorrat' : ''}{ing.is_deal ? ' • Deal' : ''}
            </span>
          ))}
        </div>
      </div>
      <div className="pt-3 border-t border-stone-100 flex items-center justify-between">
        <button type="button" onClick={() => setOpen(!open)} className="text-xs text-ink-muted hover:text-ink font-medium flex items-center gap-1">
          <BookOpen className="w-3.5 h-3.5" /> Zubereitung
        </button>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onLock}
            className={`px-3 py-1.5 rounded-full border text-xs font-semibold flex items-center gap-1 ${meal.locked ? 'border-brand text-brand' : 'border-stone-200'}`}
          >
            {meal.locked ? <Lock className="w-3.5 h-3.5" /> : <Unlock className="w-3.5 h-3.5" />}
            {meal.locked ? 'Fixiert' : 'Fixieren'}
          </button>
          <button
            type="button"
            disabled={swapping || !!meal.locked}
            onClick={onSwap}
            className="px-3 py-1.5 rounded-full border border-stone-200 hover:border-brand text-xs font-semibold flex items-center gap-1 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${swapping ? 'animate-spin' : ''}`} /> Tauschen
          </button>
        </div>
      </div>
      {open && (
        <p className="text-xs text-ink-muted italic bg-stone-50 p-3 rounded-xl border border-stone-200/60">{meal.instructions}</p>
      )}
    </div>
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

  async function lock(meal: Meal) {
    const data = await api<PlanPayload>('/api/plan/lock', {
      method: 'POST',
      json: { day_index: day, category: meal.category, locked: !meal.locked },
    })
    setPayload(data)
  }

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div className="bg-surface rounded-2xl p-6 border border-stone-200/80 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-muted">Dein Wochenplan</span>
            <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-stone-100">{plan.store}</span>
            <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-stone-100">{plan.diet}</span>
            <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-stone-100">{plan.portions} Port.</span>
            {plan.deal_week && <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-brand/10 text-brand">{plan.deal_week}</span>}
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Ernährungsplan &amp; Ersparnis</h1>
        </div>
        <div className="flex items-center gap-4 sm:gap-6 divide-x divide-stone-200">
          <div>
            <span className="text-xs text-ink-muted block">An der Kasse</span>
            <span className={`text-2xl font-black font-mono ${plan.over_budget ? 'text-red-700' : 'text-ink'}`}>
              {(plan.checkout_cost ?? plan.total_cost).toFixed(2)} €
            </span>
            <span className="text-[10px] text-ink-muted">von {plan.budget.toFixed(0)} € Budget</span>
          </div>
          <div className="pl-4 sm:pl-6">
            <span className="text-xs text-brand font-medium block">Du sparst</span>
            <span className="text-2xl font-black text-brand font-mono">{plan.combined_savings.toFixed(2)} €</span>
          </div>
          <div className="pl-4 sm:pl-6 hidden sm:block">
            <span className="text-xs text-ink-muted block">Ø Kalorien</span>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-black font-mono">{plan.daily_avg.calories}</span>
              <span className="text-xs text-ink-muted">/ {plan.target_calories} kcal</span>
            </div>
          </div>
          <div className="pl-4 sm:pl-6 hidden sm:block">
            <span className="text-xs text-brand font-medium block">Ø Protein</span>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-black text-brand font-mono">{plan.daily_avg.protein} g</span>
              <span className="text-xs text-ink-muted">/ {plan.target_protein}g</span>
            </div>
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

      <div className="flex gap-2 overflow-x-auto pb-2 border-b border-stone-200/80">
        {plan.days_plan.map((d, idx) => (
          <button
            key={d.day_index}
            type="button"
            onClick={() => setDay(idx)}
            className={`flex-1 min-w-[110px] py-3 px-4 rounded-xl text-xs font-bold text-center border ${
              idx === day ? 'bg-stone-900 text-white border-stone-900' : 'bg-surface text-ink-muted border-stone-200'
            }`}
          >
            <div className="font-extrabold text-sm">{d.day_name}</div>
            <div className="text-[11px] font-medium opacity-80 mt-0.5">{d.cost.toFixed(2)} € • {d.protein}g Prot</div>
          </button>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <h2 className="text-xl font-extrabold">Mahlzeiten für {active.day_name}</h2>
        <Link to="/einkaufszettel" className="text-xs font-bold text-brand hover:underline flex items-center gap-1">
          Zum Einkaufszettel <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {active.meals.map((meal) => (
          <MealCard
            key={`${day}-${meal.category}-${meal.id}`}
            meal={meal}
            swapping={swapKey === `${day}-${meal.category}`}
            onSwap={() => void swap(meal)}
            onLock={() => void lock(meal)}
          />
        ))}
      </div>

      <div className="bg-stone-900 text-white rounded-2xl p-6 sm:p-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold">Bereit für den Wocheneinkauf?</h3>
          <p className="text-xs text-stone-300 mt-1">Zutaten nach Regalgängen bei {plan.store}, in kaufbaren Packungen.</p>
        </div>
        <Link to="/einkaufszettel" className="px-6 py-3 rounded-xl bg-white text-stone-900 font-bold text-sm flex items-center justify-center gap-2">
          <ShoppingBag className="w-4 h-4" />
          Zum Einkaufszettel ({plan.shopping_list.to_buy.length} Gänge)
        </Link>
      </div>
    </div>
  )
}
