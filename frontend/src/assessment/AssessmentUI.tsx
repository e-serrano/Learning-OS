import { type FormEvent, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  type Assessment,
  type AssessmentAnswerResult,
  answerAssessment,
  completeAssessment,
  getAssessment,
} from '../api/assessments'
import { ApiError } from '../api/client'
import './assessment.css'

const DEFAULT_CONFIDENCE = 70

type Phase = 'loading' | 'error' | 'answering' | 'result' | 'complete'

/** Assessment UI (docs/TASKS.md T117, dep T105): transfer/final
 * assessment. Unlike the Session UI (T115), there is no activity chain
 * -- a transfer assessment (T089/T105) is one exercise per creation,
 * graded atomically by `AssessmentCompletionService` (T090), so after
 * `/answer` the only next step is `/complete`, never another exercise.
 * Started from the Knowledge Explorer (T114): assessments are
 * inherently single-concept (`generate_transfer_scenario` needs a
 * `concept_id`, T089), and that's the only page that already lists
 * concepts individually to pick one from. */
export function AssessmentUI() {
  const { assessmentId } = useParams<{ assessmentId: string }>()
  const [assessment, setAssessment] = useState<Assessment | null>(null)
  const [phase, setPhase] = useState<Phase>('loading')
  const [error, setError] = useState<string | null>(null)
  const [answer, setAnswer] = useState('')
  const [confidence, setConfidence] = useState(DEFAULT_CONFIDENCE)
  const [showHints, setShowHints] = useState(false)
  const [result, setResult] = useState<AssessmentAnswerResult | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!assessmentId) return
    getAssessment(assessmentId)
      .then((a) => {
        setAssessment(a)
        setPhase('answering')
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
        setPhase('error')
      })
  }, [assessmentId])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!assessmentId) return
    setBusy(true)
    setError(null)
    try {
      const res = await answerAssessment(assessmentId, answer, confidence)
      setResult(res)
      setPhase('result')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    } finally {
      setBusy(false)
    }
  }

  async function handleComplete() {
    if (!assessmentId) return
    setBusy(true)
    setError(null)
    try {
      await completeAssessment(assessmentId)
      setPhase('complete')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    } finally {
      setBusy(false)
    }
  }

  if (phase === 'loading') {
    return (
      <div className="assessment-ui">
        <p>Loading…</p>
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div className="assessment-ui">
        <div className="message error">{error}</div>
      </div>
    )
  }

  if (phase === 'complete') {
    return (
      <div className="assessment-ui">
        <h2>Assessment complete</h2>
        {assessment && <BackLink goalId={assessment.goal_id} />}
      </div>
    )
  }

  if (!assessment) {
    return (
      <div className="assessment-ui">
        <p>Loading…</p>
      </div>
    )
  }

  return (
    <div className="assessment-ui">
      <BackLink goalId={assessment.goal_id} />
      {error && <div className="message error">{error}</div>}

      {phase === 'answering' && (
        <>
          <p className="concept-label">Transfer assessment: {assessment.concept_id}</p>
          <p className="prompt">{assessment.exercise.prompt}</p>

          {assessment.exercise.success_criteria.length > 0 && (
            <ul className="success-criteria">
              {assessment.exercise.success_criteria.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          )}

          {assessment.exercise.hints.length > 0 && (
            <div className="hints">
              <button type="button" className="secondary" onClick={() => setShowHints((v) => !v)}>
                {showHints ? 'Hide hints' : 'Show hints'}
              </button>
              {showHints && (
                <ul>
                  {assessment.exercise.hints.map((h) => (
                    <li key={h}>{h}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <label htmlFor="answer">Your answer</label>
            <textarea
              id="answer"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              rows={6}
              required
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
            <button type="submit" disabled={busy || answer.trim().length === 0}>
              {busy ? 'Submitting…' : 'Submit answer'}
            </button>
          </form>
        </>
      )}

      {phase === 'result' && result && (
        <div className="result">
          <div className="demonstrated-badges">
            <span className={result.transfer_demonstrated ? 'badge yes' : 'badge no'}>
              Transfer {result.transfer_demonstrated ? 'demonstrated' : 'not demonstrated'}
            </span>
            <span className={result.independence_demonstrated ? 'badge yes' : 'badge no'}>
              Independence {result.independence_demonstrated ? 'demonstrated' : 'not demonstrated'}
            </span>
          </div>
          <div className="evaluation-scores">
            <Score label="Correctness" value={result.evaluation.correctness} />
            <Score label="Reasoning" value={result.evaluation.reasoning} />
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
          <button type="button" onClick={handleComplete} disabled={busy}>
            {busy ? 'Finishing…' : 'Complete assessment'}
          </button>
        </div>
      )}
    </div>
  )
}

function BackLink({ goalId }: { goalId: string }) {
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
