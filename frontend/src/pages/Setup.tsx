import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Sparkles, Tag } from 'lucide-react'
import { api } from '../api'
import type { HouseholdMember, Meta, PlanPayload, Prefs } from '../types'

const DEFAULT_MEMBER: HouseholdMember = { id: 'self', name: 'Ich', calories: 2200, protein: 140 }

const DEFAULT: Prefs = {
  store: 'Lidl',
  diet: 'High-Protein',
  budget: 50,
  days: 7,
  calories: 2200,
  protein: 140,
  pantry: ['Olivenöl', 'Reis', 'Haferflocken'],
  portions: 1,
  exclude: [],
  members: [DEFAULT_MEMBER],
}

function withMembers(members: HouseholdMember[]): Pick<Prefs, 'members' | 'portions' | 'calories' | 'protein'> {
  const list = members.length ? members : [DEFAULT_MEMBER]
  const n = list.length
  return {
    members: list,
    portions: n,
    calories: Math.round(list.reduce((s, m) => s + m.calories, 0) / n),
    protein: Math.round(list.reduce((s, m) => s + m.protein, 0) / n),
  }
}

export default function Setup() {
  const nav = useNavigate()
  const [meta, setMeta] = useState<Meta | null>(null)
  const [prefs, setPrefs] = useState<Prefs>(DEFAULT)
  const [step, setStep] = useState(1)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    void (async () => {
      const m = await api<Meta>('/api/meta')
      setMeta(m)
      try {
        const existing = await api<PlanPayload>('/api/plan')
        const members = existing.prefs.members?.length
          ? existing.prefs.members
          : [{ id: 'self', name: 'Ich', calories: existing.prefs.calories, protein: existing.prefs.protein }]
        setPrefs({ ...DEFAULT, ...existing.prefs, exclude: existing.prefs.exclude || [], ...withMembers(members) })
      } catch {
        /* no plan yet */
      }
    })()
  }, [])

  if (!meta) return <p className="text-sm text-ink-muted">Lade Konfigurator…</p>

  const dietName = meta.diets.find((d) => d.id === prefs.diet)?.name || prefs.diet

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api<PlanPayload>('/api/plan', { method: 'POST', json: prefs })
      nav('/plan')
    } catch {
      setError('Plan konnte nicht berechnet werden. Bitte erneut versuchen.')
    } finally {
      setBusy(false)
    }
  }

  function stepNavClass(n: number) {
    const active = n === step
    const done = n < step
    return `step-nav-btn text-left py-2 border-b-2 transition-all ${
      active ? 'border-brand' : done ? 'border-stone-800' : 'border-stone-200'
    }`
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div className="space-y-4">
        <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-ink-muted">
          <span>Konfigurator</span>
          <span>Schritt {step} von 3</span>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {[1, 2, 3].map((n) => (
            <button key={n} type="button" onClick={() => setStep(n)} className={stepNavClass(n)}>
              <span className={`block text-[11px] font-bold ${n === step ? 'text-brand' : n < step ? 'text-stone-800' : 'text-ink-muted'}`}>
                {n === 1 ? '1. Supermarkt' : n === 2 ? '2. Ziel & Budget' : '3. Vorrat'}
              </span>
              <span className="text-xs font-semibold text-ink truncate block">
                {n === 1 ? prefs.store : n === 2 ? `${dietName} • ${prefs.calories} kcal` : 'Zero Waste'}
              </span>
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={onSubmit}>
        {step === 1 && (
          <div className="bg-surface rounded-3xl p-6 sm:p-10 border border-stone-200/80 space-y-6">
            <div className="space-y-1.5">
              <span className="text-xs font-bold text-brand uppercase tracking-wider">Schritt 1</span>
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Wo kaufst du am liebsten ein?</h1>
              <p className="text-sm text-ink-muted">
                Angebote der Woche: {meta.deal_week ? `KW ${meta.deal_week.replace('2026-W', '').replace(/^\d{4}-W/, '')}` : 'kuratiert'}.
                {meta.deal_week && ` (${meta.deal_week})`}
              </p>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2">
              {meta.stores.map((store) => (
                <label key={store.id} className="cursor-pointer">
                  <input
                    type="radio"
                    name="store"
                    className="peer sr-only"
                    checked={prefs.store === store.id}
                    onChange={() => setPrefs({ ...prefs, store: store.id })}
                  />
                  <div className="p-5 rounded-2xl border border-stone-200 peer-checked:border-brand peer-checked:bg-stone-50/80 hover:bg-stone-50 transition-all flex flex-col justify-between h-32 text-left">
                    <span className="text-[11px] font-semibold text-ink-muted uppercase tracking-wider">{store.badge}</span>
                    <div>
                      <div className="font-extrabold text-lg">{store.name}</div>
                      <div className="text-[11px] text-brand font-semibold flex items-center gap-1 mt-0.5">
                        <Tag className="w-3.5 h-3.5" />
                        <span>Angebote {meta.deal_week || 'KW'}</span>
                      </div>
                    </div>
                  </div>
                </label>
              ))}
            </div>
            <div className="pt-4 flex justify-end">
              <button type="button" onClick={() => setStep(2)} className="px-6 py-3.5 rounded-xl bg-brand hover:bg-brand-light text-white font-bold text-sm flex items-center gap-2">
                Weiter zu Ziel &amp; Budget <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="bg-surface rounded-3xl p-6 sm:p-10 border border-stone-200/80 space-y-8">
            <div>
              <span className="text-xs font-bold text-brand uppercase tracking-wider">Schritt 2</span>
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight mt-1">Dein Ernährungsziel &amp; Budget</h1>
            </div>
            <div className="flex flex-wrap gap-2.5">
              {meta.diets.map((diet) => (
                <label key={diet.id} className="cursor-pointer">
                  <input type="radio" className="peer sr-only" checked={prefs.diet === diet.id} onChange={() => setPrefs({ ...prefs, diet: diet.id })} />
                  <div className="px-4 py-2.5 rounded-full border border-stone-200 text-sm font-semibold peer-checked:bg-brand peer-checked:text-white peer-checked:border-brand">
                    {diet.name}
                  </div>
                </label>
              ))}
            </div>
            <div className="space-y-2">
              <span className="text-xs font-bold uppercase tracking-wider text-ink-muted">Ohne (Allergien &amp; Unverträglichkeiten)</span>
              <div className="flex flex-wrap gap-2">
                {(meta.allergens || []).map((a) => {
                  const on = (prefs.exclude || []).includes(a.id)
                  return (
                    <button
                      key={a.id}
                      type="button"
                      onClick={() =>
                        setPrefs({
                          ...prefs,
                          exclude: on ? prefs.exclude.filter((x) => x !== a.id) : [...(prefs.exclude || []), a.id],
                        })
                      }
                      className={`px-3 py-1.5 rounded-full border text-xs font-semibold ${on ? 'bg-red-50 text-red-800 border-red-200' : 'border-stone-200'}`}
                    >
                      Ohne {a.name}
                    </button>
                  )
                })}
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-4 border-t border-stone-100">
              <div className="space-y-3">
                <span className="text-xs font-bold uppercase tracking-wider text-ink-muted">Zeitraum</span>
                <div className="grid grid-cols-2 gap-2">
                  {[5, 7].map((d) => (
                    <button
                      key={d}
                      type="button"
                      onClick={() => setPrefs({ ...prefs, days: d })}
                      className={`py-2.5 px-3 rounded-xl border text-xs font-bold ${prefs.days === d ? 'bg-stone-900 text-white border-stone-900' : 'border-stone-200'}`}
                    >
                      {d === 5 ? '5 Tage (Mo–Fr)' : '7 Tage (Vollwoche)'}
                    </button>
                  ))}
                </div>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-ink-muted">Wochenbudget (Haushalt)</span>
                  <span className="text-lg font-extrabold text-brand font-mono">{prefs.budget} €</span>
                </div>
                <input
                  type="range"
                  min={15}
                  max={250}
                  step={5}
                  value={prefs.budget}
                  onChange={(e) => setPrefs({ ...prefs, budget: Number(e.target.value) })}
                  className="w-full accent-brand"
                />
              </div>
            </div>
            <HouseholdEditor prefs={prefs} setPrefs={setPrefs} meta={meta} />
            <div className="flex justify-between">
              <button type="button" onClick={() => setStep(1)} className="px-5 py-3 rounded-xl border border-stone-200 text-xs font-bold flex items-center gap-1.5">
                <ArrowLeft className="w-4 h-4" /> Zurück
              </button>
              <button type="button" onClick={() => setStep(3)} className="px-6 py-3.5 rounded-xl bg-brand text-white font-bold text-sm flex items-center gap-2">
                Weiter zu Vorräte <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="bg-surface rounded-3xl p-6 sm:p-10 border border-stone-200/80 space-y-8">
            <div>
              <span className="text-xs font-bold text-brand uppercase tracking-wider">Schritt 3</span>
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight mt-1">Hast du schon Vorräte zuhause?</h1>
              <p className="text-sm text-ink-muted mt-1">Diese Zutaten landen nicht auf dem Einkaufszettel.</p>
            </div>
            <div className="p-4 rounded-2xl bg-stone-50 border border-stone-200/60 text-xs font-bold">
              {prefs.store} • {dietName} • {prefs.calories} kcal • {prefs.protein}g Protein • {prefs.portions} Portion{prefs.portions > 1 ? 'en' : ''} • Max. {prefs.budget} €
            </div>
            <div className="flex flex-wrap gap-2.5">
              {meta.pantry_staples.map((item) => {
                const on = prefs.pantry.includes(item.name)
                return (
                  <button
                    key={item.name}
                    type="button"
                    onClick={() =>
                      setPrefs({
                        ...prefs,
                        pantry: on ? prefs.pantry.filter((x) => x !== item.name) : [...prefs.pantry, item.name],
                      })
                    }
                    className={`px-4 py-2.5 rounded-full border text-xs ${on ? 'bg-brand/10 text-brand border-brand/40 font-bold' : 'border-stone-200 text-ink'}`}
                  >
                    {item.name} <span className="text-[10px] text-ink-muted">{item.hint}</span>
                  </button>
                )
              })}
            </div>
            {error && <p className="text-sm text-red-700">{error}</p>}
            <div className="flex justify-between gap-4">
              <button type="button" onClick={() => setStep(2)} className="px-5 py-3 rounded-xl border border-stone-200 text-xs font-bold flex items-center gap-1.5">
                <ArrowLeft className="w-4 h-4" /> Zurück
              </button>
              <button type="submit" disabled={busy} className="flex-1 max-w-sm py-4 rounded-xl bg-brand text-white font-extrabold text-sm flex items-center justify-center gap-2 disabled:opacity-60">
                {busy ? 'Wochenplan wird gerechnet…' : 'Wochenplan berechnen'}
                <Sparkles className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </form>
    </div>
  )
}

function HouseholdEditor({
  prefs,
  setPrefs,
  meta,
}: {
  prefs: Prefs
  setPrefs: (p: Prefs) => void
  meta: Meta
}) {
  const members = prefs.members?.length ? prefs.members : [DEFAULT_MEMBER]
  const [openCalc, setOpenCalc] = useState<string | null>(null)

  function commit(next: HouseholdMember[]) {
    setPrefs({ ...prefs, ...withMembers(next) })
  }

  return (
    <div className="space-y-3 pt-2 border-t border-stone-100">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-wider text-ink-muted">Personen im Haushalt</span>
        <button
          type="button"
          disabled={members.length >= 6}
          onClick={() =>
            commit([...members, { id: `m${Date.now()}`, name: `Person ${members.length + 1}`, calories: 2000, protein: 120 }])
          }
          className="text-xs font-bold text-brand"
        >
          + Person
        </button>
      </div>
      <p className="text-xs text-ink-muted">
        Jede Person hat eigene kcal/Protein. Gekocht wird {members.length} Portion{members.length > 1 ? 'en' : ''}; der Plan zielt auf den Durchschnitt ({prefs.calories} kcal / {prefs.protein} g).
      </p>
      {members.map((m) => (
        <div key={m.id} className="p-4 rounded-2xl border border-stone-200 space-y-3 bg-stone-50/80">
          <div className="flex gap-2">
            <input
              value={m.name}
              onChange={(e) => commit(members.map((x) => (x.id === m.id ? { ...x, name: e.target.value } : x)))}
              className="flex-1 rounded-xl border border-stone-200 px-3 py-2 text-sm font-semibold"
            />
            {members.length > 1 && (
              <button type="button" className="text-xs text-red-700 font-bold" onClick={() => commit(members.filter((x) => x.id !== m.id))}>
                Entfernen
              </button>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <label className="text-[11px] font-bold text-ink-muted">
              kcal
              <input
                type="number"
                min={1200}
                max={4000}
                step={50}
                value={m.calories}
                onChange={(e) => commit(members.map((x) => (x.id === m.id ? { ...x, calories: Number(e.target.value) } : x)))}
                className="mt-1 w-full rounded-lg border px-2 py-1.5 font-mono text-sm"
              />
            </label>
            <label className="text-[11px] font-bold text-ink-muted">
              Protein g
              <input
                type="number"
                min={50}
                max={250}
                step={5}
                value={m.protein}
                onChange={(e) => commit(members.map((x) => (x.id === m.id ? { ...x, protein: Number(e.target.value) } : x)))}
                className="mt-1 w-full rounded-lg border px-2 py-1.5 font-mono text-sm"
              />
            </label>
          </div>
          <button type="button" className="text-xs font-bold text-brand" onClick={() => setOpenCalc(openCalc === m.id ? null : m.id)}>
            {openCalc === m.id ? 'Rechner schließen' : 'Bedarf berechnen (Alter, Gewicht, Sport)'}
          </button>
          {openCalc === m.id && (
            <CalculatorForm
              onApply={(calories, protein) => {
                commit(members.map((x) => (x.id === m.id ? { ...x, calories, protein } : x)))
                setOpenCalc(null)
              }}
              meta={meta}
            />
          )}
        </div>
      ))}
    </div>
  )
}

function CalculatorForm({
  onApply,
  meta,
}: {
  onApply: (calories: number, protein: number) => void
  meta: Meta
}) {
  const [sex, setSex] = useState('female')
  const [age, setAge] = useState('32')
  const [height, setHeight] = useState('170')
  const [weight, setWeight] = useState('70')
  const [activity, setActivity] = useState('moderate')
  const [goal, setGoal] = useState('maintain')
  const [result, setResult] = useState<{ calories: number; protein: number; tdee: number; bmr: number } | null>(null)
  const [err, setErr] = useState('')

  async function run() {
    setErr('')
    try {
      const data = await api<{ calories: number; protein: number; tdee: number; bmr: number }>('/api/calculator', {
        method: 'POST',
        json: { sex, age: Number(age), height_cm: Number(height), weight_kg: Number(weight), activity, goal },
      })
      setResult(data)
    } catch {
      setErr('Bitte Angaben prüfen.')
    }
  }

  return (
    <div className="space-y-2 text-xs bg-white rounded-xl border border-stone-200 p-3">
      <div className="grid grid-cols-2 gap-2">
        <select value={sex} onChange={(e) => setSex(e.target.value)} className="border rounded-lg px-2 py-1.5">
          <option value="female">Frau</option>
          <option value="male">Mann</option>
        </select>
        <select value={goal} onChange={(e) => setGoal(e.target.value)} className="border rounded-lg px-2 py-1.5">
          {(meta.goals || [{ id: 'maintain', name: 'Halten' }]).map((g) => (
            <option key={g.id} value={g.id}>{g.name}</option>
          ))}
        </select>
        <label>Alter <input value={age} onChange={(e) => setAge(e.target.value)} className="border rounded-lg px-2 py-1 w-full" /></label>
        <label>Größe cm <input value={height} onChange={(e) => setHeight(e.target.value)} className="border rounded-lg px-2 py-1 w-full" /></label>
        <label>Gewicht kg <input value={weight} onChange={(e) => setWeight(e.target.value)} className="border rounded-lg px-2 py-1 w-full" /></label>
        <select value={activity} onChange={(e) => setActivity(e.target.value)} className="border rounded-lg px-2 py-1.5">
          {(meta.activity_levels || []).map((a) => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
      </div>
      <button type="button" onClick={() => void run()} className="px-3 py-1.5 rounded-lg bg-stone-900 text-white font-bold">Berechnen</button>
      {err && <p className="text-red-700">{err}</p>}
      {result && (
        <div className="flex items-center justify-between gap-2">
          <span>Grundumsatz {result.bmr} · Verbrauch {result.tdee} → <b>{result.calories} kcal / {result.protein} g Protein</b></span>
          <button type="button" className="font-bold text-brand" onClick={() => onApply(result.calories, result.protein)}>Übernehmen</button>
        </div>
      )}
    </div>
  )
}
