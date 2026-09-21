import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  type Roadmap,
  type RoadmapNode,
  generateRoadmap,
  getRoadmap,
  recalculateRoadmap,
} from '../api/roadmap'
import { MasteryBar } from '../shared/MasteryBar'
import './roadmap.css'

const MAX_MASTERY = 5

/** Roadmap view (docs/TASKS.md T113, dep T101): dependencies and
 * progress per concept. Renders the node/edge graph `GET
 * /goals/{id}/roadmap` returns as a readable list rather than a node-link
 * diagram -- no other Phase 11 page attempts graph rendering yet, and a
 * list already carries every piece of information the task asks for
 * (each node's progress, and its prerequisites derived from
 * `PREREQUISITE_OF` edges) without the added complexity of a layout
 * engine for an MVP page. */
export function RoadmapView() {
  const { goalId } = useParams<{ goalId: string }>()
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null)
  const [notGenerated, setNotGenerated] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    if (!goalId) return
    try {
      setRoadmap(await getRoadmap(goalId))
      setNotGenerated(false)
      setError(null)
    } catch (err) {
      if (err instanceof ApiError && err.code === 'NOT_FOUND') {
        setNotGenerated(true)
        setError(null)
      } else {
        setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
      }
    }
  }, [goalId])

  useEffect(() => {
    load()
  }, [load])

  async function handleGenerate() {
    if (!goalId) return
    setBusy(true)
    setError(null)
    try {
      setRoadmap(await generateRoadmap(goalId))
      setNotGenerated(false)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    } finally {
      setBusy(false)
    }
  }

  async function handleRecalculate() {
    if (!goalId) return
    setBusy(true)
    setError(null)
    try {
      setRoadmap(await recalculateRoadmap(goalId))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    } finally {
      setBusy(false)
    }
  }

  if (error) {
    return (
      <div className="roadmap-view">
        <BackLink goalId={goalId} />
        <div className="message error">{error}</div>
      </div>
    )
  }

  if (notGenerated) {
    return (
      <div className="roadmap-view">
        <BackLink goalId={goalId} />
        <h2>Roadmap</h2>
        <p className="subtitle">No roadmap has been generated for this goal yet.</p>
        <button type="button" onClick={handleGenerate} disabled={busy}>
          {busy ? 'Generating…' : 'Generate roadmap'}
        </button>
      </div>
    )
  }

  if (!roadmap) {
    return (
      <div className="roadmap-view">
        <p>Loading…</p>
      </div>
    )
  }

  const prerequisitesOf = (nodeId: string) =>
    roadmap.edges
      .filter((e) => e.relation === 'PREREQUISITE_OF' && e.target_id === nodeId)
      .map((e) => roadmap.nodes.find((n) => n.id === e.source_id)?.title ?? e.source_id)

  return (
    <div className="roadmap-view">
      <BackLink goalId={goalId} />
      <div className="roadmap-header">
        <h2>Roadmap</h2>
        <span className="version-tag">v{roadmap.version}</span>
      </div>
      <button type="button" className="secondary" onClick={handleRecalculate} disabled={busy}>
        {busy ? 'Recalculating…' : 'Recalculate'}
      </button>
      <div className="roadmap-nodes">
        {roadmap.nodes.map((node) => (
          <RoadmapNodeCard key={node.id} node={node} prerequisites={prerequisitesOf(node.id)} />
        ))}
      </div>
    </div>
  )
}

function BackLink({ goalId }: { goalId: string | undefined }) {
  return (
    <Link to={goalId ? `/goals/${goalId}` : '/'} className="back-link">
      ← Goal
    </Link>
  )
}

function RoadmapNodeCard({
  node,
  prerequisites,
}: {
  node: RoadmapNode
  prerequisites: string[]
}) {
  return (
    <div className="roadmap-node">
      <div className="roadmap-node-header">
        <strong>{node.title}</strong>
        <span className="domain-tag">{node.domain}</span>
      </div>
      <MasteryBar mastery={node.mastery / MAX_MASTERY} />
      <div className="roadmap-node-meta">
        <span>{node.status}</span>
        {prerequisites.length > 0 && <span>Requires: {prerequisites.join(', ')}</span>}
      </div>
    </div>
  )
}
