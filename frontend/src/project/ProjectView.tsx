import { type FormEvent, useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  type Project,
  type ProjectTask,
  type SubmitTaskResult,
  getProject,
  submitTask,
} from '../api/projects'
import './project.css'

interface LocationState {
  tasks?: ProjectTask[]
}

/** Project view (docs/TASKS.md T118, dep T106): project and tasks.
 * `GET /projects/{id}` (T106) deliberately never returns tasks -- there
 * is no persisted `Project -> Session` link to resolve them from (see
 * `project_session_service.py`'s own docstring) -- so the task list
 * this page can show only exists right after creation, passed through
 * `navigate(path, {state: {tasks}})` from `GoalView`'s "Start project".
 * Reloading this page, or opening it from a bookmarked URL, loses the
 * task list -- a real, documented limitation of T106's API, not
 * something this page can work around without a backend change. */
export function ProjectView() {
  const { projectId } = useParams<{ projectId: string }>()
  const location = useLocation()
  const [project, setProject] = useState<Project | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tasks] = useState<ProjectTask[]>((location.state as LocationState | null)?.tasks ?? [])
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null)
  const [deliverable, setDeliverable] = useState('')
  const [busy, setBusy] = useState(false)
  const [resultsByTask, setResultsByTask] = useState<Record<string, SubmitTaskResult>>({})

  useEffect(() => {
    if (!projectId) return
    getProject(projectId)
      .then(setProject)
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
      })
  }, [projectId])

  function toggleTask(taskId: string) {
    setExpandedTaskId((current) => (current === taskId ? null : taskId))
    setDeliverable('')
  }

  async function handleSubmit(event: FormEvent, taskId: string) {
    event.preventDefault()
    if (!projectId) return
    setBusy(true)
    setError(null)
    try {
      const result = await submitTask(projectId, taskId, deliverable)
      setResultsByTask((prev) => ({ ...prev, [taskId]: result }))
      setExpandedTaskId(null)
      setDeliverable('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    } finally {
      setBusy(false)
    }
  }

  if (error) {
    return (
      <div className="project-view">
        <div className="message error">{error}</div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="project-view">
        <p>Loading…</p>
      </div>
    )
  }

  return (
    <div className="project-view">
      <Link to={`/goals/${project.goal_id}`} className="back-link">
        ← Goal
      </Link>
      <div className="project-view-header">
        <h2>{project.title}</h2>
        <span className={`status-tag status-${project.status}`}>{project.status}</span>
      </div>
      <p className="subtitle">{project.objective}</p>

      {tasks.length === 0 ? (
        <p className="subtitle">
          Tasks aren't available after leaving this page -- reopen it right after starting the
          project to submit deliverables.
        </p>
      ) : (
        <div className="task-list">
          {tasks.map((task) => {
            const result = resultsByTask[task.task_id]
            const completed = result !== undefined || task.status === 'completed'
            return (
              <div key={task.task_id} className="task">
                <button
                  type="button"
                  className="task-header"
                  onClick={() => toggleTask(task.task_id)}
                  disabled={completed}
                >
                  <span>
                    {task.sequence}. {task.description}
                  </span>
                  <span className={`status-tag status-${completed ? 'completed' : task.status}`}>
                    {completed ? 'completed' : task.status}
                  </span>
                </button>
                {expandedTaskId === task.task_id && !completed && (
                  <form className="task-form" onSubmit={(e) => handleSubmit(e, task.task_id)}>
                    <label htmlFor={`deliverable-${task.task_id}`}>Deliverable</label>
                    <textarea
                      id={`deliverable-${task.task_id}`}
                      value={deliverable}
                      onChange={(e) => setDeliverable(e.target.value)}
                      rows={5}
                      required
                    />
                    <button type="submit" disabled={busy || deliverable.trim().length === 0}>
                      {busy ? 'Submitting…' : 'Submit'}
                    </button>
                  </form>
                )}
                {result && (
                  <div className="task-result">
                    {result.evaluation && (
                      <>
                        <p className="feedback">{result.evaluation.feedback}</p>
                        <div className="evaluation-scores">
                          <span>{Math.round(result.evaluation.correctness * 100)}% correctness</span>
                          <span>{Math.round(result.evaluation.independence * 100)}% independence</span>
                          <span>{Math.round(result.evaluation.transfer * 100)}% transfer</span>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
