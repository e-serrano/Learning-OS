import { type FormEvent, useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { type Concept, listKnowledge } from '../api/knowledge'
import { type TutorTurn, askTutor } from '../api/sessions'
import './tutor-chat.css'

interface TutorChatProps {
  sessionId: string
  goalId: string
  onEnd: () => void
}

/** Chat UI for the Socratic/interview tutor turn (docs/TASKS.md T142,
 * dep T132/T141). `POST /sessions/{id}/tutor` is stateless per call --
 * the caller resends the whole conversation each time -- so this
 * component owns the transcript entirely client-side; nothing here is
 * persisted server-side beyond the per-call AI run log.
 *
 * The tutor speaks first: an empty-message/empty-history call on mount
 * seeds the opening question, matching what `TutorService.ask` already
 * supports (its own test covers a blank opening message) rather than
 * making the learner type into silence. The concept picker locks once
 * the conversation has a first exchange -- switching concepts mid-chat
 * would mix context the tutor was never given. */
export function TutorChat({ sessionId, goalId, onEnd }: TutorChatProps) {
  const [concepts, setConcepts] = useState<Concept[]>([])
  const [conceptId, setConceptId] = useState('')
  const [loadingConcepts, setLoadingConcepts] = useState(true)
  const [history, setHistory] = useState<TutorTurn[]>([])
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    listKnowledge(goalId)
      .then(({ concepts: list }) => {
        if (cancelled) return
        setConcepts(list)
        if (list.length > 0) setConceptId(list[0].id)
        setLoadingConcepts(false)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
        setLoadingConcepts(false)
      })
    return () => {
      cancelled = true
    }
  }, [goalId])

  useEffect(() => {
    if (!conceptId) return
    let cancelled = false
    setBusy(true)
    askTutor(sessionId, conceptId, [], '')
      .then((response) => {
        if (cancelled) return
        setHistory([{ speaker: 'tutor', content: response.content }])
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
      })
      .finally(() => {
        if (!cancelled) setBusy(false)
      })
    return () => {
      cancelled = true
    }
    // conceptId only ever changes once, before the first exchange (the
    // picker locks after that), so this fires the opening turn exactly
    // once per real chat.
  }, [sessionId, conceptId])

  async function handleSend(event: FormEvent) {
    event.preventDefault()
    const trimmed = message.trim()
    if (trimmed.length === 0 || !conceptId) return
    setBusy(true)
    setError(null)
    const learnerTurn: TutorTurn = { speaker: 'learner', content: trimmed }
    try {
      const response = await askTutor(sessionId, conceptId, history, trimmed)
      setHistory((prev) => [...prev, learnerTurn, { speaker: 'tutor', content: response.content }])
      setMessage('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    } finally {
      setBusy(false)
    }
  }

  if (loadingConcepts) {
    return (
      <div className="tutor-chat">
        <p>Loading…</p>
      </div>
    )
  }

  if (concepts.length === 0) {
    return (
      <div className="tutor-chat">
        <p>This goal has no concepts yet -- generate a roadmap first.</p>
        <button type="button" onClick={onEnd}>
          End session
        </button>
      </div>
    )
  }

  const started = history.length > 0

  return (
    <div className="tutor-chat">
      <label htmlFor="tutor-concept">Concept</label>
      <select
        id="tutor-concept"
        value={conceptId}
        onChange={(e) => setConceptId(e.target.value)}
        disabled={started}
      >
        {concepts.map((c) => (
          <option key={c.id} value={c.id}>
            {c.title}
          </option>
        ))}
      </select>

      <div className="tutor-chat-transcript">
        {history.map((turn, i) => (
          <div key={i} className={`tutor-chat-turn ${turn.speaker}`}>
            <span className="speaker-label">{turn.speaker === 'tutor' ? 'Tutor' : 'You'}</span>
            <p>{turn.content}</p>
          </div>
        ))}
        {busy && history.length === 0 && <p className="tutor-chat-hint">Thinking…</p>}
      </div>

      {error && <div className="message error">{error}</div>}

      <form onSubmit={handleSend}>
        <label htmlFor="tutor-message" className="sr-only">
          Message
        </label>
        <textarea
          id="tutor-message"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={3}
          placeholder="Type your response…"
          disabled={busy}
        />
        <div className="tutor-chat-actions">
          <button type="submit" disabled={busy || message.trim().length === 0}>
            {busy ? 'Sending…' : 'Send'}
          </button>
          <button type="button" className="secondary" onClick={onEnd} disabled={busy}>
            End session
          </button>
        </div>
      </form>
    </div>
  )
}
