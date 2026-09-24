import { type FormEvent, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  type AnswerResult,
  type NextActivity,
  type Session,
  completeSession,
  getNextActivity,
  getSession,
  submitAnswer,
} from '../api/sessions'
import { ReadAloudButton } from '../shared/ReadAloudButton'
import { SqlSandbox } from '../shared/SqlSandbox'
import { VoiceInputButton } from '../shared/VoiceInputButton'
import './session.css'

const DEFAULT_CONFIDENCE = 70

type Phase = 'loading' | 'error' | 'no-candidates' | 'answering' | 'result' | 'complete'

/** Session UI (docs/TASKS.md T115, dep T103): the core learning loop --
 * activity, answer, confidence, hints, feedback, and next. `/next`'s
 * response is shown as the activity to answer; submitting calls
 * `/answer`, whose response already embeds the *next* activity
 * (`AnswerFlowService`, T103) -- so "Continue" never calls `/next`
 * again, it just swaps in `result.next_activity.content` directly. When
 * `next_activity` comes back `null` there are no more candidates for
 * this goal right now, so the only way forward is `/complete`. */
export function SessionUI() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [session, setSession] = useState<Session | null>(null)
  const [phase, setPhase] = useState<Phase>('loading')
  const [error, setError] = useState<string | null>(null)
  const [activity, setActivity] = useState<NextActivity | null>(null)
  const [answer, setAnswer] = useState('')
  const [confidence, setConfidence] = useState(DEFAULT_CONFIDENCE)
  const [showHints, setShowHints] = useState(false)
  const [result, setResult] = useState<AnswerResult | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!sessionId) return
    let cancelled = false

    async function start() {
      try {
        const s = await getSession(sessionId!)
        if (cancelled) return
        setSession(s)
        if (s.status !== 'active') {
          setPhase('complete')
          return
        }
        const next = await getNextActivity(sessionId!)
        if (cancelled) return
        setActivity(next)
        setPhase('answering')
      } catch (err) {
        if (cancelled) return
        if (err instanceof ApiError && err.code === 'SESSION_STATE_ERROR') {
          setPhase('no-candidates')
        } else {
          setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
          setPhase('error')
        }
      }
    }

    start()
    return () => {
      cancelled = true
    }
  }, [sessionId])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!sessionId || !activity) return
    setBusy(true)
    setError(null)
    try {
      const res = await submitAnswer(sessionId, activity.activity_id, answer, confidence)
      setResult(res)
      setPhase('result')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    } finally {
      setBusy(false)
    }
  }

  function handleContinue() {
    if (!result?.next_activity) return
    setActivity(result.next_activity)
    setAnswer('')
    setConfidence(DEFAULT_CONFIDENCE)
    setShowHints(false)
    setResult(null)
    setPhase('answering')
  }

  async function handleFinish() {
    if (!sessionId) return
    setBusy(true)
    setError(null)
    try {
      setSession(await completeSession(sessionId))
      setPhase('complete')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    } finally {
      setBusy(false)
    }
  }

  if (phase === 'loading') {
    return (
      <div className="session-ui">
        <p>Loading…</p>
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div className="session-ui">
        <div className="message error">{error}</div>
      </div>
    )
  }

  if (phase === 'no-candidates') {
    return (
      <div className="session-ui">
        <h2>Nothing to work on yet</h2>
        <p className="subtitle">
          This goal has no activity candidates right now -- generate a roadmap and a diagnostic
          first.
        </p>
        {session && <BackToGoalLink goalId={session.goal_id} />}
      </div>
    )
  }

  if (phase === 'complete') {
    return (
      <div className="session-ui">
        <h2>Session complete</h2>
        {session && <BackToGoalLink goalId={session.goal_id} />}
      </div>
    )
  }

  if (!activity) {
    return (
      <div className="session-ui">
        <p>Loading…</p>
      </div>
    )
  }

  return (
    <div className="session-ui">
      {session && <BackToGoalLink goalId={session.goal_id} />}
      {error && <div className="message error">{error}</div>}

      {phase === 'answering' && (
        <>
          <p className="activity-type">{activity.type}</p>
          <div className="prompt-row">
            <p className="prompt">{activity.content.prompt}</p>
            <ReadAloudButton text={activity.content.prompt} />
          </div>

          {activity.content.success_criteria.length > 0 && (
            <ul className="success-criteria">
              {activity.content.success_criteria.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          )}

          {activity.content.hints.length > 0 && (
            <div className="hints">
              <button type="button" className="secondary" onClick={() => setShowHints((v) => !v)}>
                {showHints ? 'Hide hints' : 'Show hints'}
              </button>
              {showHints && (
                <ul>
                  {activity.content.hints.map((h) => (
                    <li key={h}>{h}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <SqlSandbox />

          <form onSubmit={handleSubmit}>
            <label htmlFor="answer">Your answer</label>
            <textarea
              id="answer"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              rows={6}
              required
            />
            <VoiceInputButton
              disabled={busy}
              onTranscript={(text) =>
                setAnswer((prev) => (prev.trim().length > 0 ? `${prev} ${text}` : text))
              }
            />
            <label htmlFor="confidence">Confidence: {confidence}%</label>
            <input
              id="confidence"
              type="range"
              min={0}
              max={100}
              value={confidence}
              onChange={(e) => setConfidence(Number(e.target.value))}
            />
            <div className="session-actions">
              <button type="submit" disabled={busy || answer.trim().length === 0}>
                {busy ? 'Submitting…' : 'Submit answer'}
              </button>
              <button type="button" className="secondary" onClick={handleFinish} disabled={busy}>
                End session
              </button>
            </div>
          </form>
        </>
      )}

      {phase === 'result' && result && (
        <div className="result">
          <div className="evaluation-scores">
            <Score label="Correctness" value={result.evaluation.correctness} />
            <Score label="Reasoning" value={result.evaluation.reasoning} />
            <Score label="Completeness" value={result.evaluation.completeness} />
            <Score label="Independence" value={result.evaluation.independence} />
            <Score label="Transfer" value={result.evaluation.transfer} />
          </div>
          <p className="feedback">{result.evaluation.feedback}</p>
          {result.evaluation.misconceptions.length > 0 && (
            <ul className="misconceptions">
              {result.evaluation.misconceptions.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          )}
          {result.knowledge_updates.length > 0 && (
            <div className="knowledge-updates">
              {result.knowledge_updates.map((u) => (
                <span key={u.concept_id} className="status-tag">
                  {u.concept_id}: {u.status}
                </span>
              ))}
            </div>
          )}
          <div className="session-actions">
            {result.next_activity ? (
              <button type="button" onClick={handleContinue}>
                Continue
              </button>
            ) : (
              <button type="button" onClick={handleFinish} disabled={busy}>
                {busy ? 'Finishing…' : 'Finish session'}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function BackToGoalLink({ goalId }: { goalId: string }) {
  return (
    <Link to={`/goals/${goalId}`} className="back-link">
      ← Goal
    </Link>
  )
}

function Score({ label, value }: { label: string; value: number }) {
  return (
    <div className="score">
      <strong>{Math.round(value * 100)}%</strong>
      <span>{label}</span>
    </div>
  )
}
