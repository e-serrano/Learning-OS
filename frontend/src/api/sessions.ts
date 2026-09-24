import { request } from './client'

export type SessionMode =
  | 'guided'
  | 'practice'
  | 'review'
  | 'assessment'
  | 'project'
  | 'interview'
  | 'socratic'
  | 'teach_back'
export type SessionStatus = 'planned' | 'active' | 'completed' | 'abandoned'
export type ActivityType =
  | 'recall'
  | 'explanation'
  | 'example'
  | 'exercise'
  | 'feedback'
  | 'reflection'
  | 'review'
  | 'project_task'
  | 'assessment'

export interface Session {
  id: string
  goal_id: string
  mode: SessionMode
  objective: string
  status: SessionStatus
  started_at: string | null
  ended_at: string | null
}

export interface ExerciseContent {
  exercise_id: string
  type: string
  difficulty: number
  prompt: string
  success_criteria: string[]
  hints: string[]
}

export interface NextActivity {
  activity_id: string
  type: ActivityType
  content: ExerciseContent
}

export interface Evaluation {
  id: string
  correctness: number
  reasoning: number
  completeness: number
  independence: number
  transfer: number
  misconceptions: string[]
  feedback: string
  recommended_action: string
}

export interface KnowledgeUpdate {
  concept_id: string
  mastery: number
  status: string
  mistakes_recorded: number
  next_review_scheduled_at: string
}

export interface AnswerResult {
  evaluation: Evaluation
  knowledge_updates: KnowledgeUpdate[]
  next_activity: NextActivity | null
}

export function createSession(
  goalId: string,
  mode: SessionMode,
  durationMinutes: number,
): Promise<Session> {
  return request(`/goals/${goalId}/sessions`, {
    method: 'POST',
    body: JSON.stringify({ mode, duration_minutes: durationMinutes }),
  })
}

export function getSession(sessionId: string): Promise<Session> {
  return request(`/sessions/${sessionId}`)
}

export function getNextActivity(sessionId: string): Promise<NextActivity> {
  return request(`/sessions/${sessionId}/next`, { method: 'POST' })
}

export function submitAnswer(
  sessionId: string,
  activityId: string,
  answer: string,
  confidence: number,
): Promise<AnswerResult> {
  return request(`/sessions/${sessionId}/activities/${activityId}/answer`, {
    method: 'POST',
    body: JSON.stringify({ answer, confidence }),
  })
}

export function completeSession(sessionId: string): Promise<Session> {
  return request(`/sessions/${sessionId}/complete`, { method: 'POST' })
}

export interface TutorTurn {
  speaker: 'tutor' | 'learner'
  content: string
}

export interface TutorTurnResult {
  mode: string
  content: string
  check_for_understanding: string | null
  next_activity: string | null
}

export function askTutor(
  sessionId: string,
  conceptId: string,
  history: TutorTurn[],
  message: string,
): Promise<TutorTurnResult> {
  return request(`/sessions/${sessionId}/tutor`, {
    method: 'POST',
    body: JSON.stringify({ concept_id: conceptId, message, history }),
  })
}
