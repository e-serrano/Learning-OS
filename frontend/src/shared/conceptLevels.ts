export interface PrerequisiteEdge {
  source_id: string
  target_id: string
  relation: string
}

/** Prerequisite depth per item -- level 0 is foundational (no
 * `PREREQUISITE_OF` prerequisite inside the given item set), every other
 * item sits one level below the deepest of its own prerequisites. Used
 * by `KnowledgeGraph`'s row layout (docs/TASKS.md T131) and by
 * `orderByPrerequisite` below (docs/TASKS.md T156).
 *
 * Cycles shouldn't happen in practice, but relations can be AI-authored
 * and aren't guaranteed acyclic -- a concept already "in progress" up
 * its own chain falls back to level 0 instead of recursing forever,
 * rather than crashing or silently dropping it from the result. */
export function computeLevels<T extends { id: string }>(
  items: T[],
  edges: readonly PrerequisiteEdge[],
): Map<string, number> {
  const ids = new Set(items.map((item) => item.id))
  const prerequisitesOf = new Map<string, string[]>()
  for (const edge of edges) {
    if (edge.relation !== 'PREREQUISITE_OF') continue
    if (!ids.has(edge.source_id) || !ids.has(edge.target_id) || edge.source_id === edge.target_id) {
      continue
    }
    const list = prerequisitesOf.get(edge.target_id) ?? []
    list.push(edge.source_id)
    prerequisitesOf.set(edge.target_id, list)
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

  for (const item of items) levelOf(item.id)
  return levels
}

/** Orders items so a `PREREQUISITE_OF` source always comes before the
 * target it unlocks -- basics first, complex/dependent items after
 * (docs/TASKS.md T156, user request, for `RoadmapView` and
 * `KnowledgeExplorer`'s list view). `Array.prototype.sort` is stable
 * (ES2019+), so items at the same level keep their original relative
 * order. */
export function orderByPrerequisite<T extends { id: string }>(
  items: T[],
  edges: readonly PrerequisiteEdge[],
): T[] {
  const levels = computeLevels(items, edges)
  return [...items].sort((a, b) => (levels.get(a.id) ?? 0) - (levels.get(b.id) ?? 0))
}
