import { type FormEvent, useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  type Goal,
  type GoalProgress,
  type TargetLevel,
  createGoal,
  getGoalProgress,
  listGoals,
} from '../api/goals'
import { MasteryBar } from '../shared/MasteryBar'
import './dashboard.css'

interface GoalWithProgress {
  goal: Goal
  progress: GoalProgress
}

const TARGET_LEVELS: TargetLevel[] = ['beginner', 'intermediate', 'advanced', 'professional']

/** Dashboard (docs/TASKS.md T111, dep T107): overall status across every
 * goal plus a next action. No dedicated "create goal" task exists
 * anywhere in Phase 11 (docs/TASKS.md), so the empty-state form here is
 * also the only way to create a goal from the UI -- otherwise a fresh
 * install with zero goals would be a dead end with no path forward. */
export function Dashboard() {
  const [goals, setGoals] = useState<GoalWithProgress[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const { goals: list } = await listGoals()
      const withProgress = await Promise.all(
        list.map(async (goal) => ({ goal, progress: await getGoalProgress(goal.id) })),
      )
      setGoals(withProgress)
      setLoadError(null)
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  if (loadError) {
    return (
      <div className="dashboard">
        <div className="message error">{loadError}</div>
      </div>
    )
  }
  if (!goals) {
    return (
      <div className="dashboard">
        <p>Loading…</p>
      </div>
    )
  }

  const dueReviews = goals.reduce((sum, g) => sum + g.progress.due_reviews, 0)

  return (
    <div className="dashboard">
      <h2>Dashboard</h2>
      <NextAction dueReviews={dueReviews} />
      {goals.length === 0 ? (
        <CreateGoalForm onCreated={load} />
      ) : (
        <>
          <div className="goal-cards">
            {goals.map(({ goal, progress }) => (
              <GoalCard key={goal.id} goal={goal} progress={progress} />
            ))}
          </div>
          <CreateGoalForm onCreated={load} collapsedByDefault />
        </>
      )}
    </div>
  )
}

function NextAction({ dueReviews }: { dueReviews: number }) {
  if (dueReviews === 0) {
    return <div className="message success">You're all caught up -- no reviews due.</div>
  }
  return (
    <div className="next-action">
      <p>
        You have {dueReviews} review{dueReviews === 1 ? '' : 's'} due.
      </p>
      <Link to="/reviews">Review now</Link>
    </div>
  )
}

function GoalCard({ goal, progress }: GoalWithProgress) {
  return (
    <Link to={`/goals/${goal.id}`} className="goal-card">
      <div className="goal-card-header">
        <strong>{goal.title}</strong>
        <span className={`status-tag status-${goal.status}`}>{goal.status}</span>
      </div>
      <MasteryBar mastery={progress.mastery} />
      <div className="goal-card-stats">
        <span>{progress.concepts_total} concepts</span>
        <span>{progress.mastered} mastered</span>
        <span>{progress.weak} weak</span>
        {progress.due_reviews > 0 && <span>{progress.due_reviews} due</span>}
      </div>
    </Link>
  )
}

function CreateGoalForm({
  onCreated,
  collapsedByDefault = false,
}: {
  onCreated: () => void
  collapsedByDefault?: boolean
}) {
  const [expanded, setExpanded] = useState(!collapsedByDefault)
  const [title, setTitle] = useState('')
  const [targetLevel, setTargetLevel] = useState<TargetLevel>('intermediate')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!expanded) {
    return (
      <button type="button" className="secondary" onClick={() => setExpanded(true)}>
        + New goal
      </button>
    )
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await createGoal({ title: title.trim(), target_level: targetLevel })
      setTitle('')
      setExpanded(collapsedByDefault ? false : true)
      onCreated()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="create-goal-form" onSubmit={handleSubmit}>
      <h3>New goal</h3>
      <label htmlFor="goal-title">What do you want to learn?</label>
      <input
        id="goal-title"
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="e.g. Advanced SQL for analytics"
        required
      />
      <label htmlFor="goal-level">Target level</label>
      <select
        id="goal-level"
        value={targetLevel}
        onChange={(e) => setTargetLevel(e.target.value as TargetLevel)}
      >
        {TARGET_LEVELS.map((level) => (
          <option key={level} value={level}>
            {level}
          </option>
        ))}
      </select>
      <button type="submit" disabled={busy || title.trim().length === 0}>
        {busy ? 'Creating…' : 'Create goal'}
      </button>
      {error && <div className="message error">{error}</div>}
    </form>
  )
}
