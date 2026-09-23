import { useEffect, useRef, useState } from 'react'
import './voice.css'

interface SpeechRecognitionAlternative {
  transcript: string
}

interface SpeechRecognitionResult {
  readonly length: number
  [index: number]: SpeechRecognitionAlternative
}

interface SpeechRecognitionResultList {
  readonly length: number
  [index: number]: SpeechRecognitionResult
}

interface SpeechRecognitionEvent {
  results: SpeechRecognitionResultList
}

interface SpeechRecognitionLike {
  lang: string
  interimResults: boolean
  continuous: boolean
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onerror: (() => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
}

type SpeechRecognitionCtor = new () => SpeechRecognitionLike

function getSpeechRecognitionCtor(): SpeechRecognitionCtor | null {
  if (typeof window === 'undefined') return null
  const w = window as unknown as {
    SpeechRecognition?: SpeechRecognitionCtor
    webkitSpeechRecognition?: SpeechRecognitionCtor
  }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

function isVoiceInputSupported(): boolean {
  return getSpeechRecognitionCtor() !== null
}

function transcriptOf(event: SpeechRecognitionEvent): string {
  let text = ''
  for (let i = 0; i < event.results.length; i++) {
    text += event.results[i][0].transcript
  }
  return text
}

/** Voice input via the browser's (non-standard, Chrome/Edge/Safari-only,
 * no Firefox support) SpeechRecognition API -- docs/TASKS.md T134.
 * Renders nothing when the browser doesn't expose it (jsdom included,
 * so this is invisible in every other component's tests by default) --
 * same graceful-degradation approach as every other capability-gated UI
 * bit in this app (e.g. KnowledgeExplorer's `MockProvider` limits).
 * One utterance per click: `continuous`/`interimResults` are both off,
 * so `onresult` fires once with the final transcript, then `onend`
 * fires and listening stops on its own -- clicking again starts a new
 * utterance rather than accumulating one long open microphone. */
export function VoiceInputButton({
  onTranscript,
  disabled = false,
}: {
  onTranscript: (text: string) => void
  disabled?: boolean
}) {
  const [listening, setListening] = useState(false)
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop()
    }
  }, [])

  if (!isVoiceInputSupported()) return null

  function toggle() {
    if (listening) {
      recognitionRef.current?.stop()
      return
    }
    const Ctor = getSpeechRecognitionCtor()
    if (!Ctor) return
    const recognition = new Ctor()
    recognition.lang = 'en-US'
    recognition.interimResults = false
    recognition.continuous = false
    recognition.onresult = (event) => onTranscript(transcriptOf(event))
    recognition.onerror = () => setListening(false)
    recognition.onend = () => setListening(false)
    recognitionRef.current = recognition
    recognition.start()
    setListening(true)
  }

  return (
    <button
      type="button"
      className="voice-button"
      onClick={toggle}
      disabled={disabled}
      aria-pressed={listening}
    >
      {listening ? 'Stop listening' : 'Speak answer'}
    </button>
  )
}
