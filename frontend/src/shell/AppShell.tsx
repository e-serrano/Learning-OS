import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { listVaultChanges } from '../api/vault'
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
 * the user asked for, visible on every routed page.
 *
 * Pending-changes badge (docs/TASKS.md T155, user request): `GET
 * /vault/changes` already returns only PENDING proposals (T081), so the
 * count is a direct read, no separate "unread" concept needed. Refetches
 * on every navigation (not just once on mount) since `AppShell` itself
 * never remounts between routes -- otherwise the badge would go stale
 * the moment the user approves/rejects a proposal on `/vault`. That
 * still left the count stale for an approve/reject that happens WITHOUT
 * a navigation (staying on `/vault` itself, T161/ISSUE-005) -- fixed by
 * also listening for a `vault:changed` window event `VaultDiffUI`
 * dispatches right after a successful apply/reject, since the two
 * components are router siblings with no other shared state. */
export function AppShell() {
  const { t } = useTranslation()
  const location = useLocation()
  const [pendingChanges, setPendingChanges] = useState(0)

  useEffect(() => {
    let cancelled = false
    function refresh() {
      listVaultChanges()
        .then((res) => {
          if (!cancelled) setPendingChanges(res.changes.length)
        })
        .catch(() => {
          // Best-effort nav badge -- never worth surfacing an error for.
        })
    }
    refresh()
    window.addEventListener('vault:changed', refresh)
    return () => {
      cancelled = true
      window.removeEventListener('vault:changed', refresh)
    }
  }, [location.pathname])

  return (
    <div className="app-shell">
      <nav className="app-nav">
        <span className="app-nav-brand">Learning OS</span>
        <NavLink to="/" end>
          {t('nav.dashboard')}
        </NavLink>
        <NavLink to="/reviews">{t('nav.reviews')}</NavLink>
        <NavLink to="/vault">
          {t('nav.vault')}
          {pendingChanges > 0 && (
            <span
              className="app-nav-badge"
              aria-label={`${pendingChanges} ${t('nav.vaultPendingChangesSuffix')}`}
            >
              {pendingChanges}
            </span>
          )}
        </NavLink>
        <NavLink to="/settings">{t('nav.settings')}</NavLink>
        <LanguageToggle />
      </nav>
      <main className="app-content">
        <Outlet />
      </main>
    </div>
  )
}
