import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { createAssessment } from '../api/assessments'
import { ApiError } from '../api/client'
import {
  type Concept,
  type ConceptRelation,
  type ConceptStatus,
  getConceptRelations,
  listKnowledge,
} from '../api/knowledge'
import { MasteryBar } from '../shared/MasteryBar'
import './knowledge.css'

const MAX_MASTERY = 5

const STATUS_FILTERS: ConceptStatus[] = [
  'weak',
  'needs_review',
  'learning',
  'developing',
  'usable',
  'strong',
  'mastered',
  'unknown',
  'deprecated',
]

/** Knowledge explorer (docs/TASKS.md T114, dep T100): concepts, evidence
 * and weaknesses for a goal. "Evidence" here means the materialized
 * signals `Concept` itself carries (mastery, confidence, retention,
 * last practiced) -- T100 is the only dependency, and no route anywhere
 * in the API exposes raw `Evidence` rows (`EvidenceRepository` is
 * evaluator/mastery-engine-internal, never an HTTP resource), so a raw
 * evidence log is out of scope here, same "stick to what the dep list
 * actually provides" reading T112 already used. "Weaknesses" is the
 * `status` filter `GET /goals/{id}/knowledge` already supports -- no
 * separate UI needed beyond exposing that filter, defaulted to `weak`. */
export function KnowledgeExplorer() {
  const { goalId } = useParams<{ goalId: string }>()
  const navigate = useNavigate()
  const [status, setStatus] = useState<ConceptStatus | ''>('')
  const [concepts, setConcepts] = useState<Concept[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [relationsById, setRelationsById] = useState<Record<string, ConceptRelation[]>>({})
  const [assessing, setAssessing] = useState(false)

  const load = useCallback(async () => {
    if (!goalId) return
    try {
      const { concepts: list } = await listKnowledge(goalId, status || undefined)
      setConcepts(list)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    }
  }, [goalId, status])

  useEffect(() => {
    load()
  }, [load])

  async function toggleExpand(conceptId: string) {
    if (expandedId === conceptId) {
      setExpandedId(null)
      return
    }
    setExpandedId(conceptId)
    if (!relationsById[conceptId]) {
      try {
        const { relations } = await getConceptRelations(conceptId)
        setRelationsById((prev) => ({ ...prev, [conceptId]: relations }))
      } catch {
        setRelationsById((prev) => ({ ...prev, [conceptId]: [] }))
      }
    }
  }

  async function startAssessment(conceptId: string) {
    if (!goalId) return
    setAssessing(true)
    setError(null)
    try {
      const assessment = await createAssessment(goalId, conceptId)
      navigate(`/assessments/${assessment.assessment_id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
      setAssessing(false)
    }
  }

  return (
    <div className="knowledge-explorer">
      <Link to={goalId ? `/goals/${goalId}` : '/'} className="back-link">
        ← Goal
      </Link>
      <h2>Knowledge Explorer</h2>

      <label htmlFor="status-filter">Status</label>
      <select
        id="status-filter"
        value={status}
        onChange={(e) => setStatus(e.target.value as ConceptStatus | '')}
      >
        <option value="">All</option>
        {STATUS_FILTERS.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>

      {error && <div className="message error">{error}</div>}

      {!error && !concepts && <p>Loading…</p>}

      {concepts && concepts.length === 0 && <p className="subtitle">No concepts match.</p>}

      {concepts && concepts.length > 0 && (
        <div className="concept-list">
          {concepts.map((concept) => (
            <ConceptRow
              key={concept.id}
              concept={concept}
              expanded={expandedId === concept.id}
              relations={relationsById[concept.id]}
              titleById={Object.fromEntries(concepts.map((c) => [c.id, c.title]))}
              onToggle={() => toggleExpand(concept.id)}
              onStartAssessment={() => startAssessment(concept.id)}
              assessing={assessing}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function ConceptRow({
  concept,
  expanded,
  relations,
  titleById,
  onToggle,
  onStartAssessment,
  assessing,
}: {
  concept: Concept
  expanded: boolean
  relations: ConceptRelation[] | undefined
  titleById: Record<string, string>
  onToggle: () => void
  onStartAssessment: () => void
  assessing: boolean
}) {
  return (
    <div className="concept-row">
      <button type="button" className="concept-row-header" onClick={onToggle}>
        <strong>{concept.title}</strong>
        <span className="domain-tag">{concept.domain}</span>
        <span className={`status-tag status-${concept.status}`}>{concept.status}</span>
      </button>
      {expanded && (
        <div className="concept-details">
          <MasteryBar mastery={concept.mastery / MAX_MASTERY} />
          <div className="concept-stats">
            <span>{concept.confidence}% confidence</span>
            <span>{concept.retention}% retention</span>
            {concept.next_review && (
              <span>Next review {new Date(concept.next_review).toLocaleDateString()}</span>
            )}
            {concept.last_practiced && (
              <span>Last practiced {new Date(concept.last_practiced).toLocaleDateString()}</span>
            )}
          </div>
          {relations === undefined && <p className="subtitle">Loading relations…</p>}
          {relations && relations.length === 0 && (
            <p className="subtitle">No related concepts.</p>
          )}
          {relations && relations.length > 0 && (
            <ul className="relation-list">
              {relations.map((r) => (
                <li key={`${r.source_id}-${r.target_id}-${r.relation}`}>
                  {r.relation.replace(/_/g, ' ').toLowerCase()} →{' '}
                  {titleById[r.target_id] ?? r.target_id}
                </li>
              ))}
            </ul>
          )}
          <button type="button" className="secondary" onClick={onStartAssessment} disabled={assessing}>
            {assessing ? 'Starting…' : 'Start transfer assessment'}
          </button>
        </div>
      )}
    </div>
  )
}
