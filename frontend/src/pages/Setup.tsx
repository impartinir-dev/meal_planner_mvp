import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Sparkles, Tag } from 'lucide-react'
import { api } from '../api'
import HouseholdEditor, { DEFAULT_MEMBER, withMembers } from '../components/HouseholdEditor'
import type { Meta, PlanPayload, Prefs, Profile } from '../types'

const DEFAULT_EQ = ['stovetop', 'pan', 'saucepan', 'pot', 'oven']

const EQ_LABEL: Record<string, string> = {
  stovetop: 'Herd',
  pan: 'Pfanne',
  saucepan: 'Stielkasserolle',
  pot: 'Töpfe',
  oven: 'Backofen',
  airfryer: 'Heißluftfritteuse',
  microwave: 'Mikrowelle',
  blender: 'Mixer',
  kettle: 'Wasserkocher',
  toaster: 'Toaster',
  'no-cook': 'Kein Kochen',
}

const DEFAULT: Prefs = {
  store: 'lidl',
  diet: 'High-Protein',
  budget: 50,
  days: 7,
  calories: 2200,
  protein: 140,
  pantry: ['Reis', 'Haferflocken'],
  portions: 1,
  exclude: [],
  members: [DEFAULT_MEMBER],
  equipment: DEFAULT_EQ,
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
      const liveId = m.stores[0]?.id || 'lidl'
      let household = [DEFAULT_MEMBER]
      try {
        const profile = await api<Profile>('/api/profile')
        if (profile.members?.length) household = profile.members
      } catch {
        household = [DEFAULT_MEMBER]
      }
      try {
        const existing = await api<PlanPayload>('/api/plan')
        const merged = {
          ...DEFAULT,
          ...existing.prefs,
          exclude: existing.prefs.exclude || [],
          equipment: existing.prefs.equipment?.length ? existing.prefs.equipment : DEFAULT_EQ,
          ...withMembers(household),
        }
        if (!m.stores.some((s) => s.id === merged.store)) merged.store = liveId
        setPrefs(merged)
      } catch {
        setPrefs({ ...DEFAULT, store: liveId, ...withMembers(household) })
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
      nav('/')
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
      active ? 'border-brand' : done ? 'border-zinc-800' : 'border-zinc-200'
    }`
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div className="space-y-4">
        <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-ink-muted">
          <span>Konfigurator</span>
          <span>Schritt {step} von 4</span>
        </div>
        <div className="grid grid-cols-4 gap-2">
          {[1, 2, 3, 4].map((n) => (
            <button key={n} type="button" onClick={() => setStep(n)} className={stepNavClass(n)}>
              <span className={`block text-[11px] font-bold ${n === step ? 'text-brand' : n < step ? 'text-zinc-800' : 'text-ink-muted'}`}>
                {n === 1 ? '1. Markt' : n === 2 ? '2. Haushalt' : n === 3 ? '3. Küche' : '4. Reste'}
              </span>
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={onSubmit}>
        {step === 1 && (
          <div className="bg-surface rounded-3xl p-6 sm:p-10 border border-zinc-200/80 space-y-6">
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
                  <div className="p-5 rounded-2xl border border-zinc-200 peer-checked:border-brand peer-checked:bg-zinc-50/80 hover:bg-zinc-50 transition-all flex flex-col justify-between h-32 text-left">
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
          <div className="bg-surface rounded-3xl p-6 sm:p-10 border border-zinc-200/80 space-y-8">
            <div>
              <span className="text-xs font-bold text-brand uppercase tracking-wider">Schritt 2</span>
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight mt-1">Dein Ernährungsziel &amp; Budget</h1>
            </div>
            <div className="flex flex-wrap gap-2.5">
              {meta.diets.map((diet) => (
                <label key={diet.id} className="cursor-pointer">
                  <input type="radio" className="peer sr-only" checked={prefs.diet === diet.id} onChange={() => setPrefs({ ...prefs, diet: diet.id })} />
                  <div className="px-4 py-2.5 rounded-full border border-zinc-200 text-sm font-semibold peer-checked:bg-brand peer-checked:text-white peer-checked:border-brand">
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
                      className={`px-3 py-1.5 rounded-full border text-xs font-semibold ${on ? 'bg-red-50 text-red-800 border-red-200' : 'border-zinc-200'}`}
                    >
                      Ohne {a.name}
                    </button>
                  )
                })}
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-4 border-t border-zinc-100">
              <div className="space-y-3">
                <span className="text-xs font-bold uppercase tracking-wider text-ink-muted">Zeitraum</span>
                <div className="grid grid-cols-2 gap-2">
                  {[5, 7].map((d) => (
                    <button
                      key={d}
                      type="button"
                      onClick={() => setPrefs({ ...prefs, days: d })}
                      className={`py-2.5 px-3 rounded-xl border text-xs font-bold ${prefs.days === d ? 'bg-zinc-900 text-white border-zinc-900' : 'border-zinc-200'}`}
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
            <HouseholdEditor
              members={prefs.members}
              meta={meta}
              onChange={(members) => setPrefs({ ...prefs, ...withMembers(members) })}
            />
            <div className="flex justify-between">
              <button type="button" onClick={() => setStep(1)} className="px-5 py-3 rounded-xl border border-zinc-200 text-xs font-bold flex items-center gap-1.5">
                <ArrowLeft className="w-4 h-4" /> Zurück
              </button>
              <button type="button" onClick={() => setStep(3)} className="px-6 py-3.5 rounded-xl bg-brand text-white font-bold text-sm flex items-center gap-2">
                Weiter zur Küche <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="bg-surface rounded-3xl p-6 sm:p-10 border border-zinc-200/80 space-y-8">
            <div>
              <span className="text-xs font-bold text-brand uppercase tracking-wider">Schritt 3</span>
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight mt-1">Was steht in deiner Küche?</h1>
              <p className="text-sm text-ink-muted mt-1">Ohne Backofen keine Ofengerichte. Ohne Pfanne keine Brat-Rezepte.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {(Object.keys(EQ_LABEL) as string[]).filter((id) => id !== 'no-cook').map((id) => {
                const on = (prefs.equipment || []).includes(id)
                return (
                  <button
                    key={id}
                    type="button"
                    onClick={() =>
                      setPrefs({
                        ...prefs,
                        equipment: on ? prefs.equipment.filter((x) => x !== id) : [...(prefs.equipment || []), id],
                      })
                    }
                    className={`px-4 py-2.5 rounded-full border text-xs font-semibold ${on ? 'bg-brand text-white border-brand' : 'border-zinc-200'}`}
                  >
                    {EQ_LABEL[id]}
                  </button>
                )
              })}
            </div>
            <div className="flex justify-between">
              <button type="button" onClick={() => setStep(2)} className="px-5 py-3 rounded-xl border border-zinc-200 text-xs font-bold flex items-center gap-1.5">
                <ArrowLeft className="w-4 h-4" /> Zurück
              </button>
              <button type="button" onClick={() => setStep(4)} className="px-6 py-3.5 rounded-xl bg-brand text-white font-bold text-sm flex items-center gap-2">
                Weiter zu Resten <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="bg-surface rounded-3xl p-6 sm:p-10 border border-zinc-200/80 space-y-8">
            <div>
              <span className="text-xs font-bold text-brand uppercase tracking-wider">Schritt 4 · Zero Waste</span>
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight mt-1">Was ist noch im Haus?</h1>
              <p className="text-sm text-ink-muted mt-1">Diese Zutaten landen nicht auf dem Einkaufszettel.</p>
            </div>
            <div className="p-4 rounded-2xl bg-zinc-50 border border-zinc-200/60 text-xs font-bold">
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
                    className={`px-4 py-2.5 rounded-full border text-xs ${on ? 'bg-brand/10 text-brand border-brand/40 font-bold' : 'border-zinc-200 text-ink'}`}
                  >
                    {item.name} <span className="text-[10px] text-ink-muted">{item.hint}</span>
                  </button>
                )
              })}
            </div>
            {error && <p className="text-sm text-red-700">{error}</p>}
            <div className="flex justify-between gap-4">
              <button type="button" onClick={() => setStep(3)} className="px-5 py-3 rounded-xl border border-zinc-200 text-xs font-bold flex items-center gap-1.5">
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
