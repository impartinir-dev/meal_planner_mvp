import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth'
import Layout from './components/Layout'
import Home from './pages/Home'
import Invites from './pages/Invites'
import Login from './pages/Login'
import PlanPage from './pages/Plan'
import Register from './pages/Register'
import Setup from './pages/Setup'
import Shopping from './pages/Shopping'
import Cupboard from './pages/Cupboard'
import Upgrade from './pages/Upgrade'
import DealsAdmin from './pages/DealsAdmin'
import Profile from './pages/Profile'
import type { ReactNode } from 'react'

function Guard({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <p className="p-8 text-sm text-ink-muted">Lade…</p>
  if (!user) return <Navigate to="/login" replace />
  return children
}

function Guest({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <p className="p-8 text-sm text-ink-muted">Lade…</p>
  if (user) return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route
            path="/login"
            element={
              <Guest>
                <Login />
              </Guest>
            }
          />
          <Route
            path="/register"
            element={
              <Guest>
                <Register />
              </Guest>
            }
          />
          <Route
            element={
              <Guard>
                <Layout />
              </Guard>
            }
          >
            <Route path="/" element={<Home />} />
            <Route path="/setup" element={<Setup />} />
            <Route path="/plan" element={<PlanPage />} />
            <Route path="/einkaufszettel" element={<Shopping />} />
            <Route path="/einladungen" element={<Invites />} />
            <Route path="/vorrat" element={<Cupboard />} />
            <Route path="/pro" element={<Upgrade />} />
            <Route path="/profil" element={<Profile />} />
            <Route path="/angebote" element={<DealsAdmin />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
