import { type FormEvent, useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import {
  type Review,
  type ReviewCompletionResult,
  completeReview,
  listTodaysReviews,
} from '../api/reviews'
import { MasteryBar } from '../shared/MasteryBar'
import './reviews.css'

const DEFAULT_CONFIDENCE = 70
const MAX_MASTERY = 5

type Phase = 'loading' | 'error' | 'empty' | 'reviewing' | 'result'

/** Reviews UI (docs/TASKS.md T116, dep T104): complete today's due
 * reviews one at a time. Completion is self-reported (T087's own
 * docstring: a Review has no linked Exercise, so correctness comes
 * straight from the user's own confidence, not an AI grade) -- so this
 * is a simpler loop than the Session UI (T115): no server round-trip
 * for "what's next", the full queue is already the `GET /reviews/today`
 * list, advanced locally after each `/complete` call. */
export function ReviewsUI() {
  const [reviews, setReviews] = useState<Review[]>([])
  const [index, setIndex] = useState(0)
  const [phase, setPhase] = useState<Phase>('loading')
  const [error, setError] = useState<string | null>(null)
  const [answer, setAnswer] = useState('')
  const [confidence, setConfidence] = useState(DEFAULT_CONFIDENCE)
  const [result, setResult] = useState<ReviewCompletionResult | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    listTodaysReviews()
      .then(({ reviews: list }) => {
        setReviews(list)
        setPhase(list.length > 0 ? 'reviewing' : 'empty')
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
        setPhase('error')
      })
  }, [])

  const current = reviews[index]

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!current) return
    setBusy(true)
    setError(null)
    try {
      const res = await completeReview(current.id, answer, confidence)
      setResult(res)
      setPhase('result')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    } finally {
      setBusy(false)
    }
  }

  function handleContinue() {
    const nextIndex = index + 1
    setAnswer('')
    setConfidence(DEFAULT_CONFIDENCE)
    setResult(null)
    if (nextIndex < reviews.length) {
      setIndex(nextIndex)
      setPhase('reviewing')
    } else {
      setPhase('empty')
    }
  }

  if (phase === 'loading') {
    return (
      <div className="reviews-ui">
        <p>Loading…</p>
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div className="reviews-ui">
        <div className="message error">{error}</div>
      </div>
    )
  }

  if (phase === 'empty') {
    return (
      <div className="reviews-ui">
        <h2>Reviews</h2>
        <div className="message success">You're all caught up -- no reviews due.</div>
      </div>
    )
  }

  return (
    <div className="reviews-ui">
      <h2>Reviews</h2>
      <p className="progress-label">
        {index + 1} of {reviews.length}
      </p>
      {error && <div className="message error">{error}</div>}

      {phase === 'reviewing' && current && (
        <>
          <p className="concept-label">{current.concept_id}</p>
          <form onSubmit={handleSubmit}>
            <label htmlFor="answer">What do you recall?</label>
            <textarea
              id="answer"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              rows={5}
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
              {busy ? 'Submitting…' : 'Submit'}
            </button>
          </form>
        </>
      )}

      {phase === 'result' && result && (
        <div className="review-result">
          <p>
            Next review in {Math.round(result.next_review.interval_days)} day
            {Math.round(result.next_review.interval_days) === 1 ? '' : 's'}.
          </p>
          <MasteryBar mastery={result.concept.mastery / MAX_MASTERY} />
          <div className="review-stats">
            <span>{Math.round(result.concept.retention)}% retention</span>
            <span className="status-tag">{result.concept.status}</span>
          </div>
          <button type="button" onClick={handleContinue}>
            {index + 1 < reviews.length ? 'Next review' : 'Done'}
          </button>
        </div>
      )}
    </div>
  )
}
