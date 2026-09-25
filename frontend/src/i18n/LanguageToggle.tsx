import { useTranslation } from './LanguageContext'
import './language-toggle.css'

/** Nav-bar language toggle (docs/TASKS.md T147, user request): shows the
 * flag of the language a click would switch TO, not the one currently
 * active -- click the Spanish flag to read the app in Spanish, at which
 * point the button itself becomes the British flag (switch back to
 * English), matching exactly what the user asked for. Emoji flags, not
 * an SVG/image asset -- render natively everywhere without hosting or
 * licensing anything, the smallest implementation that actually works
 * (docs/AGENTS.md #25). */
export function LanguageToggle() {
  const { language, setLanguage } = useTranslation()
  const nextLanguage = language === 'en' ? 'es' : 'en'
  const label = language === 'en' ? 'Switch to Spanish' : 'Cambiar a inglés'

  return (
    <button
      type="button"
      className="language-toggle"
      onClick={() => {
        // Fire-and-forget: the UI already flipped optimistically: a
        // failed persist just means the choice doesn't survive a
        // refresh, not worth its own error UI on a nav-bar toggle.
        setLanguage(nextLanguage).catch(() => {})
      }}
      aria-label={label}
      title={label}
    >
      <span aria-hidden="true">{nextLanguage === 'es' ? '🇪🇸' : '🇬🇧'}</span>
    </button>
  )
}
