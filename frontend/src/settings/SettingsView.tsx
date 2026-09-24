import { type ChangeEvent, useEffect, useState } from 'react'
import { ApiError, getSettings, updateGitAutoCommit, updateLanguage } from '../api/settings'
import { AIProviderSettings } from './AIProviderSettings'
import './settings.css'

type Phase = 'loading' | 'error' | 'ready'

/** Settings page (user request, 2026-09-24): a single app-wide language
 * preference that steers both the UI's own copy and every AI-generated
 * response, including Obsidian note content the curator writes
 * (`AIOrchestrator.generate` injects `constraints.language` into every
 * AI call from the configured value -- see docs/AI_CONTRACTS.md #2).
 *
 * Also carries the opt-in git auto-commit toggle (docs/TASKS.md T138):
 * once on, every vault write the app makes is committed to the vault's
 * own git history automatically -- no separate action per change,
 * disabled and hidden behind a plain checkbox when the vault isn't a
 * git repo at all.
 *
 * The AI provider section (docs/TASKS.md T146) is its own component,
 * `AIProviderSettings` -- separate data source (`GET /onboarding/status`,
 * not `GET /settings`), so it loads/errors independently. */
export function SettingsView() {
  const [phase, setPhase] = useState<Phase>('loading')
  const [error, setError] = useState<string | null>(null)
  const [language, setLanguage] = useState('en')
  const [languages, setLanguages] = useState<Record<string, string>>({})
  const [gitAutoCommit, setGitAutoCommit] = useState(false)
  const [gitAvailable, setGitAvailable] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getSettings()
      .then((settings) => {
        setLanguage(settings.language)
        setLanguages(settings.supported_languages)
        setGitAutoCommit(settings.git_auto_commit)
        setGitAvailable(settings.git_available)
        setPhase('ready')
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
        setPhase('error')
      })
  }, [])

  async function handleLanguageChange(event: ChangeEvent<HTMLSelectElement>) {
    const next = event.target.value
    setLanguage(next)
    setSaving(true)
    setSaved(false)
    setError(null)
    try {
      const settings = await updateLanguage(next)
      setLanguage(settings.language)
      setSaved(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    } finally {
      setSaving(false)
    }
  }

  async function handleGitAutoCommitChange(event: ChangeEvent<HTMLInputElement>) {
    const next = event.target.checked
    setGitAutoCommit(next)
    setSaving(true)
    setSaved(false)
    setError(null)
    try {
      const settings = await updateGitAutoCommit(next)
      setGitAutoCommit(settings.git_auto_commit)
      setSaved(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    } finally {
      setSaving(false)
    }
  }

  if (phase === 'loading') {
    return (
      <div className="settings-view">
        <p>Loading…</p>
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div className="settings-view">
        <div className="message error">{error}</div>
      </div>
    )
  }

  return (
    <div className="settings-view">
      <h2>Settings</h2>

      <label htmlFor="language">Language</label>
      <p className="field-hint">
        Applies to the app and to notes the AI writes into your Obsidian vault.
      </p>
      <select id="language" value={language} onChange={handleLanguageChange} disabled={saving}>
        {Object.entries(languages).map(([code, name]) => (
          <option key={code} value={code}>
            {name}
          </option>
        ))}
      </select>

      <label htmlFor="git-auto-commit" className="checkbox-label">
        <input
          id="git-auto-commit"
          type="checkbox"
          checked={gitAutoCommit}
          onChange={handleGitAutoCommitChange}
          disabled={saving || !gitAvailable}
        />
        Git auto-commit
      </label>
      <p className="field-hint">
        {gitAvailable
          ? 'Automatically commits each vault change the app applies, one commit per file.'
          : 'Your configured vault is not a git repository, so this is unavailable.'}
      </p>

      {saving && <p className="field-hint">Saving…</p>}
      {saved && !saving && <div className="message success">Saved.</div>}
      {error && <div className="message error">{error}</div>}

      <h3>AI provider</h3>
      <AIProviderSettings />
    </div>
  )
}
