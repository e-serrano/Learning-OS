"""Review/transfer E2E (docs/TASKS.md T091): a weak concept generates a
due review, completing it produces evidence and updates retention, and
a later transfer assessment produces a measurable transfer outcome --
exercising every service built in T086-T090 against a real
SQLite-backed stack.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session as DbSession

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import EvaluatorResponse, ExerciseGeneratorResponse
from app.ai.orchestrator import AIOrchestrator
from app.domain.entities import Concept, LearningGoal, Review
from app.domain.enums import (
    ConceptStatus,
    EvidenceSourceType,
    ExerciseType,
    GoalStatus,
    ReviewStatus,
    TargetLevel,
)
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.models import ActivityModel, SessionModel
from app.persistence.repositories import (
    SqlConceptRelationRepository,
    SqlConceptRepository,
    SqlEvaluationRepository,
    SqlEvidenceRepository,
    SqlExerciseAttemptRepository,
    SqlExerciseRepository,
    SqlGoalRepository,
    SqlMistakeRepository,
    SqlReviewRepository,
    SqlSessionRepository,
)
from app.services.answer_submission_service import AnswerSubmissionService
from app.services.assessment_completion_service import AssessmentCompletionService
from app.services.context_builder import ContextBuilder
from app.services.evaluator_service import EvaluatorService
from app.services.evidence_creation_service import EvidenceCreationService
from app.services.retention_update_service import RetentionUpdateService
from app.services.review_completion_service import ReviewCompletionService
from app.services.review_creation_service import ReviewCreationService
from app.services.review_scheduler import ReviewScheduler
from app.services.todays_reviews_service import TodaysReviewsService
from app.services.transfer_assessment_service import TransferAssessmentService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW


class SequentialIdGenerator:
    def __init__(self) -> None:
        self._counters: dict[str, int] = {}

    def new_id(self, prefix: str) -> str:
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return f"{prefix}_{self._counters[prefix]}"


def _engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


def _seed_session_and_activity(engine: Engine, session_id: str, activity_id: str) -> None:
    with DbSession(engine) as db:
        db.add(
            SessionModel(
                id=session_id,
                goal_id="goal_1",
                mode="assessment",
                objective="Transfer check",
                status="active",
                started_at=NOW.isoformat(),
                created_at=NOW.isoformat(),
            )
        )
        db.flush()
        db.add(
            ActivityModel(
                id=activity_id,
                session_id=session_id,
                type="assessment",
                sequence=1,
                status="active",
                payload_json="{}",
                created_at=NOW.isoformat(),
            )
        )
        db.commit()


@pytest.mark.asyncio
async def test_weak_concept_review_then_measurable_transfer(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    ids = SequentialIdGenerator()
    clock = FixedClock()

    goals = SqlGoalRepository(engine)
    concepts = SqlConceptRepository(engine)
    evidence = SqlEvidenceRepository(engine)
    reviews = SqlReviewRepository(engine)
    exercises = SqlExerciseRepository(engine)
    sessions = SqlSessionRepository(engine)
    attempts = SqlExerciseAttemptRepository(engine)
    evaluations = SqlEvaluationRepository(engine)

    provider = MockProvider()
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]

    # -- a weak concept, already due for review
    goals.add(
        LearningGoal(
            id="goal_1",
            title="Learn SQL",
            target_level=TargetLevel.PROFESSIONAL,
            status=GoalStatus.ACTIVE,
            priority=3,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    concepts.add(
        Concept(
            id="window_functions",
            title="Window Functions",
            domain="sql",
            status=ConceptStatus.WEAK,
            mastery=0.8,
            confidence=20,
            importance=4,
            retention=15,
            next_review=NOW - timedelta(hours=1),
            created_at=NOW,
            updated_at=NOW,
        )
    )
    reviews.add(
        Review(
            id="review_seed",
            concept_id="window_functions",
            goal_id="goal_1",
            scheduled_at=NOW - timedelta(hours=1),
            interval_days=1.0,
            status=ReviewStatus.SCHEDULED,
        )
    )

    # -- T086: the review shows up as due today
    todays_reviews = TodaysReviewsService(reviews, clock)
    assert [r.id for r in todays_reviews.list_today()] == ["review_seed"]

    # -- T087: complete the review (self-reported, high confidence)
    review_creation = ReviewCreationService(reviews, ReviewScheduler(clock, ids))
    review_completion = ReviewCompletionService(reviews, evidence, review_creation, clock, ids)
    _seed_session_and_activity(engine, "session_review", "activity_review")
    completion = review_completion.complete_review(
        "review_seed",
        "activity_review",
        answer="A window function computes over a row set",
        confidence=85,
    )
    assert completion.completed_review.status == ReviewStatus.COMPLETED
    assert completion.evidence.source_type == EvidenceSourceType.REVIEW
    assert completion.next_review.status == ReviewStatus.SCHEDULED

    # -- T088: retention is derived from that review evidence
    retention_service = RetentionUpdateService(concepts, evidence)
    updated_concept = retention_service.update_retention("window_functions")
    assert updated_concept.retention == 85.0  # confidence 85 -> correctness 0.85 -> retention 85%

    # -- T089: later, a transfer assessment probes the same concept in a new scenario
    context_builder = ContextBuilder(
        goals,
        concepts,
        SqlConceptRelationRepository(engine),
        evidence,
        SqlMistakeRepository(engine),
    )
    transfer_service = TransferAssessmentService(
        goals, context_builder, exercises, orchestrator, clock, ids
    )
    provider.set_response(
        ExerciseGeneratorResponse,
        ExerciseGeneratorResponse(
            type=ExerciseType.SCENARIO,
            difficulty=4,
            prompt="Given a new logistics dataset, rank shipments per warehouse.",
            success_criteria=["Uses a window function correctly in a new domain"],
            hints=[],
            solution=(
                "SELECT RANK() OVER (PARTITION BY warehouse_id ORDER BY ship_date) FROM shipments;"
            ),
            common_mistakes=[],
            transfer_variant=None,
        ),
    )
    transfer_exercise = await transfer_service.generate_transfer_scenario(
        "goal_1", "window_functions"
    )
    assert transfer_exercise.concept_ids == ["window_functions"]

    # -- T090: complete it, producing a measurable transfer outcome
    _seed_session_and_activity(engine, "session_transfer", "activity_transfer")
    answer_submission = AnswerSubmissionService(exercises, sessions, attempts, clock, ids)
    evaluator = EvaluatorService(attempts, exercises, evaluations, orchestrator, clock, ids)
    evidence_creation = EvidenceCreationService(
        evaluations, attempts, exercises, evidence, clock, ids
    )
    assessment_completion = AssessmentCompletionService(
        answer_submission, evaluator, evidence_creation
    )
    provider.set_response(
        EvaluatorResponse,
        EvaluatorResponse(
            correctness=0.9,
            reasoning=0.85,
            completeness=0.8,
            independence=0.75,
            transfer=0.8,
            feedback="Correctly applied the concept to a new domain.",
            recommended_action="advance",
        ),
    )
    assessment_result = await assessment_completion.complete_assessment(
        transfer_exercise.id,
        "session_transfer",
        "activity_transfer",
        answer=(
            "SELECT RANK() OVER (PARTITION BY warehouse_id ORDER BY ship_date) FROM shipments;"
        ),
        confidence=80,
    )

    # -- the narrative closes: weak concept -> review -> measurable later transfer
    assert assessment_result.transfer_demonstrated is True
    assert assessment_result.independence_demonstrated is True
    sources = {e.source_type for e in evidence.list_by_concept("window_functions")}
    assert EvidenceSourceType.REVIEW in sources
    assert EvidenceSourceType.ASSESSMENT in sources
