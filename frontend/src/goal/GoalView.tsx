import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  type Goal,
  type GoalProgress,
  completeGoal,
  getGoal,
  getGoalProgress,
  pauseGoal,
} from '../api/goals'
import { createSession } from '../api/sessions'
import { MasteryBar } from '../shared/MasteryBar'
import './goal.css'

const DEFAULT_SESSION_DURATION_MINUTES = 30

/** Goal view (docs/TASKS.md T112, dep T096+T107): mastery, weak-concept
 * and due-review counts, and links out to the roadmap (T113) and
 * knowledge explorer (T114) -- those own the full weak-concept list and
 * dependency graph respectively, so this page only shows the at-a-glance
 * numbers `GET /goals/{id}/progress` already gives it, same summary/
 * detail split the Dashboard (T111) uses for its goal cards.
 *
 * Pause/Complete are the only lifecycle actions `GoalApplicationService`
 * exposes (T096) -- there is no `draft -> active` action anywhere yet
 * (T096's own note: activation is a side effect of generating a roadmap,
 * T101), so this page doesn't invent one. */
export function GoalView() {
  const { goalId } = useParams<{ goalId: string }>()
  const navigate = useNavigate()
  const [goal, setGoal] = useState<Goal | null>(null)
  const [progress, setProgress] = useState<GoalProgress | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    if (!goalId) return
    try {
      const [goalResult, progressResult] = await Promise.all([
        getGoal(goalId),
        getGoalProgress(goalId),
      ])
      setGoal(goalResult)
      setProgress(progressResult)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    }
  }, [goalId])

  useEffect(() => {
    load()
  }, [load])

  async function handlePause() {
    if (!goalId) return
    setBusy(true)
    try {
      setGoal(await pauseGoal(goalId))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    } finally {
      setBusy(false)
    }
  }

  async function handleComplete() {
    if (!goalId) return
    setBusy(true)
    try {
      setGoal(await completeGoal(goalId))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    } finally {
      setBusy(false)
    }
  }

  async function handleStartSession() {
    if (!goalId) return
    setBusy(true)
    try {
      const session = await createSession(goalId, 'guided', DEFAULT_SESSION_DURATION_MINUTES)
      navigate(`/sessions/${session.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
      setBusy(false)
    }
  }

  if (error) {
    return (
      <div className="goal-view">
        <div className="message error">{error}</div>
      </div>
    )
  }
  if (!goal || !progress) {
    return (
      <div className="goal-view">
        <p>Loading…</p>
      </div>
    )
  }

  return (
    <div className="goal-view">
      <Link to="/" className="back-link">
        ← Dashboard
      </Link>
      <div className="goal-view-header">
        <h2>{goal.title}</h2>
        <span className={`status-tag status-${goal.status}`}>{goal.status}</span>
      </div>
      {goal.description && <p className="subtitle">{goal.description}</p>}

      <MasteryBar mastery={progress.mastery} />

      <div className="goal-stats-grid">
        <div className="stat">
          <strong>{progress.concepts_total}</strong>
          <span>concepts</span>
        </div>
        <div className="stat">
          <strong>{progress.mastered}</strong>
          <span>mastered</span>
        </div>
        <div className="stat">
          <strong>{progress.weak}</strong>
          <span>weak</span>
        </div>
        <div className="stat">
          <strong>{progress.due_reviews}</strong>
          <span>reviews due</span>
        </div>
        <div className="stat">
          <strong>{progress.recent_sessions}</strong>
          <span>recent sessions</span>
        </div>
      </div>

      <div className="goal-view-links">
        <Link to={`/goals/${goal.id}/roadmap`}>Roadmap</Link>
        <Link to={`/goals/${goal.id}/knowledge`}>Knowledge explorer</Link>
      </div>

      {(goal.status === 'draft' || goal.status === 'active') && (
        <button type="button" onClick={handleStartSession} disabled={busy}>
          Start session
        </button>
      )}

      {goal.status === 'active' && (
        <div className="goal-view-actions">
          <button type="button" className="secondary" onClick={handlePause} disabled={busy}>
            Pause goal
          </button>
          <button type="button" onClick={handleComplete} disabled={busy}>
            Mark complete
          </button>
        </div>
      )}
    </div>
  )
}
