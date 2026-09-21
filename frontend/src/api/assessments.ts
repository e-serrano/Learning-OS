import { request } from './client'

export interface AssessmentExercise {
  exercise_id: string
  type: string
  difficulty: number
  prompt: string
  success_criteria: string[]
  hints: string[]
}

export interface Assessment {
  assessment_id: string
  session_id: string
  goal_id: string
  concept_id: string
  status: string
  exercise: AssessmentExercise
}

export interface AssessmentEvaluation {
  correctness: number
  reasoning: number
  independence: number
  transfer: number
  feedback: string
  misconceptions: string[]
}

export interface AssessmentConceptUpdate {
  concept_id: string
  mastery: number
  status: string
}

export interface AssessmentAnswerResult {
  evaluation: AssessmentEvaluation
  transfer_demonstrated: boolean
  independence_demonstrated: boolean
  updated_concepts: AssessmentConceptUpdate[]
}

export interface AssessmentCompleteResult {
  session_id: string
  status: string
}

export function createAssessment(goalId: string, conceptId: string): Promise<Assessment> {
  return request(`/goals/${goalId}/assessments`, {
    method: 'POST',
    body: JSON.stringify({ concept_id: conceptId }),
  })
}

export function getAssessment(assessmentId: string): Promise<Assessment> {
  return request(`/assessments/${assessmentId}`)
}

export function answerAssessment(
  assessmentId: string,
  answer: string,
  confidence: number,
): Promise<AssessmentAnswerResult> {
  return request(`/assessments/${assessmentId}/answer`, {
    method: 'POST',
    body: JSON.stringify({ answer, confidence }),
  })
}

export function completeAssessment(assessmentId: string): Promise<AssessmentCompleteResult> {
  return request(`/assessments/${assessmentId}/complete`, { method: 'POST' })
}
