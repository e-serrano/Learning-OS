import { useTranslation } from './LanguageContext'
import './language-toggle.css'

/** Inline SVG flags, not emoji (docs/TASKS.md T151, dogfood ISSUE-001):
 * regional-indicator flag emoji (🇪🇸/🇬🇧) render as plain two-letter text
 * ("ES"/"GB") on a lot of real Windows installs -- Segoe UI Emoji only
 * gained joined flag glyphs in recent Windows 11 builds, so the toggle
 * silently stopped looking like a flag at all for a large share of this
 * app's actual target platform. A tiny self-contained SVG per flag
 * renders identically everywhere, no font/OS dependency, no external
 * asset to host (docs/AGENTS.md #25 still applies -- this is the
 * smallest fix that actually works cross-platform). */
function SpainFlag() {
  return (
    <svg viewBox="0 0 60 30" width="20" height="14" aria-hidden="true">
      <rect width="60" height="30" fill="#AA151B" />
      <rect y="7.5" width="60" height="15" fill="#F1BF00" />
    </svg>
  )
}

function UkFlag() {
  return (
    <svg viewBox="0 0 60 30" width="20" height="14" aria-hidden="true">
      <rect width="60" height="30" fill="#012169" />
      <path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" strokeWidth="6" />
      <path d="M0,0 L60,30 M60,0 L0,30" stroke="#C8102E" strokeWidth="2" />
      <path d="M30,0 V30 M0,15 H60" stroke="#fff" strokeWidth="10" />
      <path d="M30,0 V30 M0,15 H60" stroke="#C8102E" strokeWidth="6" />
    </svg>
  )
}

/** Nav-bar language toggle (docs/TASKS.md T147, user request): shows the
 * flag of the language a click would switch TO, not the one currently
 * active -- click the Spanish flag to read the app in Spanish, at which
 * point the button itself becomes the British flag (switch back to
 * English), matching exactly what the user asked for. */
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
      {nextLanguage === 'es' ? <SpainFlag /> : <UkFlag />}
    </button>
  )
}
