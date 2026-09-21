import { request } from './client'

export interface Review {
  id: string
  concept_id: string
  goal_id: string
  scheduled_at: string
  completed_at: string | null
  interval_days: number
  stability: number | null
  difficulty: number | null
  status: string
}

export interface ReviewConceptSummary {
  concept_id: string
  mastery: number
  retention: number
  status: string
}

export interface ReviewCompletionResult {
  completed_review: Review
  next_review: Review
  concept: ReviewConceptSummary
}

export function listTodaysReviews(): Promise<{ reviews: Review[] }> {
  return request('/reviews/today')
}

export function completeReview(
  reviewId: string,
  answer: string,
  confidence: number,
): Promise<ReviewCompletionResult> {
  return request(`/reviews/${reviewId}/complete`, {
    method: 'POST',
    body: JSON.stringify({ answer, confidence }),
  })
}
