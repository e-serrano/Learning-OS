import { useCallback, useEffect, useMemo, useState } from 'react'
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
import { KnowledgeGraph } from './KnowledgeGraph'
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
 * separate UI needed beyond exposing that filter, defaulted to `weak`.
 *
 * Graph view (docs/TASKS.md T131) adds a node-link rendering of the same
 * data alongside the list, `KnowledgeGraph.tsx` -- the first real
 * node-link diagram in the app (`RoadmapView`, T113, deliberately chose a
 * list over one for its MVP scope). There is no batch "relations for a
 * goal" endpoint (only `GET /concepts/{id}/relations`, one concept at a
 * time), so switching to graph view fetches every currently-loaded
 * concept's relations in parallel and merges them into the same
 * `relationsById` cache the list view already populates lazily per row
 * -- same underlying call, just eager instead of on-expand. Because it
 * reuses `concepts` as-is, the graph reflects whatever the status filter
 * currently shows; an edge whose other end was filtered out is simply
 * skipped (the graph can only draw nodes it has -- switch the filter to
 * "All" for the complete graph). Selecting a node reuses
 * `toggleExpand`/`ConceptDetailsPanel` -- one detail-rendering path for
 * both views. */
export function KnowledgeExplorer() {
  const { goalId } = useParams<{ goalId: string }>()
  const navigate = useNavigate()
  const [status, setStatus] = useState<ConceptStatus | ''>('')
  const [concepts, setConcepts] = useState<Concept[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [relationsById, setRelationsById] = useState<Record<string, ConceptRelation[]>>({})
  const [assessing, setAssessing] = useState(false)
  const [view, setView] = useState<'list' | 'graph'>('list')
  const [loadingGraph, setLoadingGraph] = useState(false)

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

  useEffect(() => {
    if (view !== 'graph' || !concepts) return
    const missing = concepts.filter((c) => !relationsById[c.id])
    if (missing.length === 0) return
    let cancelled = false
    setLoadingGraph(true)
    Promise.all(
      missing.map(async (c): Promise<readonly [string, ConceptRelation[]]> => {
        try {
          const { relations } = await getConceptRelations(c.id)
          return [c.id, relations]
        } catch {
          return [c.id, []]
        }
      }),
    ).then((entries) => {
      if (cancelled) return
      setRelationsById((prev) => {
        const next = { ...prev }
        for (const [id, relations] of entries) next[id] = relations
        return next
      })
      setLoadingGraph(false)
    })
    return () => {
      cancelled = true
    }
  }, [view, concepts, relationsById])

  const titleById = useMemo(
    () => Object.fromEntries((concepts ?? []).map((c) => [c.id, c.title])),
    [concepts],
  )

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

  const selectedConcept = concepts?.find((c) => c.id === expandedId) ?? null

  return (
    <div className="knowledge-explorer">
      <Link to={goalId ? `/goals/${goalId}` : '/'} className="back-link">
        ← Goal
      </Link>
      <h2>Knowledge Explorer</h2>

      <div className="knowledge-toolbar">
        <div>
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
        </div>
        <div className="view-toggle" role="group" aria-label="View">
          <button
            type="button"
            className={view === 'list' ? 'active' : ''}
            onClick={() => setView('list')}
          >
            List
          </button>
          <button
            type="button"
            className={view === 'graph' ? 'active' : ''}
            onClick={() => setView('graph')}
          >
            Graph
          </button>
        </div>
      </div>

      {error && <div className="message error">{error}</div>}

      {!error && !concepts && <p>Loading…</p>}

      {concepts && concepts.length === 0 && <p className="subtitle">No concepts match.</p>}

      {concepts && concepts.length > 0 && view === 'list' && (
        <div className="concept-list">
          {concepts.map((concept) => (
            <ConceptRow
              key={concept.id}
              concept={concept}
              expanded={expandedId === concept.id}
              relations={relationsById[concept.id]}
              titleById={titleById}
              onToggle={() => toggleExpand(concept.id)}
              onStartAssessment={() => startAssessment(concept.id)}
              assessing={assessing}
            />
          ))}
        </div>
      )}

      {concepts && concepts.length > 0 && view === 'graph' && (
        <div className="knowledge-graph-wrapper">
          {loadingGraph && <p className="subtitle">Loading relations…</p>}
          <KnowledgeGraph
            concepts={concepts}
            relations={concepts.flatMap((c) => relationsById[c.id] ?? [])}
            selectedId={expandedId}
            onSelect={toggleExpand}
          />
          {selectedConcept && (
            <div className="knowledge-graph-details">
              <div className="knowledge-graph-details-header">
                <strong>{selectedConcept.title}</strong>
                <span className="domain-tag">{selectedConcept.domain}</span>
                <span className={`status-tag status-${selectedConcept.status}`}>
                  {selectedConcept.status}
                </span>
              </div>
              <ConceptDetailsPanel
                concept={selectedConcept}
                relations={relationsById[selectedConcept.id]}
                titleById={titleById}
                onStartAssessment={() => startAssessment(selectedConcept.id)}
                assessing={assessing}
              />
            </div>
          )}
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
        <ConceptDetailsPanel
          concept={concept}
          relations={relations}
          titleById={titleById}
          onStartAssessment={onStartAssessment}
          assessing={assessing}
        />
      )}
    </div>
  )
}

function ConceptDetailsPanel({
  concept,
  relations,
  titleById,
  onStartAssessment,
  assessing,
}: {
  concept: Concept
  relations: ConceptRelation[] | undefined
  titleById: Record<string, string>
  onStartAssessment: () => void
  assessing: boolean
}) {
  return (
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
      {relations && relations.length === 0 && <p className="subtitle">No related concepts.</p>}
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
  )
}
