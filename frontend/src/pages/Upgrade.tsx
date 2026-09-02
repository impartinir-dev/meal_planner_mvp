import { Link } from 'react-router-dom'
import { ScanLine, ShoppingBasket, Sparkles, Utensils } from 'lucide-react'
import { useAuth } from '../auth'

export default function Upgrade() {
  const { user } = useAuth()
  const tier = user?.plan_tier || (user?.is_pro ? 'plus' : 'free')
  const preview = Boolean(user?.is_admin) || tier === 'plus' || tier === 'premium'
  const previewLabel = user?.is_admin ? 'Admin / Premium' : tier === 'premium' ? 'Premium' : 'Plus'

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {preview && (
        <p className="text-xs font-semibold bg-brand/10 text-brand border border-brand/20 rounded-xl px-3 py-2">
          Vorschau der Kaufmaske — dein Konto ist {previewLabel}. Die Karten sehen so aus wie für einen Free-Nutzer.
        </p>
      )}
      <div>
        <p className="text-xs font-bold uppercase tracking-wider text-brand">Abo</p>
        <h1 className="text-3xl font-extrabold mt-1">Zero Waste, richtig.</h1>
        <p className="text-ink-muted text-sm mt-2">
          Der Wochenplan bleibt kostenlos. Plus merkt sich den Schrank. Premium liest den Kassenbon.
        </p>
      </div>
      <div className="grid sm:grid-cols-2 gap-4">
        <div className="bg-surface rounded-3xl border border-zinc-200 p-8 space-y-5">
          <p className="text-xs font-bold uppercase text-ink-muted">Plus</p>
          <p className="text-4xl font-black font-mono">
            4,99 €<span className="text-base font-semibold text-ink-muted"> / Monat</span>
          </p>
          <ul className="space-y-3 text-sm">
            <li className="flex gap-2">
              <ShoppingBasket className="w-4 h-4 text-brand mt-0.5" /> Vorratsschrank mit Mengen, frei eintragen
            </li>
            <li className="flex gap-2">
              <Utensils className="w-4 h-4 text-brand mt-0.5" /> Reste nach „Gekocht“ abziehen, nächste Woche weniger kaufen
            </li>
            <li className="flex gap-2">
              <Sparkles className="w-4 h-4 text-brand mt-0.5" /> Zero-Waste-€ auf Plan und Zettel
            </li>
          </ul>
          <button type="button" disabled className="w-full py-3 rounded-xl bg-brand text-white text-sm font-bold disabled:opacity-80">
            Plus wählen
          </button>
          <p className="text-xs text-ink-muted">Checkout kommt mit Stripe. Bis dahin schaltet der Admin frei.</p>
        </div>
        <div className="bg-zinc-900 text-white rounded-3xl border border-zinc-900 p-8 space-y-5">
          <p className="text-xs font-bold uppercase text-zinc-400">Premium</p>
          <p className="text-4xl font-black font-mono">
            8,99 €<span className="text-base font-semibold text-zinc-400"> / Monat</span>
          </p>
          <ul className="space-y-3 text-sm">
            <li className="flex gap-2">
              <ScanLine className="w-4 h-4 mt-0.5" /> Alles aus Plus
            </li>
            <li className="flex gap-2">
              <ScanLine className="w-4 h-4 mt-0.5" /> Kassenbon fotografieren → landet im Schrank
            </li>
          </ul>
          <button type="button" disabled className="w-full py-3 rounded-xl bg-white text-zinc-900 text-sm font-bold disabled:opacity-90">
            Premium wählen
          </button>
          <p className="text-xs text-zinc-400">Checkout kommt mit Stripe. Bis dahin schaltet der Admin frei.</p>
        </div>
      </div>
      {(tier === 'plus' || tier === 'premium' || user?.is_admin) && (
        <p className="text-center">
          <Link to="/vorrat" className="text-brand font-bold text-sm">
            Zum Vorratsschrank
          </Link>
        </p>
      )}
    </div>
  )
}
