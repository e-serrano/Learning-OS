import { type ReactNode, createContext, useContext, useEffect, useState } from 'react'
import { getSettings, updateLanguage as apiUpdateLanguage } from '../api/settings'
import { type Language, translations } from './translations'

export type { Language }

interface LanguageContextValue {
  language: Language
  /** Updates local state immediately (optimistic), then persists via
   * `PATCH /settings/language` -- returns that request's own promise so
   * a caller that cares about success/failure (`SettingsView`'s save
   * feedback) can await/catch it; a caller that doesn't (the nav flag
   * toggle) can just call it and ignore the promise. */
  setLanguage: (language: Language) => Promise<void>
  t: (key: string) => string
}

const LanguageContext = createContext<LanguageContextValue | null>(null)

function isSupportedLanguage(value: string): value is Language {
  return value === 'en' || value === 'es'
}

/** App-wide language state (docs/TASKS.md T147, user request: the app's
 * own UI, not just AI output, in either English or Spanish -- Spanish by
 * default, matching the backend's own default (docs/TASKS.md T147,
 * `AppConfig.language`)).
 *
 * Starts as `'en'` synchronously, on purpose: `GET /settings` resolves
 * async, and every existing component test renders and asserts text
 * immediately without mocking that endpoint -- defaulting to `'es'`
 * before the fetch resolves would break every one of them for a reason
 * unrelated to what they actually test. A real user's browser sees the
 * correct language moments later once the fetch lands (`'es'` for a
 * fresh install, since that's the backend's own new default); a test
 * that wants to assert Spanish rendering mocks `GET /settings` itself,
 * the same way `SettingsView.test.tsx`/`AIProviderSettings.test.tsx`
 * already do for their own concerns.
 *
 * Persists via the same `PATCH /settings/language` endpoint
 * `SettingsView`'s own language `<select>` already uses (docs/TASKS.md
 * T140) -- this and that stay in sync because they both read from and
 * write to the one stored `AppConfig.language`, not two separate values. */
export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>('en')

  useEffect(() => {
    let cancelled = false
    getSettings()
      .then((settings) => {
        if (cancelled) return
        if (isSupportedLanguage(settings.language)) setLanguageState(settings.language)
      })
      .catch(() => {
        // Best-effort: language preference is a nice-to-have, never worth
        // blocking or erroring the whole app over a failed fetch.
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function setLanguage(next: Language): Promise<void> {
    setLanguageState(next) // optimistic -- the UI reflects the choice immediately
    await apiUpdateLanguage(next)
  }

  function t(key: string): string {
    return translations[key]?.[language] ?? key
  }

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useTranslation(): LanguageContextValue {
  const context = useContext(LanguageContext)
  if (!context) {
    throw new Error('useTranslation must be used within a LanguageProvider')
  }
  return context
}
