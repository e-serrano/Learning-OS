import { NavLink, Outlet } from 'react-router-dom'
import { useTranslation } from '../i18n/LanguageContext'
import { LanguageToggle } from '../i18n/LanguageToggle'
import './AppShell.css'

/** Layout for the app once onboarding is complete (docs/TASKS.md T109) --
 * left nav plus a routed content area. Nav only links to goal-agnostic
 * pages (Dashboard, Reviews, Vault, Settings); goal-scoped routes
 * (goal/roadmap/knowledge/session/assessment/project) are reachable by
 * URL and get their own links once the Dashboard (T111) can list goals.
 *
 * `LanguageToggle` (docs/TASKS.md T147) lives here -- the "general UI"
 * the user asked for, visible on every routed page. */
export function AppShell() {
  const { t } = useTranslation()
  return (
    <div className="app-shell">
      <nav className="app-nav">
        <span className="app-nav-brand">Learning OS</span>
        <NavLink to="/" end>
          {t('nav.dashboard')}
        </NavLink>
        <NavLink to="/reviews">{t('nav.reviews')}</NavLink>
        <NavLink to="/vault">{t('nav.vault')}</NavLink>
        <NavLink to="/settings">{t('nav.settings')}</NavLink>
        <LanguageToggle />
      </nav>
      <main className="app-content">
        <Outlet />
      </main>
    </div>
  )
}
