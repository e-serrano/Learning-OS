"""Full canonical-loop end-to-end test (docs/TASKS.md T121,
docs/SPECS.md #1: "GOAL -> DIAGNOSE -> 80/20 -> ROADMAP -> LEARN ->
PRACTICE -> FEEDBACK -> ADAPT -> CONSOLIDATE -> REVIEW -> TRANSFER ->
PROJECT -> EVALUATE").

A backend `TestClient` integration test, not a Playwright browser test
(docs/TASKS.md T120's own infrastructure): every AI-dependent step here
needs a canned response from `MockProvider`, and `MockProvider.set_response()`
is only callable from Python, never through any HTTP endpoint -- a
browser-driven test could not get past the first AI call. Every route
touched below has its own service-level test already (T096-T119); this
test's job is only to prove the *whole* journey composes end to end
through the real HTTP surface, not to re-verify any single step's logic.

Real implementation order diverges from SPECS.md's textual
GOAL -> DIAGNOSE -> 80/20 -> ROADMAP sequence: `DiagnosticSessionService`
(T102) requires concepts already linked to the goal, and only
`RoadmapService.build_roadmap` (T068) creates and links them -- so
ROADMAP must run before DIAGNOSE can find anything to diagnose. This is
not a new decision; T102's own docstring already establishes it, and
`PlannerService.plan()` (T067) returning `roadmap_nodes`/`roadmap_edges`
alongside the 80/20 output means one `/roadmap/generate` call already
covers 80/20 + ROADMAP together.

CONSOLIDATE has no route at all: `CuratorService` (T080) and
`ProposalValidator` (T081) are fully built but never invoked from any
application flow or API route anywhere in the codebase (confirmed via
grep across app/). Rather than inventing new always-on production wiring
no task specifies, this test exercises the pipeline directly in Python
(propose -> validate_and_persist), then hands the resulting
ChangeProposal to the real `POST /vault/changes/{id}/apply` route for
the human-approval half of CONSOLIDATE that already exists (T097).
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import (
    CuratorOperation,
    CuratorResponse,
    DiagnosticianResponse,
    DiagnosticItem,
    EvaluatorResponse,
    ExerciseGeneratorResponse,
    HighLeverageConcept,
    PlannerResponse,
)
from app.ai.orchestrator import AIOrchestrator
from app.api.dependencies import (
    get_activity_content_service,
    get_adaptive_activity_service,
    get_answer_flow_service,
    get_apply_change_service,
    get_assessment_flow_service,
    get_assessment_session_service,
    get_change_proposal_repository,
    get_diagnostic_session_service,
    get_diff_approval_service,
    get_goal_service,
    get_next_activity_service,
    get_progress_service,
    get_project_flow_service,
    get_project_session_service,
    get_review_flow_service,
    get_roadmap_generation_service,
    get_roadmap_service,
    get_session_service,
    get_todays_reviews_service,
)
from app.domain.enums import ExerciseType, ProposalOperation
from app.main import app
from app.obsidian.change_proposal import ChangeProposalRepository
from app.obsidian.vault_resolver import VaultResolver
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
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
    SqlProjectRepository,
    SqlReviewRepository,
    SqlRoadmapRepository,
    SqlSessionRepository,
)
from app.services.activity_content_service import ActivityContentService
from app.services.activity_selector import ActivitySelector
from app.services.adaptive_activity_service import AdaptiveActivityService
from app.services.answer_flow_service import AnswerFlowService
from app.services.answer_submission_service import AnswerSubmissionService
from app.services.apply_change_service import ApplyChangeService
from app.services.assessment_completion_service import AssessmentCompletionService
from app.services.assessment_flow_service import AssessmentFlowService
from app.services.assessment_session_service import AssessmentSessionService
from app.services.context_builder import ContextBuilder
from app.services.curator_service import (
    DEFAULT_CONCEPT_NOTES_DIR,
    CuratorService,
    sanitize_concept_filename,
)
from app.services.diagnostic_service import DiagnosticService
from app.services.diagnostic_session_service import DiagnosticSessionService
from app.services.diff_approval_service import DiffApprovalService
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
from app.services.progress_service import ProgressService
from app.services.project_evaluation_service import ProjectEvaluationService
from app.services.project_flow_service import ProjectFlowService
from app.services.project_generation_service import ProjectGenerationService
from app.services.project_session_service import ProjectSessionService
from app.services.project_submission_service import ProjectSubmissionService
from app.services.project_task_service import ProjectTaskService
from app.services.proposal_validator import ProposalValidator
from app.services.retention_update_service import RetentionUpdateService
from app.services.review_completion_service import ReviewCompletionService
from app.services.review_creation_service import ReviewCreationService
from app.services.review_flow_service import ReviewFlowService
from app.services.review_scheduler import ReviewScheduler
from app.services.roadmap_generation_service import RoadmapGenerationService
from app.services.roadmap_service import RoadmapService
from app.services.session_service import SessionApplicationService
from app.services.todays_reviews_service import TodaysReviewsService
from app.services.transfer_assessment_service import TransferAssessmentService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class FakeClock:
    def now(self) -> datetime:
        return NOW


class SeqIdGenerator:
    """Deterministic, collision-free ids -- two independently-constructed
    `FakeIdGenerator`s both starting at 1 caused a real UNIQUE-constraint
    collision in T106's test suite; one shared counter avoids that here."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}

    def new_id(self, prefix: str) -> str:
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return f"{prefix}_{self._counters[prefix]}"


def _exercise_response(**overrides: object) -> ExerciseGeneratorResponse:
    defaults: dict[str, object] = dict(
        type=ExerciseType.SQL,
        difficulty=3,
        prompt="Rank each customer's orders by total using a window function.",
        success_criteria=["Uses a window function", "Handles ties correctly"],
        hints=["Consider PARTITION BY"],
        solution=(
            "SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY total DESC) "
            "FROM orders;"
        ),
        common_mistakes=["Forgetting ORDER BY inside OVER()"],
        transfer_variant="Apply the same ranking to a different table.",
    )
    defaults.update(overrides)
    return ExerciseGeneratorResponse(**defaults)  # type: ignore[arg-type]


def _evaluator_response(**overrides: object) -> EvaluatorResponse:
    defaults: dict[str, object] = dict(
        correctness=0.9,
        reasoning=0.85,
        completeness=0.85,
        independence=0.8,
        transfer=0.8,
        misconceptions=[],
        feedback="Solid use of the window function.",
        recommended_action="advance",
    )
    defaults.update(overrides)
    return EvaluatorResponse(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def vault(tmp_path: Path) -> VaultResolver:
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    return VaultResolver(str(vault_root))


@pytest.fixture
def client(engine: Engine, vault: VaultResolver) -> TestClient:
    provider = MockProvider()
    provider.set_response(
        PlannerResponse,
        PlannerResponse(
            high_leverage_concepts=[
                HighLeverageConcept(
                    concept_id="subqueries",
                    title="Subqueries",
                    importance=4,
                    reason="Foundation for window functions",
                ),
                HighLeverageConcept(
                    concept_id="window_functions",
                    title="Window Functions",
                    importance=5,
                    reason="High-leverage analytical tool",
                ),
            ],
            deferred_topics=["Recursive CTEs"],
            roadmap_nodes=[
                {"id": "subqueries", "title": "Subqueries", "importance": 4, "domain": "sql"},
                {
                    "id": "window_functions",
                    "title": "Window Functions",
                    "importance": 5,
                    "domain": "sql",
                },
            ],
            roadmap_edges=[
                {
                    "source": "subqueries",
                    "target": "window_functions",
                    "relation": "PREREQUISITE_OF",
                }
            ],
            diagnostic_focus=["subqueries", "window_functions"],
        ),
    )
    provider.set_response(
        DiagnosticianResponse,
        DiagnosticianResponse(
            items=[
                DiagnosticItem(
                    concept_id="subqueries",
                    evidence_type="recall",
                    question="What is a correlated subquery?",
                    difficulty=2,
                ),
                DiagnosticItem(
                    concept_id="window_functions",
                    evidence_type="recall",
                    question="What does OVER() do?",
                    difficulty=3,
                ),
            ]
        ),
    )
    provider.set_response(ExerciseGeneratorResponse, _exercise_response())
    provider.set_response(EvaluatorResponse, _evaluator_response())

    def _curator_response(request: object) -> CuratorResponse:
        # ActivitySelector (T064) picks whichever concept scores highest, so
        # which concept actually gets touched by the LEARN/PRACTICE answer
        # is not fixed in advance -- the curated path must match whatever
        # concept the request is actually about (ProposalValidator's
        # conventional-new-note-name check, T081/T139).
        concept_title = request.current_state["concept"]["title"]  # type: ignore[attr-defined]
        path = f"{DEFAULT_CONCEPT_NOTES_DIR}/{sanitize_concept_filename(concept_title)}.md"
        return CuratorResponse(
            operations=[
                CuratorOperation(
                    path=path,
                    operation=ProposalOperation.CREATE_FILE,
                    section=None,
                    content=f"# {concept_title}\n\nMastery notes from session evidence.\n",
                )
            ]
        )

    provider.set_response(CuratorResponse, _curator_response)
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")  # type: ignore[arg-type]

    clock = FakeClock()
    ids = SeqIdGenerator()

    goals = SqlGoalRepository(engine)
    concepts = SqlConceptRepository(engine)
    concept_relations = SqlConceptRelationRepository(engine)
    evidence = SqlEvidenceRepository(engine)
    mistakes = SqlMistakeRepository(engine)
    sessions = SqlSessionRepository(engine)
    activities = SqlActivityRepository(engine)
    exercises = SqlExerciseRepository(engine)
    exercise_attempts = SqlExerciseAttemptRepository(engine)
    evaluations = SqlEvaluationRepository(engine)
    reviews = SqlReviewRepository(engine)
    projects = SqlProjectRepository(engine)
    roadmaps = SqlRoadmapRepository(engine)
    change_proposals = ChangeProposalRepository(engine)

    context_builder = ContextBuilder(
        goals=goals,
        concepts=concepts,
        concept_relations=concept_relations,
        evidence=evidence,
        mistakes=mistakes,
    )

    goal_service = GoalApplicationService(goals, clock, ids)

    planner_service = PlannerService(goals, concepts, orchestrator)
    roadmap_service = RoadmapService(goals, concepts, concept_relations, roadmaps, clock, ids)
    roadmap_generation_service = RoadmapGenerationService(planner_service, roadmap_service)

    diagnostic_service = DiagnosticService(
        goals=goals,
        evidence=evidence,
        context_builder=context_builder,
        orchestrator=orchestrator,
        clock=clock,
        ids=ids,
    )
    diagnostic_session_service = DiagnosticSessionService(
        goals=goals,
        concepts=concepts,
        sessions=sessions,
        activities=activities,
        diagnostic=diagnostic_service,
        clock=clock,
        ids=ids,
    )

    session_service = SessionApplicationService(goals, sessions, clock, ids)
    activity_selector = ActivitySelector(concepts, concept_relations, mistakes, evidence, clock)
    next_activity_service = NextActivityService(sessions, activities, activity_selector, ids)
    adaptive_activity_service = AdaptiveActivityService(
        sessions, activities, activity_selector, ids
    )
    exercise_generator_service = ExerciseGeneratorService(
        goals=goals,
        context_builder=context_builder,
        exercises=exercises,
        orchestrator=orchestrator,
        clock=clock,
        ids=ids,
    )
    activity_content_service = ActivityContentService(activities, exercise_generator_service)
    answer_submission_service = AnswerSubmissionService(
        exercises, sessions, exercise_attempts, clock, ids
    )
    evaluator_service = EvaluatorService(
        exercise_attempts, exercises, evaluations, orchestrator, clock, ids
    )
    evidence_creation_service = EvidenceCreationService(
        evaluations, exercise_attempts, exercises, evidence, clock, ids
    )
    mistake_tracker = MistakeTracker(mistakes, clock, ids)
    mistake_update_service = MistakeUpdateService(
        evaluations, exercise_attempts, exercises, mistake_tracker
    )
    mastery_engine = MasteryEngine(evidence)
    mastery_update_service = MasteryUpdateService(concepts, mastery_engine)
    review_scheduler = ReviewScheduler(clock, ids)
    review_creation_service = ReviewCreationService(reviews, review_scheduler)
    answer_flow_service = AnswerFlowService(
        sessions=sessions,
        activities=activities,
        answer_submission=answer_submission_service,
        evaluator=evaluator_service,
        evidence_creation=evidence_creation_service,
        mistake_update=mistake_update_service,
        mastery_update=mastery_update_service,
        review_creation=review_creation_service,
        adaptive_activity=adaptive_activity_service,
        activity_content=activity_content_service,
    )

    todays_reviews_service = TodaysReviewsService(reviews, clock)
    retention_update_service = RetentionUpdateService(concepts, evidence)
    review_completion_service = ReviewCompletionService(
        reviews, evidence, review_creation_service, clock, ids
    )
    review_flow_service = ReviewFlowService(
        reviews=reviews,
        sessions=sessions,
        activities=activities,
        review_completion=review_completion_service,
        mastery_update=mastery_update_service,
        retention_update=retention_update_service,
        clock=clock,
        ids=ids,
    )

    transfer_assessment_service = TransferAssessmentService(
        goals=goals,
        context_builder=context_builder,
        exercises=exercises,
        orchestrator=orchestrator,
        clock=clock,
        ids=ids,
    )
    assessment_session_service = AssessmentSessionService(
        sessions=sessions,
        activities=activities,
        exercises=exercises,
        transfer_assessment=transfer_assessment_service,
        clock=clock,
        ids=ids,
    )
    assessment_completion_service = AssessmentCompletionService(
        answer_submission_service, evaluator_service, evidence_creation_service
    )
    assessment_flow_service = AssessmentFlowService(
        activities=activities,
        completion=assessment_completion_service,
        mastery_update=mastery_update_service,
        review_creation=review_creation_service,
    )

    project_generation_service = ProjectGenerationService(
        goals=goals,
        context_builder=context_builder,
        projects=projects,
        orchestrator=orchestrator,
        clock=clock,
        ids=ids,
    )
    project_task_service = ProjectTaskService(
        projects=projects, sessions=sessions, activities=activities, clock=clock, ids=ids
    )
    project_session_service = ProjectSessionService(
        goals=goals,
        projects=projects,
        generation=project_generation_service,
        tasks=project_task_service,
    )
    project_submission_service = ProjectSubmissionService(
        projects, activities, evidence, clock, ids
    )
    project_evaluation_service = ProjectEvaluationService(
        projects, evidence, orchestrator, clock, ids
    )
    project_flow_service = ProjectFlowService(
        submission=project_submission_service,
        evaluation=project_evaluation_service,
        mastery_update=mastery_update_service,
        review_creation=review_creation_service,
    )

    progress_service = ProgressService(
        goals=goals, concepts=concepts, reviews=reviews, sessions=sessions, clock=clock
    )

    diff_approval_service = DiffApprovalService(change_proposals)
    apply_change_service = ApplyChangeService(engine, change_proposals, vault)

    app.dependency_overrides[get_goal_service] = lambda: goal_service
    app.dependency_overrides[get_roadmap_generation_service] = lambda: roadmap_generation_service
    app.dependency_overrides[get_roadmap_service] = lambda: roadmap_service
    app.dependency_overrides[get_diagnostic_session_service] = lambda: diagnostic_session_service
    app.dependency_overrides[get_session_service] = lambda: session_service
    app.dependency_overrides[get_next_activity_service] = lambda: next_activity_service
    app.dependency_overrides[get_adaptive_activity_service] = lambda: adaptive_activity_service
    app.dependency_overrides[get_activity_content_service] = lambda: activity_content_service
    app.dependency_overrides[get_answer_flow_service] = lambda: answer_flow_service
    app.dependency_overrides[get_todays_reviews_service] = lambda: todays_reviews_service
    app.dependency_overrides[get_review_flow_service] = lambda: review_flow_service
    app.dependency_overrides[get_assessment_session_service] = lambda: assessment_session_service
    app.dependency_overrides[get_assessment_flow_service] = lambda: assessment_flow_service
    app.dependency_overrides[get_change_proposal_repository] = lambda: change_proposals
    app.dependency_overrides[get_apply_change_service] = lambda: apply_change_service
    app.dependency_overrides[get_diff_approval_service] = lambda: diff_approval_service
    app.dependency_overrides[get_project_session_service] = lambda: project_session_service
    app.dependency_overrides[get_project_flow_service] = lambda: project_flow_service
    app.dependency_overrides[get_progress_service] = lambda: progress_service

    test_client = TestClient(app)
    test_client.curator_service = CuratorService(  # type: ignore[attr-defined]
        goals, concepts, evidence, vault, orchestrator
    )
    test_client.proposal_validator = ProposalValidator(change_proposals, vault, clock, ids)  # type: ignore[attr-defined]
    test_client.reviews_repo = reviews  # type: ignore[attr-defined]
    test_client.concepts_repo = concepts  # type: ignore[attr-defined]

    yield test_client
    app.dependency_overrides.clear()


async def test_full_canonical_loop(client: TestClient) -> None:
    # GOAL
    goal_response = client.post(
        "/api/v1/goals",
        json={
            "title": "Learn advanced SQL",
            "target_level": "professional",
            "domain": "sql",
            "available_minutes_per_week": 300,
        },
    )
    assert goal_response.status_code == 201
    goal_id = goal_response.json()["id"]

    # 80/20 + ROADMAP (one call -- PlannerService returns both, see module docstring)
    roadmap_response = client.post(f"/api/v1/goals/{goal_id}/roadmap/generate")
    assert roadmap_response.status_code == 200
    roadmap_body = roadmap_response.json()
    node_ids = {node["id"] for node in roadmap_body["nodes"]}
    assert node_ids == {"subqueries", "window_functions"}

    # DIAGNOSE
    diagnostic_response = client.post(f"/api/v1/goals/{goal_id}/diagnostic/start")
    assert diagnostic_response.status_code == 200
    diagnostic_body = diagnostic_response.json()
    assert len(diagnostic_body["items"]) == 2

    # LEARN / PRACTICE: create a guided session and fetch the first activity
    session_response = client.post(
        f"/api/v1/goals/{goal_id}/sessions", json={"mode": "guided", "duration_minutes": 30}
    )
    assert session_response.status_code == 200
    session_id = session_response.json()["id"]

    next_response = client.post(f"/api/v1/sessions/{session_id}/next")
    assert next_response.status_code == 200
    activity_id = next_response.json()["activity_id"]

    # FEEDBACK / ADAPT: submit an answer, which grades it, updates mastery,
    # schedules a review, and adaptively selects the next activity.
    answer_response = client.post(
        f"/api/v1/sessions/{session_id}/activities/{activity_id}/answer",
        json={"answer": "Use ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)", "confidence": 80},
    )
    assert answer_response.status_code == 200
    answer_body = answer_response.json()
    assert len(answer_body["knowledge_updates"]) == 1
    touched_concept_id = answer_body["knowledge_updates"][0]["concept_id"]
    assert touched_concept_id in {"subqueries", "window_functions"}
    assert answer_body["knowledge_updates"][0]["mastery"] > 0

    # CONSOLIDATE: curator proposes an update to the touched concept's note,
    # the validator turns it into a persisted ChangeProposal (T080/T081 --
    # never wired into any route, so exercised directly here), and the
    # existing apply route performs the human-approval half.
    concept = client.concepts_repo.get(touched_concept_id)  # type: ignore[attr-defined]
    assert concept is not None
    operations = await client.curator_service.propose(  # type: ignore[attr-defined]
        goal_id, touched_concept_id, session_outcome="Answered correctly"
    )
    validation = client.proposal_validator.validate_and_persist(operations, concept)  # type: ignore[attr-defined]
    assert len(validation.accepted) == 1
    assert validation.rejected == []
    proposal_id = validation.accepted[0].id

    apply_response = client.post(f"/api/v1/vault/changes/{proposal_id}/apply")
    assert apply_response.status_code == 200
    assert apply_response.json()["status"] == "applied"

    changes_response = client.get("/api/v1/vault/changes")
    assert changes_response.status_code == 200
    assert changes_response.json()["changes"] == []  # no longer pending -- it was applied

    # REVIEW: complete the review the answer step scheduled.
    due_reviews = client.reviews_repo.list_by_concept(touched_concept_id)  # type: ignore[attr-defined]
    assert len(due_reviews) == 1
    review_id = due_reviews[0].id

    review_response = client.post(
        f"/api/v1/reviews/{review_id}/complete",
        json={"answer": "Recalled correctly", "confidence": 85},
    )
    assert review_response.status_code == 200
    assert review_response.json()["completed_review"]["status"] == "completed"

    # TRANSFER: create, answer, and complete a transfer assessment.
    assessment_response = client.post(
        f"/api/v1/goals/{goal_id}/assessments", json={"concept_id": "window_functions"}
    )
    assert assessment_response.status_code == 201
    assessment_id = assessment_response.json()["assessment_id"]

    assessment_answer_response = client.post(
        f"/api/v1/assessments/{assessment_id}/answer",
        json={"answer": "Applied the window function to a new dataset.", "confidence": 80},
    )
    assert assessment_answer_response.status_code == 200
    assessment_answer_body = assessment_answer_response.json()
    assert assessment_answer_body["transfer_demonstrated"] is True
    assert assessment_answer_body["independence_demonstrated"] is True

    assessment_complete_response = client.post(f"/api/v1/assessments/{assessment_id}/complete")
    assert assessment_complete_response.status_code == 200
    assert assessment_complete_response.json()["status"] == "completed"

    # PROJECT: create a project spanning both concepts, submit every task.
    project_response = client.post(
        f"/api/v1/goals/{goal_id}/projects",
        json={"concept_ids": ["subqueries", "window_functions"]},
    )
    assert project_response.status_code == 201
    project_body = project_response.json()
    project_id = project_body["project"]["id"]
    task_ids = [task["task_id"] for task in project_body["tasks"]]
    assert len(task_ids) == 2

    for task_id in task_ids:
        submit_response = client.post(
            f"/api/v1/projects/{project_id}/tasks/{task_id}/submit",
            json={"deliverable": "https://github.com/example/sql-project"},
        )
        assert submit_response.status_code == 200
        assert submit_response.json()["task_status"] == "completed"

    # EVALUATE
    progress_response = client.get(f"/api/v1/goals/{goal_id}/progress")
    assert progress_response.status_code == 200
    progress_body = progress_response.json()
    assert progress_body["concepts_total"] == 2
    assert progress_body["mastery"] > 0
    assert progress_body["mastered"] + progress_body["weak"] <= progress_body["concepts_total"]
