import type { Concept, ConceptRelation } from '../api/knowledge'

const NODE_WIDTH = 140
const NODE_HEIGHT = 44
const COLUMN_GAP = 40
const ROW_GAP = 70
const PADDING = 30
const TITLE_MAX_CHARS = 18

interface LaidOutNode {
  concept: Concept
  x: number
  y: number
}

interface LaidOutEdge {
  relation: ConceptRelation
  x1: number
  y1: number
  x2: number
  y2: number
}

/** Node-link layout for `KnowledgeGraph` (docs/TASKS.md T131). Level 0 =
 * concepts with no `PREREQUISITE_OF` prerequisite inside the current node
 * set (foundational); every other concept sits one row below the deepest
 * of its own prerequisites -- the same edge direction `RoadmapView`
 * (T113) already reads (source = the prerequisite, target = the concept
 * that needs it). Cycles shouldn't happen in practice, but relations can
 * be AI-authored and aren't guaranteed acyclic, so a concept already
 * "in progress" up its own chain falls back to level 0 instead of
 * recursing forever. No layout-engine dependency -- a level-per-row
 * grid is enough to make prerequisite structure legible without pulling
 * in a graph library (frontend has no chart/graph dependency today). */
function computeLevels(concepts: Concept[], relations: ConceptRelation[]): Map<string, number> {
  const ids = new Set(concepts.map((c) => c.id))
  const prerequisitesOf = new Map<string, string[]>()
  for (const r of relations) {
    if (r.relation !== 'PREREQUISITE_OF') continue
    if (!ids.has(r.source_id) || !ids.has(r.target_id) || r.source_id === r.target_id) continue
    const list = prerequisitesOf.get(r.target_id) ?? []
    list.push(r.source_id)
    prerequisitesOf.set(r.target_id, list)
  }

  const levels = new Map<string, number>()
  const inProgress = new Set<string>()

  function levelOf(id: string): number {
    const cached = levels.get(id)
    if (cached !== undefined) return cached
    if (inProgress.has(id)) return 0
    inProgress.add(id)
    const prereqs = prerequisitesOf.get(id) ?? []
    const level = prereqs.length === 0 ? 0 : 1 + Math.max(...prereqs.map(levelOf))
    inProgress.delete(id)
    levels.set(id, level)
    return level
  }

  for (const c of concepts) levelOf(c.id)
  return levels
}

function layout(concepts: Concept[], relations: ConceptRelation[]) {
  const levels = computeLevels(concepts, relations)
  const byLevel = new Map<number, Concept[]>()
  for (const c of concepts) {
    const level = levels.get(c.id) ?? 0
    const list = byLevel.get(level) ?? []
    list.push(c)
    byLevel.set(level, list)
  }

  const nodes: LaidOutNode[] = []
  const positionById = new Map<string, { x: number; y: number }>()
  const maxLevel = Math.max(0, ...byLevel.keys())
  for (let level = 0; level <= maxLevel; level++) {
    const rowConcepts = byLevel.get(level) ?? []
    rowConcepts.forEach((concept, index) => {
      const x = PADDING + index * (NODE_WIDTH + COLUMN_GAP)
      const y = PADDING + level * (NODE_HEIGHT + ROW_GAP)
      nodes.push({ concept, x, y })
      positionById.set(concept.id, { x, y })
    })
  }

  const ids = new Set(concepts.map((c) => c.id))
  const edges: LaidOutEdge[] = []
  for (const r of relations) {
    if (r.source_id === r.target_id) continue
    if (!ids.has(r.source_id) || !ids.has(r.target_id)) continue
    const from = positionById.get(r.source_id)
    const to = positionById.get(r.target_id)
    if (!from || !to) continue
    edges.push({
      relation: r,
      x1: from.x + NODE_WIDTH / 2,
      y1: from.y + NODE_HEIGHT / 2,
      x2: to.x + NODE_WIDTH / 2,
      y2: to.y + NODE_HEIGHT / 2,
    })
  }

  const columnsInWidestRow = Math.max(1, ...Array.from(byLevel.values()).map((c) => c.length))
  const width =
    PADDING * 2 + columnsInWidestRow * NODE_WIDTH + Math.max(0, columnsInWidestRow - 1) * COLUMN_GAP
  const height = PADDING * 2 + (maxLevel + 1) * NODE_HEIGHT + maxLevel * ROW_GAP

  return { nodes, edges, width, height }
}

function truncate(title: string): string {
  return title.length > TITLE_MAX_CHARS ? `${title.slice(0, TITLE_MAX_CHARS - 1)}…` : title
}

/** SVG node-link rendering of a goal's concepts and their relations.
 * Purely presentational -- `KnowledgeExplorer` owns fetching and
 * selection state, this component only lays out and draws whatever
 * `concepts`/`relations` it is given, and reports clicks via `onSelect`. */
export function KnowledgeGraph({
  concepts,
  relations,
  selectedId,
  onSelect,
}: {
  concepts: Concept[]
  relations: ConceptRelation[]
  selectedId: string | null
  onSelect: (conceptId: string) => void
}) {
  if (concepts.length === 0) return null
  const { nodes, edges, width, height } = layout(concepts, relations)

  return (
    <div className="knowledge-graph-scroll">
      <svg
        className="knowledge-graph"
        viewBox={`0 0 ${width} ${height}`}
        width={width}
        height={height}
        role="img"
        aria-label="Concept graph"
      >
        <defs>
          <marker
            id="kg-arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M0 0 L10 5 L0 10 z" fill="rgba(128, 128, 128, 0.8)" />
          </marker>
        </defs>
        {edges.map((edge) => (
          <line
            key={`${edge.relation.source_id}-${edge.relation.target_id}-${edge.relation.relation}`}
            x1={edge.x1}
            y1={edge.y1}
            x2={edge.x2}
            y2={edge.y2}
            className={`kg-edge kg-edge-${edge.relation.relation.toLowerCase()}`}
            markerEnd={edge.relation.relation === 'PREREQUISITE_OF' ? 'url(#kg-arrow)' : undefined}
          />
        ))}
        {nodes.map(({ concept, x, y }) => (
          <g
            key={concept.id}
            transform={`translate(${x}, ${y})`}
            className={`kg-node kg-status-${concept.status}${
              concept.id === selectedId ? ' kg-node-selected' : ''
            }`}
            onClick={() => onSelect(concept.id)}
            role="button"
            tabIndex={0}
            aria-label={concept.title}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') onSelect(concept.id)
            }}
          >
            <rect width={NODE_WIDTH} height={NODE_HEIGHT} rx={8} />
            <text x={NODE_WIDTH / 2} y={NODE_HEIGHT / 2} textAnchor="middle" dominantBaseline="middle">
              {truncate(concept.title)}
            </text>
          </g>
        ))}
      </svg>
    </div>
  )
}
