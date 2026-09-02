import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { LogOut, SlidersHorizontal, Sparkle, UserRound } from 'lucide-react'
import { useAuth } from '../auth'
import { api } from '../api'

export default function Layout() {
  const { user, logout } = useAuth()
  const [version, setVersion] = useState('')
  useEffect(() => {
    void api<{ version: string }>('/api/version').then((v) => setVersion(v.version)).catch(() => undefined)
  }, [])

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3.5 py-1.5 rounded-full transition-colors ${
      isActive ? 'bg-zinc-100 text-brand font-semibold' : 'text-ink-muted hover:text-ink hover:bg-zinc-50'
    }`

  return (
    <div className="min-h-full flex flex-col font-sans antialiased text-ink bg-canvas">
      <header className="bg-surface/90 backdrop-blur-md border-b border-zinc-200/80 sticky top-0 z-40">
        <div className="max-w-[1120px] mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 group">
            <span className="w-8 h-8 rounded-full bg-brand text-white flex items-center justify-center shadow-xs">
              <Sparkle className="w-4 h-4" />
            </span>
            <span className="font-extrabold text-lg tracking-tight text-ink group-hover:text-brand transition-colors">
              Nutri<span className="text-brand">Match</span>
            </span>
            {(user?.plan_tier === 'plus' || user?.plan_tier === 'premium' || user?.is_pro) && (
              <span className="text-[10px] font-extrabold uppercase tracking-wider bg-brand text-white px-1.5 py-0.5 rounded">
                {user?.plan_tier === 'premium' ? 'Premium' : 'Plus'}
              </span>
            )}
          </Link>
          <nav className="flex items-center gap-1 sm:gap-2 text-sm font-medium overflow-x-auto">
            <NavLink to="/" end className={linkClass}>Heute</NavLink>
            <NavLink to="/plan" className={linkClass}>Wochenplan</NavLink>
            <NavLink to="/einkaufszettel" className={linkClass}>Einkaufszettel</NavLink>
            {(user?.is_pro || user?.plan_tier === 'plus' || user?.plan_tier === 'premium') && (
              <NavLink to="/vorrat" className={linkClass}>Vorrat</NavLink>
            )}
            <NavLink to="/pro" className={linkClass}>Abo</NavLink>
            <NavLink to="/profil" className={linkClass}>
              <span className="inline-flex items-center gap-1"><UserRound className="w-3.5 h-3.5" />Profil</span>
            </NavLink>
            {user?.is_admin && (
              <>
                <NavLink to="/einladungen" className={linkClass}>Admin</NavLink>
                <NavLink to="/angebote" className={linkClass}>Angebote</NavLink>
              </>
            )}
            <Link
              to="/setup"
              className="ml-2 px-4 py-1.5 rounded-full border border-zinc-300 hover:border-brand text-ink hover:text-brand transition-all text-xs font-semibold flex items-center gap-1.5 whitespace-nowrap"
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>Neuer Plan</span>
            </Link>
            <button type="button" onClick={() => void logout()} className="p-2 text-ink-muted hover:text-ink" title="Abmelden">
              <LogOut className="w-4 h-4" />
            </button>
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-[1120px] w-full mx-auto px-4 sm:px-6 py-8 sm:py-12">
        <Outlet />
      </main>
      <footer className="border-t border-zinc-200/80 py-8 text-center text-xs text-ink-muted">
        <p className="font-semibold text-ink">NutriMatch Deutschland {version && <span className="font-mono">v{version}</span>}</p>
        <p>Smarter Wocheneinkauf nach kuratierten Wochenangeboten &amp; Zero Food Waste.</p>
      </footer>
    </div>
  )
}
