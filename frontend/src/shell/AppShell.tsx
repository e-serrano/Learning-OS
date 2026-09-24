import { NavLink, Outlet } from 'react-router-dom'
import './AppShell.css'

/** Layout for the app once onboarding is complete (docs/TASKS.md T109) --
 * left nav plus a routed content area. Nav only links to goal-agnostic
 * pages (Dashboard, Reviews, Vault, Settings); goal-scoped routes
 * (goal/roadmap/knowledge/session/assessment/project) are reachable by
 * URL and get their own links once the Dashboard (T111) can list goals. */
export function AppShell() {
  return (
    <div className="app-shell">
      <nav className="app-nav">
        <span className="app-nav-brand">Learning OS</span>
        <NavLink to="/" end>
          Dashboard
        </NavLink>
        <NavLink to="/reviews">Reviews</NavLink>
        <NavLink to="/vault">Vault</NavLink>
        <NavLink to="/settings">Settings</NavLink>
      </nav>
      <main className="app-content">
        <Outlet />
      </main>
    </div>
  )
}
