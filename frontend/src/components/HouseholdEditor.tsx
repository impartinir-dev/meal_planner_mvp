import { useState } from 'react'
import { api } from '../api'
import type { HouseholdMember, MemberRole, Meta, Prefs } from '../types'

export const DEFAULT_MEMBER: HouseholdMember = { id: 'self', name: 'Ich', role: 'ich', calories: 2200, protein: 140 }

export const ROLE_LABEL: Record<MemberRole, string> = {
  ich: 'Ich',
  partner: 'Partner',
  kind: 'Kind',
  mitbewohner: 'Mitbewohner',
  andere: 'Andere',
}

export function withMembers(members: HouseholdMember[]): Pick<Prefs, 'members' | 'portions' | 'calories' | 'protein'> {
  const list = members.length ? members : [DEFAULT_MEMBER]
  const n = list.length
  return {
    members: list,
    portions: n,
    calories: Math.round(list.reduce((s, m) => s + m.calories, 0) / n),
    protein: Math.round(list.reduce((s, m) => s + m.protein, 0) / n),
  }
}

export default function HouseholdEditor({
  members,
  onChange,
  meta,
}: {
  members: HouseholdMember[]
  onChange: (next: HouseholdMember[]) => void
  meta: Meta
}) {
  const list = members.length ? members : [DEFAULT_MEMBER]
  const [openCalc, setOpenCalc] = useState<string | null>(null)

  function commit(next: HouseholdMember[]) {
    onChange(next.length ? next : [DEFAULT_MEMBER])
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-wider text-ink-muted">Personen im Haushalt</span>
        <button
          type="button"
          disabled={list.length >= 6}
          onClick={() =>
            commit([
              ...list,
              {
                id: `m${Date.now()}`,
                name: `Person ${list.length + 1}`,
                role: 'mitbewohner',
                calories: 2000,
                protein: 120,
              },
            ])
          }
          className="text-xs font-bold text-brand"
        >
          + Person
        </button>
      </div>
      <p className="text-xs text-ink-muted">
        Familie, Mitbewohner, wer mitisst. Gekocht wird {list.length} Portion{list.length > 1 ? 'en' : ''}.
        Ziel ist die Summe ({list.reduce((s, m) => s + m.calories, 0)} kcal / {list.reduce((s, m) => s + m.protein, 0)} g).
      </p>
      {list.map((m) => (
        <div key={m.id} className="p-4 rounded-2xl border border-zinc-200 space-y-3 bg-zinc-50/80">
          <div className="flex gap-2">
            <input
              value={m.name}
              onChange={(e) => commit(list.map((x) => (x.id === m.id ? { ...x, name: e.target.value } : x)))}
              className="flex-1 rounded-xl border border-zinc-200 px-3 py-2 text-sm font-semibold"
            />
            <select
              value={m.role || 'andere'}
              onChange={(e) => commit(list.map((x) => (x.id === m.id ? { ...x, role: e.target.value as MemberRole } : x)))}
              className="rounded-xl border border-zinc-200 px-2 py-2 text-xs font-semibold"
            >
              {(Object.keys(ROLE_LABEL) as MemberRole[]).map((role) => (
                <option key={role} value={role}>
                  {ROLE_LABEL[role]}
                </option>
              ))}
            </select>
            {list.length > 1 && (
              <button type="button" className="text-xs text-red-700 font-bold" onClick={() => commit(list.filter((x) => x.id !== m.id))}>
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
                onChange={(e) => commit(list.map((x) => (x.id === m.id ? { ...x, calories: Number(e.target.value) } : x)))}
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
                onChange={(e) => commit(list.map((x) => (x.id === m.id ? { ...x, protein: Number(e.target.value) } : x)))}
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
                commit(list.map((x) => (x.id === m.id ? { ...x, calories, protein } : x)))
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
    <div className="space-y-2 text-xs bg-white rounded-xl border border-zinc-200 p-3">
      <div className="grid grid-cols-2 gap-2">
        <select value={sex} onChange={(e) => setSex(e.target.value)} className="border rounded-lg px-2 py-1.5">
          <option value="female">Frau</option>
          <option value="male">Mann</option>
        </select>
        <select value={goal} onChange={(e) => setGoal(e.target.value)} className="border rounded-lg px-2 py-1.5">
          {(meta.goals || [{ id: 'maintain', name: 'Halten' }]).map((g) => (
            <option key={g.id} value={g.id}>
              {g.name}
            </option>
          ))}
        </select>
        <label>
          Alter <input value={age} onChange={(e) => setAge(e.target.value)} className="border rounded-lg px-2 py-1 w-full" />
        </label>
        <label>
          Größe cm <input value={height} onChange={(e) => setHeight(e.target.value)} className="border rounded-lg px-2 py-1 w-full" />
        </label>
        <label>
          Gewicht kg <input value={weight} onChange={(e) => setWeight(e.target.value)} className="border rounded-lg px-2 py-1 w-full" />
        </label>
        <select value={activity} onChange={(e) => setActivity(e.target.value)} className="border rounded-lg px-2 py-1.5">
          {(meta.activity_levels || []).map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
      </div>
      <button type="button" onClick={() => void run()} className="px-3 py-1.5 rounded-lg bg-zinc-900 text-white font-bold">
        Berechnen
      </button>
      {err && <p className="text-red-700">{err}</p>}
      {result && (
        <div className="flex items-center justify-between gap-2">
          <span>
            Grundumsatz {result.bmr} · Verbrauch {result.tdee} →{' '}
            <b>
              {result.calories} kcal / {result.protein} g Protein
            </b>
          </span>
          <button type="button" className="font-bold text-brand" onClick={() => onApply(result.calories, result.protein)}>
            Übernehmen
          </button>
        </div>
      )}
    </div>
  )
}
