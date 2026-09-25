import { useEffect, useState } from 'react'
import { useTranslation } from '../i18n/LanguageContext'
import './voice.css'

/** Voice output via the standard `SpeechSynthesis` API -- docs/TASKS.md
 * T134. Unlike `VoiceInputButton`'s recognition API, synthesis is
 * broadly supported (including Firefox) and part of TypeScript's DOM
 * lib, so no custom typing is needed here -- only the same
 * feature-detect-and-render-nothing fallback for environments with
 * neither (jsdom included). */
function isVoiceOutputSupported(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window
}

export function ReadAloudButton({ text }: { text: string }) {
  const { language, t } = useTranslation()
  const [speaking, setSpeaking] = useState(false)

  useEffect(() => {
    return () => {
      window.speechSynthesis?.cancel()
    }
  }, [])

  if (!isVoiceOutputSupported()) return null

  function toggle() {
    if (speaking) {
      window.speechSynthesis.cancel()
      setSpeaking(false)
      return
    }
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = language === 'es' ? 'es-ES' : 'en-US'
    utterance.onend = () => setSpeaking(false)
    utterance.onerror = () => setSpeaking(false)
    window.speechSynthesis.speak(utterance)
    setSpeaking(true)
  }

  return (
    <button
      type="button"
      className="voice-button"
      onClick={toggle}
      aria-pressed={speaking}
      disabled={text.trim().length === 0}
    >
      {speaking ? t('voice.stopReading') : t('voice.readAloud')}
    </button>
  )
}
