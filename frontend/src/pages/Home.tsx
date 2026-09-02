import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Moon, ShoppingBag, SlidersHorizontal, Sun, Tag, Utensils } from 'lucide-react'
import { api, ApiError } from '../api'
import { useAuth } from '../auth'
import type { Meal, Plan, PlanPayload } from '../types'

const SLOTS = ['Frühstück', 'Mittagessen', 'Abendessen'] as const

const SLOT_META: Record<string, { label: string; Icon: typeof Sun; hint: string }> = {
  Frühstück: { label: 'Frühstück', Icon: Sun, hint: 'Morgen' },
  Mittagessen: { label: 'Mittagessen', Icon: Utensils, hint: 'Mittag' },
  Abendessen: { label: 'Abendessen', Icon: Moon, hint: 'Abend' },
}

type CupboardItem = { id: number; name: string; quantity: number; unit: string }

function greeting(hour: number) {
  if (hour < 11) return 'Guten Morgen'
  if (hour < 17) return 'Guten Tag'
  return 'Guten Abend'
}

function currentSlot(hour: number) {
  if (hour < 11) return 'Frühstück'
  if (hour < 16) return 'Mittagessen'
  return 'Abendessen'
}

function leftoverCount(plan: Plan) {
  return plan.shopping_list.already_at_home?.length || 0
}

export default function Home() {
  const { user } = useAuth()
  const [payload, setPayload] = useState<PlanPayload | null>(null)
  const [missing, setMissing] = useState(false)
  const [cupboard, setCupboard] = useState<CupboardItem[] | null>(null)
  const [loading, setLoading] = useState(true)
  const hour = new Date().getHours()
  const slotNow = currentSlot(hour)
  const plus = user?.is_pro || user?.plan_tier === 'plus' || user?.plan_tier === 'premium'

  useEffect(() => {
    void (async () => {
      try {
        const data = await api<PlanPayload>('/api/plan')
        setPayload(data)
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) setMissing(true)
        else setMissing(true)
      }
      if (plus) {
        try {
          const data = await api<{ items: CupboardItem[] }>('/api/cupboard/')
          setCupboard(data.items)
        } catch {
          setCupboard([])
        }
      }
      setLoading(false)
    })()
  }, [plus])

  if (loading) return <p className="text-sm text-ink-muted">Lade Küche…</p>

  const plan = payload?.plan
  const today = plan?.days_plan[0]
  const cookedToday = today?.meals.filter((m) => m.status === 'cooked').length || 0

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">
            {greeting(hour)}
            {today ? ` · ${today.day_name}` : ''}
            {plan ? ` · ${plan.store}` : ''}
          </p>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight mt-1">Deine Küche heute</h1>
          <p className="text-sm text-ink-muted mt-1">
            {missing
              ? 'Noch kein Wochenplan. Markt, Haushalt, Küche — dann kochen.'
              : `${plan?.portions} Person${(plan?.portions || 1) > 1 ? 'en' : ''} · ${plan?.diet} · KW ${plan?.deal_week}`}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            to="/setup"
            className="px-4 py-2.5 rounded-full border border-zinc-300 text-sm font-semibold inline-flex items-center gap-1.5 hover:border-brand hover:text-brand"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            {missing ? 'Plan anlegen' : 'Neuer Plan'}
          </Link>
          {!missing && (
            <Link
              to="/einkaufszettel"
              className="px-4 py-2.5 rounded-full bg-zinc-900 text-white text-sm font-bold inline-flex items-center gap-1.5"
            >
              <ShoppingBag className="w-3.5 h-3.5" />
              Einkaufszettel
            </Link>
          )}
        </div>
      </div>

      {missing ? (
        <EmptyKitchen plus={plus} />
      ) : (
        plan && today && (
          <>
            <section className="grid lg:grid-cols-3 gap-3">
              {SLOTS.map((slot) => {
                const meal = today.meals.find((m) => m.category === slot)
                return (
                  <TodayMealCard key={slot} slot={slot} meal={meal} active={slot === slotNow} />
                )
              })}
            </section>

            <section className="grid sm:grid-cols-3 gap-3">
              <StatCard
                label="An der Kasse"
                value={`${(plan.checkout_cost ?? plan.total_cost).toFixed(2)} €`}
                hint={`von ${plan.budget.toFixed(0)} €`}
                alert={plan.over_budget}
              />
              <StatCard
                label="Zero Waste"
                value={`−${plan.pantry_savings.toFixed(2)} €`}
                hint={`${leftoverCount(plan)} Positionen bleiben im Schrank`}
                brand
              />
              <StatCard
                label="Heute gekocht"
                value={`${cookedToday} / 3`}
                hint={today.calories ? `${today.calories} kcal heute` : 'Noch nichts abgehakt'}
              />
            </section>

            <section className="rounded-3xl border border-zinc-200 bg-surface p-5 sm:p-6 space-y-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">Die Woche</p>
                  <h2 className="text-lg font-extrabold">Sieben Tage, ohne hin und her</h2>
                </div>
                <Link to="/plan" className="text-sm font-bold text-brand inline-flex items-center gap-1">
                  Wochenplan <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
                {plan.days_plan.map((day, idx) => (
                  <Link
                    key={day.day_index}
                    to="/plan"
                    className={`rounded-2xl border p-3 min-h-[112px] ${
                      idx === 0 ? 'border-brand/40 bg-brand/5' : 'border-zinc-200 bg-canvas'
                    }`}
                  >
                    <p className="text-[10px] font-bold uppercase tracking-wider text-ink-muted">
                      {day.day_name.slice(0, 2)}
                      {idx === 0 ? ' · heute' : ''}
                    </p>
                    <ul className="mt-2 space-y-1">
                      {day.meals.slice(0, 3).map((m) => (
                        <li key={m.id + m.category} className="text-[11px] font-semibold leading-snug truncate">
                          {m.name}
                        </li>
                      ))}
                    </ul>
                  </Link>
                ))}
              </div>
            </section>
          </>
        )
      )}

      <section className="grid md:grid-cols-2 gap-3">
        <Link
          to={plus ? '/vorrat' : '/pro'}
          className="rounded-3xl border border-zinc-200 bg-surface p-6 hover:border-brand/40 transition-colors"
        >
          <p className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">Vorratsschrank</p>
          <h2 className="text-lg font-extrabold mt-1">Was schon da ist, wird nicht gekauft</h2>
          {plus && cupboard ? (
            cupboard.length === 0 ? (
              <p className="text-sm text-ink-muted mt-2">Schrank ist leer. Reste und Packungen eintragen.</p>
            ) : (
              <ul className="mt-3 space-y-1 text-sm">
                {cupboard.slice(0, 5).map((item) => (
                  <li key={item.id} className="flex justify-between gap-3">
                    <span className="truncate">{item.name}</span>
                    <span className="font-mono text-ink-muted shrink-0">
                      {item.quantity} {item.unit}
                    </span>
                  </li>
                ))}
                {cupboard.length > 5 && (
                  <li className="text-xs text-ink-muted">+{cupboard.length - 5} weitere</li>
                )}
              </ul>
            )
          ) : (
            <p className="text-sm text-ink-muted mt-2">Plus merkt sich den Schrank. 4,99 €.</p>
          )}
        </Link>
        <div className="rounded-3xl border border-zinc-200 bg-surface p-6 space-y-3">
          <p className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">Schnell</p>
          <div className="grid grid-cols-2 gap-2">
            <QuickLink to="/plan" label="Wochenplan" />
            <QuickLink to="/einkaufszettel" label="Einkauf" />
            <QuickLink to="/setup" label="Neuer Plan" />
            <QuickLink to={plus ? '/vorrat' : '/pro'} label={plus ? 'Vorrat' : 'Plus'} />
          </div>
        </div>
      </section>
    </div>
  )
}

function EmptyKitchen({ plus }: { plus: boolean }) {
  return (
    <section className="rounded-3xl border border-zinc-200 bg-surface p-8 sm:p-10 space-y-6">
      <div className="max-w-lg">
        <h2 className="text-2xl font-extrabold">Drei Schritte, dann steht die Woche.</h2>
        <p className="text-sm text-ink-muted mt-2">
          Markt mit aktuellen Preisen, Personen und Küche. Der Plan kommt aus dem eigenen Rezeptkatalog — nicht aus einer leeren Liste.
        </p>
      </div>
      <ol className="grid sm:grid-cols-3 gap-3 text-sm">
        <li className="rounded-2xl border border-zinc-200 bg-canvas p-4">
          <p className="text-[10px] font-bold uppercase text-ink-muted">1</p>
          <p className="font-extrabold mt-1">Markt</p>
          <p className="text-ink-muted mt-1">Nur Lidl und Marktkauf, solange Preise da sind.</p>
        </li>
        <li className="rounded-2xl border border-zinc-200 bg-canvas p-4">
          <p className="text-[10px] font-bold uppercase text-ink-muted">2</p>
          <p className="font-extrabold mt-1">Haushalt</p>
          <p className="text-ink-muted mt-1">Personen, Makros, was in der Küche steht.</p>
        </li>
        <li className="rounded-2xl border border-zinc-200 bg-canvas p-4">
          <p className="text-[10px] font-bold uppercase text-ink-muted">3</p>
          <p className="font-extrabold mt-1">Reste</p>
          <p className="text-ink-muted mt-1">{plus ? 'Schrank abziehen, weniger kaufen.' : 'Plus merkt sich den Schrank.'}</p>
        </li>
      </ol>
      <Link to="/setup" className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-brand text-white text-sm font-bold">
        Zum Konfigurator <ArrowRight className="w-4 h-4" />
      </Link>
    </section>
  )
}

function TodayMealCard({ slot, meal, active }: { slot: string; meal?: Meal; active: boolean }) {
  const meta = SLOT_META[slot]
  const Icon = meta.Icon
  return (
    <Link
      to="/plan"
      className={`rounded-3xl border bg-surface p-5 min-h-[160px] flex flex-col ${
        active ? 'border-brand/50 shadow-sm' : 'border-zinc-200'
      } ${meal?.status === 'skipped' ? 'opacity-50' : ''} ${meal?.status === 'cooked' ? 'bg-brand/5' : ''}`}
    >
      <div className="flex items-center justify-between gap-2">
        <p className="text-[10px] font-bold uppercase tracking-wider text-ink-muted inline-flex items-center gap-1.5">
          <Icon className="w-3.5 h-3.5 text-brand" />
          {meta.label}
          {active && <span className="text-brand">jetzt</span>}
        </p>
        {meal?.has_deal && <Tag className="w-3.5 h-3.5 text-amber-700" />}
      </div>
      {meal ? (
        <>
          <p className="text-lg font-extrabold leading-snug mt-3">{meal.name}</p>
          <p className="text-xs text-ink-muted mt-auto pt-3">
            {meal.prep_time} · {meal.macros.calories} kcal
            {meal.status === 'cooked' ? ' · gekocht' : ''}
          </p>
        </>
      ) : (
        <p className="text-sm text-ink-muted mt-3">Kein Gericht in diesem Slot.</p>
      )}
    </Link>
  )
}

function StatCard({
  label,
  value,
  hint,
  brand,
  alert,
}: {
  label: string
  value: string
  hint: string
  brand?: boolean
  alert?: boolean
}) {
  return (
    <div className={`rounded-2xl border px-4 py-3 ${brand ? 'border-brand/20 bg-brand/5' : 'border-zinc-200 bg-surface'}`}>
      <p className={`text-[10px] font-bold uppercase ${brand ? 'text-brand' : 'text-ink-muted'}`}>{label}</p>
      <p className={`text-2xl font-black font-mono mt-1 ${alert ? 'text-red-700' : brand ? 'text-brand' : ''}`}>{value}</p>
      <p className={`text-[11px] ${brand ? 'text-brand/80' : 'text-ink-muted'}`}>{hint}</p>
    </div>
  )
}

function QuickLink({ to, label }: { to: string; label: string }) {
  return (
    <Link to={to} className="rounded-2xl border border-zinc-200 px-3 py-3 text-sm font-bold hover:border-brand/40">
      {label}
    </Link>
  )
}
