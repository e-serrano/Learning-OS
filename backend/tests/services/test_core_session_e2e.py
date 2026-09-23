"""Core session E2E (docs/TASKS.md T079): MockProvider drives the full
loop goal -> diagnostic -> roadmap -> session -> exercise -> answer ->
evaluation -> evidence -> mastery -> mistake -> review, exercising every
service built in T065-T078 against a real SQLite-backed stack.

Narrative: the user already knows `select_basics` (existing knowledge,
seeded directly -- there is no "import existing concept" service yet).
Diagnostic tests that pre-existing concept first; the planner then adds
`window_functions` as a new high-leverage concept building on it
(matching AI_CONTRACTS.md #4's "existing knowledge" planner input) --
this lets the literal task order (diagnostic before roadmap) hold
without contradicting DiagnosticService's real dependency on an
already-persisted concept (see T066's note).
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session as DbSession

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import (
    DiagnosticianResponse,
    DiagnosticItem,
    EvaluatorResponse,
    ExerciseGeneratorResponse,
    HighLeverageConcept,
    PlannerResponse,
)
from app.ai.orchestrator import AIOrchestrator
from app.domain.entities import Concept
from app.domain.enums import (
    ActivityStatus,
    ActivityType,
    ConceptRelationType,
    ConceptStatus,
    ExerciseType,
    GoalStatus,
    ReviewStatus,
    SessionMode,
    SessionStatus,
    TargetLevel,
)
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.models import ActivityModel, SessionModel
from app.persistence.repositories import (
    SqlActivityRepository,
    SqlConceptRelationRepository,
    SqlConceptRepository,
    SqlEvaluationRepository,
    SqlEvidenceRepository,
    SqlExerciseAttemptRepository,
    SqlExerciseRepository,
    SqlGoalRepository,
    SqlMistakeRepository,
    SqlReviewRepository,
    SqlRoadmapRepository,
    SqlSessionRepository,
)
from app.services.activity_selector import ActivitySelector
from app.services.adaptive_activity_service import AdaptiveActivityService
from app.services.answer_submission_service import AnswerSubmissionService
from app.services.context_builder import ContextBuilder
from app.services.diagnostic_service import DiagnosticService
from app.services.evaluator_service import EvaluatorService
from app.services.evidence_creation_service import EvidenceCreationService
from app.services.exercise_generator_service import ExerciseGeneratorService
from app.services.goal_service import GoalApplicationService
from app.services.mastery_engine import MasteryEngine
from app.services.mastery_update_service import MasteryUpdateService
from app.services.mistake_tracker import MistakeTracker
from app.services.mistake_update_service import MistakeUpdateService
from app.services.next_activity_service import NextActivityService
from app.services.planner_service import PlannerService
from app.services.review_creation_service import ReviewCreationService
from app.services.review_scheduler import ReviewScheduler
from app.services.roadmap_service import RoadmapEdge, RoadmapNode, RoadmapService
from app.services.session_service import SessionApplicationService

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


@pytest.mark.asyncio
async def test_core_session_flow_end_to_end(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    ids = SequentialIdGenerator()
    clock = FixedClock()

    goals = SqlGoalRepository(engine)
    concepts = SqlConceptRepository(engine)
    concept_relations = SqlConceptRelationRepository(engine)
    evidence = SqlEvidenceRepository(engine)
    mistakes = SqlMistakeRepository(engine)
    reviews = SqlReviewRepository(engine)
    roadmaps = SqlRoadmapRepository(engine)
    exercises = SqlExerciseRepository(engine)
    attempts = SqlExerciseAttemptRepository(engine)
    evaluations = SqlEvaluationRepository(engine)
    sessions = SqlSessionRepository(engine)
    activities = SqlActivityRepository(engine)

    provider = MockProvider()
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]

    context_builder = ContextBuilder(goals, concepts, concept_relations, evidence, mistakes)
    goal_service = GoalApplicationService(goals, clock, ids)
    diagnostic_service = DiagnosticService(
        goals, evidence, context_builder, orchestrator, clock, ids
    )
    planner_service = PlannerService(goals, concepts, orchestrator)
    roadmap_service = RoadmapService(goals, concepts, concept_relations, roadmaps, clock, ids)
    session_service = SessionApplicationService(goals, sessions, clock, ids)
    activity_selector = ActivitySelector(concepts, concept_relations, mistakes, evidence, clock)
    next_activity_service = NextActivityService(sessions, activities, activity_selector, ids)
    exercise_generator_service = ExerciseGeneratorService(
        goals, context_builder, exercises, orchestrator, clock, ids
    )
    answer_submission_service = AnswerSubmissionService(exercises, sessions, attempts, clock, ids)
    evaluator_service = EvaluatorService(attempts, exercises, evaluations, orchestrator, clock, ids)
    evidence_creation_service = EvidenceCreationService(
        evaluations, attempts, exercises, evidence, clock, ids
    )
    mastery_update_service = MasteryUpdateService(concepts, MasteryEngine(evidence))
    mistake_tracker = MistakeTracker(mistakes, clock, ids)
    mistake_update_service = MistakeUpdateService(evaluations, attempts, exercises, mistake_tracker)
    review_creation_service = ReviewCreationService(reviews, ReviewScheduler(clock, ids))
    adaptive_activity_service = AdaptiveActivityService(
        sessions, activities, activity_selector, ids
    )

    # -- existing knowledge, seeded directly (no import service exists yet)
    concepts.add(
        Concept(
            id="select_basics",
            title="SELECT basics",
            domain="sql",
            status=ConceptStatus.USABLE,
            mastery=3,
            confidence=60,
            importance=2,
            retention=50,
            created_at=NOW,
            updated_at=NOW,
        )
    )

    # -- goal (T065)
    goal = goal_service.create_goal(
        title="Learn analytical SQL", target_level=TargetLevel.PROFESSIONAL, domain="sql"
    )
    assert goal.status == GoalStatus.DRAFT
    concepts.link_to_goal(goal.id, "select_basics", importance=2)

    # -- diagnostic against existing knowledge (T066)
    diagnostic_session_id, diagnostic_activity_id = _seed_diagnostic_session(engine, goal.id)
    provider.set_response(
        DiagnosticianResponse,
        DiagnosticianResponse(
            items=[
                DiagnosticItem(
                    concept_id="select_basics",
                    evidence_type="recall",
                    question="What does SELECT * do?",
                    difficulty=1,
                )
            ]
        ),
    )
    items = await diagnostic_service.generate_items(goal.id, ["select_basics"])
    assert items[0].concept_id == "select_basics"
    diagnostic_evidence = diagnostic_service.record_response(
        goal_id=goal.id,
        concept_id="select_basics",
        activity_id=diagnostic_activity_id,
        evidence_type="recall",
        correctness=0.9,
        difficulty=1,
        session_id=diagnostic_session_id,
        question=items[0].question,
    )
    assert diagnostic_evidence.correctness == 0.9

    # -- roadmap: planner proposes a new concept building on existing knowledge (T067, T068)
    provider.set_response(
        PlannerResponse,
        PlannerResponse(
            high_leverage_concepts=[
                HighLeverageConcept(
                    concept_id="window_functions",
                    title="Window Functions",
                    importance=5,
                    reason="Used everywhere in analytics SQL",
                )
            ],
            deferred_topics=["recursive_ctes"],
            roadmap_nodes=[
                {"id": "select_basics", "title": "SELECT basics", "importance": 2},
                {"id": "window_functions", "title": "Window Functions", "importance": 5},
            ],
            roadmap_edges=[
                {
                    "source": "select_basics",
                    "target": "window_functions",
                    "relation": "PREREQUISITE_OF",
                }
            ],
            diagnostic_focus=["window_functions"],
        ),
    )
    plan = await planner_service.plan(goal.id)
    nodes = [RoadmapNode(**n) for n in plan.roadmap_nodes]
    edges = [
        RoadmapEdge(
            source=e["source"], target=e["target"], relation=ConceptRelationType(e["relation"])
        )
        for e in plan.roadmap_edges
    ]
    roadmap = roadmap_service.build_roadmap(goal.id, nodes, edges)
    assert roadmap.version == 1
    assert roadmap.status.value == "active"
    assert concepts.get("window_functions") is not None

    # -- session (T069) + first next-activity pick (T070)
    session = session_service.create_session(goal.id, SessionMode.GUIDED, duration_minutes=30)
    assert session.status == SessionStatus.ACTIVE
    activity = next_activity_service.select_next(session.id)
    # window_functions has importance=5 vs select_basics' importance=2, so it must win
    assert activity.concept_ids == ["window_functions"]

    # -- exercise generation (T071)
    provider.set_response(
        ExerciseGeneratorResponse,
        ExerciseGeneratorResponse(
            type=ExerciseType.SQL,
            difficulty=3,
            prompt="Write a query using ROW_NUMBER().",
            success_criteria=["Uses ROW_NUMBER()"],
            hints=["Think about PARTITION BY"],
            solution="SELECT ROW_NUMBER() OVER (...) FROM t;",
            common_mistakes=["Forgets ORDER BY inside OVER()"],
            transfer_variant="Now do the same with RANK().",
        ),
    )
    exercise = await exercise_generator_service.generate(goal.id, "window_functions")
    assert exercise.concept_ids == ["window_functions"]

    # -- answer submission (T072)
    attempt = answer_submission_service.submit_answer(
        exercise.id, session.id, "SELECT ROW_NUMBER() OVER (ORDER BY id) FROM t;", confidence=70
    )

    # -- evaluation (T073)
    provider.set_response(
        EvaluatorResponse,
        EvaluatorResponse(
            correctness=0.85,
            reasoning=0.8,
            completeness=0.75,
            independence=0.7,
            transfer=0.6,
            misconceptions=["Forgets ORDER BY inside OVER()"],
            feedback="Mostly correct, double-check ordering.",
            recommended_action="review_transfer",
        ),
    )
    evaluation = await evaluator_service.evaluate(attempt.id)
    assert evaluation.correctness == 0.85

    # -- evidence (T074)
    created_evidence = evidence_creation_service.create_evidence(
        evaluation.id, activity_id=activity.id
    )
    assert [e.concept_id for e in created_evidence] == ["window_functions"]
    assert created_evidence[0].source_type.value == "exercise"

    # -- mastery update (T075)
    updated_concept = await mastery_update_service.update_mastery("window_functions", goal.id)
    assert updated_concept.mastery > 0

    # -- mistake update (T076)
    recorded_mistakes = mistake_update_service.record_from_evaluation(evaluation.id)
    assert [m.description for m in recorded_mistakes] == ["Forgets ORDER BY inside OVER()"]
    assert recorded_mistakes[0].concept_id == "window_functions"

    # -- review creation (T077)
    review = review_creation_service.schedule_review(
        "window_functions", goal.id, correctness=evaluation.correctness
    )
    assert review.status == ReviewStatus.SCHEDULED
    assert review.interval_days == 1.0  # first review for this concept

    # -- adaptive next activity, demonstrating the loop continues (T078)
    adaptive = adaptive_activity_service.select_next(
        session.id, just_completed_concept_id="window_functions"
    )
    assert adaptive.activity.status == ActivityStatus.ACTIVE
    assert adaptive.reason.breakdown  # explainable, not an opaque score


def _seed_diagnostic_session(engine: Engine, goal_id: str) -> tuple[str, str]:
    """Diagnostic runs before the main session exists, but Evidence still
    needs a real session/activity row to satisfy the schema's foreign
    keys -- a short-lived assessment-mode session serves that purpose."""
    with DbSession(engine) as db:
        db.add(
            SessionModel(
                id="session_diagnostic",
                goal_id=goal_id,
                mode="assessment",
                objective="Diagnostic",
                status="active",
                started_at=NOW.isoformat(),
                created_at=NOW.isoformat(),
            )
        )
        db.flush()
        db.add(
            ActivityModel(
                id="activity_diagnostic",
                session_id="session_diagnostic",
                type=ActivityType.ASSESSMENT.value,
                sequence=1,
                status="active",
                payload_json="{}",
                created_at=NOW.isoformat(),
            )
        )
        db.commit()
    return "session_diagnostic", "activity_diagnostic"
