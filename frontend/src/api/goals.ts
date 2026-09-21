import { request } from './client'

export type TargetLevel = 'beginner' | 'intermediate' | 'advanced' | 'professional'
export type GoalStatus = 'draft' | 'active' | 'paused' | 'completed' | 'archived'

export interface Goal {
  id: string
  title: string
  description: string | null
  domain: string | null
  target_level: TargetLevel
  status: GoalStatus
  priority: number
  deadline: string | null
  available_minutes_per_week: number | null
  created_at: string
  updated_at: string
}

export interface GoalListResponse {
  goals: Goal[]
}

export interface GoalProgress {
  mastery: number
  concepts_total: number
  mastered: number
  weak: number
  due_reviews: number
  recent_sessions: number
}

export function listGoals(): Promise<GoalListResponse> {
  return request('/goals')
}

export function createGoal(input: { title: string; target_level: TargetLevel }): Promise<Goal> {
  return request('/goals', { method: 'POST', body: JSON.stringify(input) })
}

export function getGoalProgress(goalId: string): Promise<GoalProgress> {
  return request(`/goals/${goalId}/progress`)
}
