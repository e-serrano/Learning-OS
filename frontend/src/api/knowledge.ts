import { request } from './client'

export type ConceptStatus =
  | 'unknown'
  | 'learning'
  | 'weak'
  | 'developing'
  | 'usable'
  | 'strong'
  | 'mastered'
  | 'needs_review'
  | 'deprecated'

export interface Concept {
  id: string
  title: string
  domain: string
  status: ConceptStatus
  /** 0..5 scale (docs/DOMAIN_MODEL.md #18), same as `RoadmapNode.mastery`. */
  mastery: number
  confidence: number
  importance: number
  retention: number
  last_practiced: string | null
  next_review: string | null
  obsidian_path: string | null
  created_at: string
  updated_at: string
}

export interface ConceptRelation {
  source_id: string
  target_id: string
  relation: string
  weight: number | null
}

export function listKnowledge(
  goalId: string,
  status?: ConceptStatus,
): Promise<{ concepts: Concept[] }> {
  const query = status ? `?status=${status}` : ''
  return request(`/goals/${goalId}/knowledge${query}`)
}

export function getConceptRelations(
  conceptId: string,
): Promise<{ relations: ConceptRelation[] }> {
  return request(`/concepts/${conceptId}/relations`)
}
