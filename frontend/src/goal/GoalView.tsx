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
import { listKnowledge } from '../api/knowledge'
import { type Project, createProject, listProjects } from '../api/projects'
import { type SessionMode, createSession } from '../api/sessions'
import { useTranslation } from '../i18n/LanguageContext'
import { MasteryBar } from '../shared/MasteryBar'
import './goal.css'

const DEFAULT_SESSION_DURATION_MINUTES = 30

/** Only the modes reachable from "Start session" -- practice/review/
 * assessment/project/teach_back each already have their own dedicated
 * creation flow elsewhere (AssessmentUI, ProjectView, teach-back
 * service, T133), so this picker doesn't try to cover them too. */
function sessionModeOptions(t: (key: string) => string): { value: SessionMode; label: string }[] {
  return [
    { value: 'guided', label: t('goalView.modeGuided') },
    { value: 'socratic', label: t('goalView.modeSocratic') },
    { value: 'interview', label: t('goalView.modeInterview') },
  ]
}

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
  const { t } = useTranslation()
  const { goalId } = useParams<{ goalId: string }>()
  const navigate = useNavigate()
  const [goal, setGoal] = useState<Goal | null>(null)
  const [progress, setProgress] = useState<GoalProgress | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [sessionMode, setSessionMode] = useState<SessionMode>('guided')

  const load = useCallback(async () => {
    if (!goalId) return
    try {
      const [goalResult, progressResult, projectsResult] = await Promise.all([
        getGoal(goalId),
        getGoalProgress(goalId),
        listProjects(goalId),
      ])
      setGoal(goalResult)
      setProgress(progressResult)
      setProjects(projectsResult.projects)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.couldNotReachBackend'))
    }
  }, [goalId, t])

  useEffect(() => {
    load()
  }, [load])

  async function handlePause() {
    if (!goalId) return
    setBusy(true)
    try {
      setGoal(await pauseGoal(goalId))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.couldNotReachBackend'))
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
      setError(err instanceof ApiError ? err.message : t('common.couldNotReachBackend'))
    } finally {
      setBusy(false)
    }
  }

  async function handleStartSession() {
    if (!goalId) return
    setBusy(true)
    try {
      const session = await createSession(goalId, sessionMode, DEFAULT_SESSION_DURATION_MINUTES)
      navigate(`/sessions/${session.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.couldNotReachBackend'))
      setBusy(false)
    }
  }

  async function handleStartProject() {
    if (!goalId) return
    setBusy(true)
    setError(null)
    try {
      const { concepts } = await listKnowledge(goalId)
      if (concepts.length === 0) {
        setError(t('goalView.noConceptsGenerateRoadmap'))
        setBusy(false)
        return
      }
      const created = await createProject(
        goalId,
        concepts.map((c) => c.id),
      )
      navigate(`/projects/${created.project.id}`, { state: { tasks: created.tasks } })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.couldNotReachBackend'))
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
        <p>{t('common.loading')}</p>
      </div>
    )
  }

  return (
    <div className="goal-view">
      <Link to="/" className="back-link">
        {t('common.backToDashboard')}
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
          <span>{t('dashboard.concepts')}</span>
        </div>
        <div className="stat">
          <strong>{progress.mastered}</strong>
          <span>{t('dashboard.mastered')}</span>
        </div>
        <div className="stat">
          <strong>{progress.weak}</strong>
          <span>{t('dashboard.weak')}</span>
        </div>
        <div className="stat">
          <strong>{progress.due_reviews}</strong>
          <span>{t('goalView.reviewsDue')}</span>
        </div>
        <div className="stat">
          <strong>{progress.recent_sessions}</strong>
          <span>{t('goalView.recentSessions')}</span>
        </div>
      </div>

      <div className="goal-view-links">
        <Link to={`/goals/${goal.id}/roadmap`}>{t('goalView.roadmap')}</Link>
        <Link to={`/goals/${goal.id}/knowledge`}>{t('goalView.knowledgeExplorer')}</Link>
      </div>

      {(goal.status === 'draft' || goal.status === 'active') && (
        <div className="goal-view-actions">
          <label htmlFor="session-mode" className="sr-only">
            {t('goalView.sessionMode')}
          </label>
          <select
            id="session-mode"
            value={sessionMode}
            onChange={(e) => setSessionMode(e.target.value as SessionMode)}
            disabled={busy}
          >
            {sessionModeOptions(t).map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <button type="button" onClick={handleStartSession} disabled={busy}>
            {t('goalView.startSession')}
          </button>
          <button type="button" className="secondary" onClick={handleStartProject} disabled={busy}>
            {t('goalView.startProject')}
          </button>
        </div>
      )}

      {projects.length > 0 && (
        <div className="goal-projects">
          <h3>{t('goalView.projects')}</h3>
          <ul>
            {projects.map((p) => (
              <li key={p.id}>
                <Link to={`/projects/${p.id}`}>{p.title}</Link>{' '}
                <span className={`status-tag status-${p.status}`}>{p.status}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {goal.status === 'active' && (
        <div className="goal-view-actions">
          <button type="button" className="secondary" onClick={handlePause} disabled={busy}>
            {t('goalView.pauseGoal')}
          </button>
          <button type="button" onClick={handleComplete} disabled={busy}>
            {t('goalView.markComplete')}
          </button>
        </div>
      )}
    </div>
  )
}
