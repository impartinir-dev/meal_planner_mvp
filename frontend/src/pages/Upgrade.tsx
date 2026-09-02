import { Link } from 'react-router-dom'
import { ScanLine, ShoppingBasket, Sparkles } from 'lucide-react'
import { useAuth } from '../auth'

export default function Upgrade() {
  const { user } = useAuth()
  if (user?.is_pro) {
    return (
      <div className="max-w-lg mx-auto text-center space-y-3">
        <p className="font-bold">Du hast NutriMatch Pro.</p>
        <Link to="/vorrat" className="text-brand font-bold text-sm">Zum Vorratsschrank</Link>
      </div>
    )
  }
  return (
    <div className="max-w-lg mx-auto space-y-6">
      <div>
        <p className="text-xs font-bold uppercase tracking-wider text-brand">Freemium</p>
        <h1 className="text-3xl font-extrabold mt-1">NutriMatch Pro</h1>
        <p className="text-ink-muted text-sm mt-2">
          Der Wochenplan bleibt kostenlos. Pro merkt sich deinen echten Vorrat — inklusive Kassenbon-Foto.
        </p>
      </div>
      <div className="bg-surface rounded-3xl border border-stone-200 p-8 space-y-5">
        <p className="text-4xl font-black font-mono">4,99 €<span className="text-base font-semibold text-ink-muted"> / Monat</span></p>
        <ul className="space-y-3 text-sm">
          <li className="flex gap-2"><ShoppingBasket className="w-4 h-4 text-brand mt-0.5" /> Persistenter Vorratsschrank mit Mengen</li>
          <li className="flex gap-2"><ScanLine className="w-4 h-4 text-brand mt-0.5" /> Kassenbon fotografieren, Zutaten landen im Schrank</li>
          <li className="flex gap-2"><Sparkles className="w-4 h-4 text-brand mt-0.5" /> Der nächste Plan zieht den Schrank automatisch ab</li>
        </ul>
        <p className="text-xs text-ink-muted">
          Zahlung läuft über den Admin (Überweisung / später Stripe). Schreib uns, dann wird dein Konto auf Pro gestellt.
        </p>
      </div>
    </div>
  )
}
