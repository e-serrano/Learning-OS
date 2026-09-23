"""Review routes (docs/TASKS.md T104, docs/API_SPEC.md #7).

`POST /reviews/{id}/complete` has no documented response shape (the
spec only shows the request body) -- designed here as the completed
review, the newly-scheduled next review, and the concept's updated
mastery/retention/status, so a client can reflect the outcome without a
second round-trip (same reasoning as T103's `knowledge_updates`).
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies import get_review_flow_service, get_todays_reviews_service
from app.api.errors import api_error
from app.domain.entities import Review
from app.domain.enums import ConceptStatus, ReviewStatus
from app.domain.value_objects import ConfidencePercent
from app.services.review_completion_service import ReviewNotDueError, ReviewNotFoundError
from app.services.review_flow_service import ReviewFlowResult, ReviewFlowService
from app.services.todays_reviews_service import TodaysReviewsService

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])

TodaysReviewsServiceDep = Annotated[TodaysReviewsService, Depends(get_todays_reviews_service)]
ReviewFlowServiceDep = Annotated[ReviewFlowService, Depends(get_review_flow_service)]


class ReviewResponse(BaseModel):
    id: str
    concept_id: str
    goal_id: str
    scheduled_at: datetime
    completed_at: datetime | None
    interval_days: float
    stability: float | None
    difficulty: float | None
    status: ReviewStatus

    @classmethod
    def from_entity(cls, review: Review) -> "ReviewResponse":
        return cls(**review.model_dump())


class ReviewListResponse(BaseModel):
    reviews: list[ReviewResponse]


class ConceptSummaryResponse(BaseModel):
    concept_id: str
    mastery: float
    retention: float
    status: ConceptStatus


class CompleteReviewRequest(BaseModel):
    answer: str
    confidence: ConfidencePercent


class ReviewCompletionResponse(BaseModel):
    completed_review: ReviewResponse
    next_review: ReviewResponse
    concept: ConceptSummaryResponse

    @classmethod
    def from_result(cls, result: ReviewFlowResult) -> "ReviewCompletionResponse":
        return cls(
            completed_review=ReviewResponse.from_entity(result.completed_review),
            next_review=ReviewResponse.from_entity(result.next_review),
            concept=ConceptSummaryResponse(
                concept_id=result.concept.id,
                mastery=result.concept.mastery,
                retention=result.concept.retention,
                status=result.concept.status,
            ),
        )


@router.get("/today", response_model=ReviewListResponse)
def list_todays_reviews(service: TodaysReviewsServiceDep) -> ReviewListResponse:
    return ReviewListResponse(reviews=[ReviewResponse.from_entity(r) for r in service.list_today()])


@router.post("/{review_id}/complete", response_model=ReviewCompletionResponse)
async def complete_review(
    review_id: str, request: CompleteReviewRequest, service: ReviewFlowServiceDep
) -> ReviewCompletionResponse:
    try:
        result = await service.complete_review(review_id, request.answer, request.confidence)
    except ReviewNotFoundError as exc:
        raise api_error("NOT_FOUND", f"Review '{review_id}' not found", 404) from exc
    except ReviewNotDueError as exc:
        raise api_error("SESSION_STATE_ERROR", str(exc), 409) from exc
    return ReviewCompletionResponse.from_result(result)
