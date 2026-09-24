import { type ChangeEvent, useEffect, useState } from 'react'
import { ApiError, getSettings, updateLanguage } from '../api/settings'
import './settings.css'

type Phase = 'loading' | 'error' | 'ready'

/** Settings page (user request, 2026-09-24): a single app-wide language
 * preference that steers both the UI's own copy and every AI-generated
 * response, including Obsidian note content the curator writes
 * (`AIOrchestrator.generate` injects `constraints.language` into every
 * AI call from the configured value -- see docs/AI_CONTRACTS.md #2). */
export function SettingsView() {
  const [phase, setPhase] = useState<Phase>('loading')
  const [error, setError] = useState<string | null>(null)
  const [language, setLanguage] = useState('en')
  const [languages, setLanguages] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getSettings()
      .then((settings) => {
        setLanguage(settings.language)
        setLanguages(settings.supported_languages)
        setPhase('ready')
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
        setPhase('error')
      })
  }, [])

  async function handleChange(event: ChangeEvent<HTMLSelectElement>) {
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
      <select id="language" value={language} onChange={handleChange} disabled={saving}>
        {Object.entries(languages).map(([code, name]) => (
          <option key={code} value={code}>
            {name}
          </option>
        ))}
      </select>

      {saving && <p className="field-hint">Saving…</p>}
      {saved && !saving && <div className="message success">Saved.</div>}
      {error && <div className="message error">{error}</div>}
    </div>
  )
}
