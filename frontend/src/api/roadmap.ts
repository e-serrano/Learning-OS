import { request } from './client'

export type ConceptRelation =
  | 'PREREQUISITE_OF'
  | 'RELATED_TO'
  | 'PART_OF'
  | 'CONTRASTS_WITH'
  | 'APPLIED_BY'

export interface RoadmapNode {
  id: string
  title: string
  domain: string
  status: string
  /** 0..5 scale (docs/DOMAIN_MODEL.md #18) -- unlike `GoalProgress.mastery`
   * (T107), this is NOT pre-normalized to 0..1. */
  mastery: number
  confidence: number
  importance: number
}

export interface RoadmapEdge {
  source_id: string
  target_id: string
  relation: ConceptRelation
}

export interface Roadmap {
  id: string
  goal_id: string
  version: number
  status: 'active' | 'superseded'
  nodes: RoadmapNode[]
  edges: RoadmapEdge[]
}

export function getRoadmap(goalId: string): Promise<Roadmap> {
  return request(`/goals/${goalId}/roadmap`)
}

export function generateRoadmap(goalId: string): Promise<Roadmap> {
  return request(`/goals/${goalId}/roadmap/generate`, { method: 'POST' })
}

export function recalculateRoadmap(goalId: string): Promise<Roadmap> {
  return request(`/goals/${goalId}/roadmap/recalculate`, { method: 'POST' })
}
