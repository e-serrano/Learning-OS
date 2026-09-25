import { type ChangeEvent, useEffect, useState } from 'react'
import { ApiError, getSettings, updateGitAutoCommit } from '../api/settings'
import { type Language, useTranslation } from '../i18n/LanguageContext'
import { AIProviderSettings } from './AIProviderSettings'
import './settings.css'

type Phase = 'loading' | 'error' | 'ready'

function isSupportedLanguage(value: string): value is Language {
  return value === 'en' || value === 'es'
}

/** Settings page (user request, 2026-09-24): a single app-wide language
 * preference that steers both the UI's own copy and every AI-generated
 * response, including Obsidian note content the curator writes
 * (`AIOrchestrator.generate` injects `constraints.language` into every
 * AI call from the configured value -- see docs/AI_CONTRACTS.md #2).
 * Narrowed to just English/Spanish and reads/writes through the shared
 * `LanguageContext` (docs/TASKS.md T147) rather than its own local
 * state -- otherwise this dropdown and the nav-bar flag toggle
 * (`AppShell`) would each hold their own copy of "the current
 * language" and drift out of sync with each other.
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
  const { language, setLanguage, t } = useTranslation()
  const [phase, setPhase] = useState<Phase>('loading')
  const [error, setError] = useState<string | null>(null)
  const [languages, setLanguages] = useState<Record<string, string>>({})
  const [gitAutoCommit, setGitAutoCommit] = useState(false)
  const [gitAvailable, setGitAvailable] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getSettings()
      .then((settings) => {
        setLanguages(settings.supported_languages)
        setGitAutoCommit(settings.git_auto_commit)
        setGitAvailable(settings.git_available)
        setPhase('ready')
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : t('common.couldNotReachBackend'))
        setPhase('error')
      })
  }, [t])

  async function handleLanguageChange(event: ChangeEvent<HTMLSelectElement>) {
    const next = event.target.value
    if (!isSupportedLanguage(next)) return
    setSaving(true)
    setSaved(false)
    setError(null)
    try {
      await setLanguage(next)
      setSaved(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.couldNotReachBackend'))
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
      setError(err instanceof ApiError ? err.message : t('common.couldNotReachBackend'))
    } finally {
      setSaving(false)
    }
  }

  if (phase === 'loading') {
    return (
      <div className="settings-view">
        <p>{t('common.loading')}</p>
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
      <h2>{t('settings.title')}</h2>

      <label htmlFor="language">{t('settings.language')}</label>
      <p className="field-hint">{t('settings.languageHint')}</p>
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
        {t('settings.gitAutoCommit')}
      </label>
      <p className="field-hint">
        {gitAvailable
          ? t('settings.gitAutoCommitHintAvailable')
          : t('settings.gitAutoCommitHintUnavailable')}
      </p>

      {saving && <p className="field-hint">{t('settings.saving')}</p>}
      {saved && !saving && <div className="message success">{t('settings.saved')}</div>}
      {error && <div className="message error">{error}</div>}

      <h3>{t('settings.aiProvider')}</h3>
      <AIProviderSettings />
    </div>
  )
}
