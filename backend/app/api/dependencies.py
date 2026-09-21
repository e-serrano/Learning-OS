import uuid
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import Engine

from app.ai.orchestrator import AIOrchestrator
from app.ai.provider_factory import (
    MissingBaseUrlError,
    MissingCredentialError,
    NoDefaultProviderError,
    build_default_provider,
)
from app.config import ConfigStore, CredentialStore, Settings
from app.obsidian.change_proposal import ChangeProposalRepository
from app.obsidian.vault_resolver import VaultResolver, VaultUnavailableError
from app.persistence.engine import create_sqlite_engine
from app.persistence.repositories.activity import SqlActivityRepository
from app.persistence.repositories.concept import SqlConceptRepository
from app.persistence.repositories.concept_relation import SqlConceptRelationRepository
from app.persistence.repositories.evaluation import SqlEvaluationRepository
from app.persistence.repositories.evidence import SqlEvidenceRepository
from app.persistence.repositories.exercise import SqlExerciseRepository
from app.persistence.repositories.exercise_attempt import SqlExerciseAttemptRepository
from app.persistence.repositories.goal import SqlGoalRepository
from app.persistence.repositories.mistake import SqlMistakeRepository
from app.persistence.repositories.review import SqlReviewRepository
from app.persistence.repositories.roadmap import SqlRoadmapRepository
from app.persistence.repositories.session import SqlSessionRepository
from app.services.activity_content_service import ActivityContentService
from app.services.activity_selector import ActivitySelector
from app.services.adaptive_activity_service import AdaptiveActivityService
from app.services.answer_flow_service import AnswerFlowService
from app.services.answer_submission_service import AnswerSubmissionService
from app.services.apply_change_service import ApplyChangeService
from app.services.assessment_completion_service import AssessmentCompletionService
from app.services.assessment_session_service import AssessmentSessionService
from app.services.context_builder import ContextBuilder
from app.services.diagnostic_service import DiagnosticService
from app.services.diagnostic_session_service import DiagnosticSessionService
from app.services.diff_approval_service import DiffApprovalService
from app.services.evaluator_service import EvaluatorService
from app.services.evidence_creation_service import EvidenceCreationService
from app.services.exercise_generator_service import ExerciseGeneratorService
from app.services.goal_service import GoalApplicationService
from app.services.knowledge_explorer_service import KnowledgeExplorerService
from app.services.mastery_engine import MasteryEngine
from app.services.mastery_update_service import MasteryUpdateService
from app.services.mistake_tracker import MistakeTracker
from app.services.mistake_update_service import MistakeUpdateService
from app.services.next_activity_service import NextActivityService
from app.services.planner_service import PlannerService
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
from app.services.vault_scan_service import VaultScanService


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class UuidIdGenerator:
    def new_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_config_store() -> ConfigStore:
    return ConfigStore(get_settings().db_path)


def get_credential_store() -> CredentialStore:
    return CredentialStore()


@lru_cache
def get_engine() -> Engine:
    return create_sqlite_engine(get_settings().db_path)


def get_clock() -> SystemClock:
    return SystemClock()


def get_id_generator() -> UuidIdGenerator:
    return UuidIdGenerator()


def get_goal_repository() -> SqlGoalRepository:
    return SqlGoalRepository(get_engine())


def get_goal_service() -> GoalApplicationService:
    return GoalApplicationService(get_goal_repository(), get_clock(), get_id_generator())


def get_vault_resolver(store: Annotated[ConfigStore, Depends(get_config_store)]) -> VaultResolver:
    """Raises HTTPException directly (rather than a plain error) -- FastAPI
    resolves dependencies before the route body runs, so a route-level
    try/except can never see an exception raised here (docs/TASKS.md T097).

    Takes `store` through `Depends()` rather than calling
    `get_config_store()` directly so `app.dependency_overrides` can
    actually reach it in tests -- a plain internal call bypasses
    FastAPI's override resolution entirely."""
    config = store.load()
    if config.vault_path is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "VAULT_UNAVAILABLE",
                    "message": "Vault is not configured",
                    "details": {},
                }
            },
        )
    try:
        return VaultResolver(config.vault_path)
    except VaultUnavailableError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VAULT_UNAVAILABLE", "message": str(exc), "details": {}}},
        ) from exc


def get_change_proposal_repository() -> ChangeProposalRepository:
    return ChangeProposalRepository(get_engine())


def get_vault_scan_service(
    vault: Annotated[VaultResolver, Depends(get_vault_resolver)],
) -> VaultScanService:
    return VaultScanService(get_engine(), vault)


def get_apply_change_service(
    vault: Annotated[VaultResolver, Depends(get_vault_resolver)],
) -> ApplyChangeService:
    return ApplyChangeService(get_engine(), get_change_proposal_repository(), vault)


def get_diff_approval_service() -> DiffApprovalService:
    return DiffApprovalService(get_change_proposal_repository())


def get_concept_repository() -> SqlConceptRepository:
    return SqlConceptRepository(get_engine())


def get_concept_relation_repository() -> SqlConceptRelationRepository:
    return SqlConceptRelationRepository(get_engine())


def get_knowledge_explorer_service() -> KnowledgeExplorerService:
    return KnowledgeExplorerService(
        get_goal_repository(), get_concept_repository(), get_concept_relation_repository()
    )


def get_ai_orchestrator(
    store: Annotated[ConfigStore, Depends(get_config_store)],
) -> AIOrchestrator:
    """Builds the orchestrator around the user's configured default AI
    provider (docs/TASKS.md T101 -- the first route to call the AI
    orchestrator over HTTP). Raises HTTPException directly for the same
    reason `get_vault_resolver` does (docs/TASKS.md T097)."""
    config = store.load()
    try:
        provider, provider_name, model = build_default_provider(
            config.ai_providers, get_credential_store()
        )
    except (NoDefaultProviderError, MissingCredentialError, MissingBaseUrlError) as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "AI_UNAVAILABLE", "message": str(exc), "details": {}}},
        ) from exc
    return AIOrchestrator(get_engine(), provider, provider_name=provider_name, model=model)


def get_roadmap_repository() -> SqlRoadmapRepository:
    return SqlRoadmapRepository(get_engine())


def get_planner_service(
    orchestrator: Annotated[AIOrchestrator, Depends(get_ai_orchestrator)],
) -> PlannerService:
    return PlannerService(get_goal_repository(), get_concept_repository(), orchestrator)


def get_roadmap_service() -> RoadmapService:
    return RoadmapService(
        goals=get_goal_repository(),
        concepts=get_concept_repository(),
        concept_relations=get_concept_relation_repository(),
        roadmaps=get_roadmap_repository(),
        clock=get_clock(),
        ids=get_id_generator(),
    )


def get_roadmap_generation_service(
    planner: Annotated[PlannerService, Depends(get_planner_service)],
    roadmaps: Annotated[RoadmapService, Depends(get_roadmap_service)],
) -> RoadmapGenerationService:
    return RoadmapGenerationService(planner, roadmaps)


def get_evidence_repository() -> SqlEvidenceRepository:
    return SqlEvidenceRepository(get_engine())


def get_mistake_repository() -> SqlMistakeRepository:
    return SqlMistakeRepository(get_engine())


def get_session_repository() -> SqlSessionRepository:
    return SqlSessionRepository(get_engine())


def get_activity_repository() -> SqlActivityRepository:
    return SqlActivityRepository(get_engine())


def get_context_builder() -> ContextBuilder:
    return ContextBuilder(
        goals=get_goal_repository(),
        concepts=get_concept_repository(),
        concept_relations=get_concept_relation_repository(),
        evidence=get_evidence_repository(),
        mistakes=get_mistake_repository(),
    )


def get_diagnostic_service(
    orchestrator: Annotated[AIOrchestrator, Depends(get_ai_orchestrator)],
) -> DiagnosticService:
    return DiagnosticService(
        goals=get_goal_repository(),
        evidence=get_evidence_repository(),
        context_builder=get_context_builder(),
        orchestrator=orchestrator,
        clock=get_clock(),
        ids=get_id_generator(),
    )


def get_diagnostic_session_service(
    diagnostic: Annotated[DiagnosticService, Depends(get_diagnostic_service)],
) -> DiagnosticSessionService:
    return DiagnosticSessionService(
        goals=get_goal_repository(),
        concepts=get_concept_repository(),
        sessions=get_session_repository(),
        activities=get_activity_repository(),
        diagnostic=diagnostic,
        clock=get_clock(),
        ids=get_id_generator(),
    )


def get_session_service() -> SessionApplicationService:
    return SessionApplicationService(
        get_goal_repository(), get_session_repository(), get_clock(), get_id_generator()
    )


def get_activity_selector() -> ActivitySelector:
    return ActivitySelector(
        get_concept_repository(),
        get_concept_relation_repository(),
        get_mistake_repository(),
        get_evidence_repository(),
        get_clock(),
    )


def get_next_activity_service(
    activity_selector: Annotated[ActivitySelector, Depends(get_activity_selector)],
) -> NextActivityService:
    return NextActivityService(
        get_session_repository(), get_activity_repository(), activity_selector, get_id_generator()
    )


def get_adaptive_activity_service(
    activity_selector: Annotated[ActivitySelector, Depends(get_activity_selector)],
) -> AdaptiveActivityService:
    return AdaptiveActivityService(
        get_session_repository(), get_activity_repository(), activity_selector, get_id_generator()
    )


def get_exercise_repository() -> SqlExerciseRepository:
    return SqlExerciseRepository(get_engine())


def get_exercise_attempt_repository() -> SqlExerciseAttemptRepository:
    return SqlExerciseAttemptRepository(get_engine())


def get_evaluation_repository() -> SqlEvaluationRepository:
    return SqlEvaluationRepository(get_engine())


def get_review_repository() -> SqlReviewRepository:
    return SqlReviewRepository(get_engine())


def get_exercise_generator_service(
    orchestrator: Annotated[AIOrchestrator, Depends(get_ai_orchestrator)],
) -> ExerciseGeneratorService:
    return ExerciseGeneratorService(
        goals=get_goal_repository(),
        context_builder=get_context_builder(),
        exercises=get_exercise_repository(),
        orchestrator=orchestrator,
        clock=get_clock(),
        ids=get_id_generator(),
    )


def get_transfer_assessment_service(
    orchestrator: Annotated[AIOrchestrator, Depends(get_ai_orchestrator)],
) -> TransferAssessmentService:
    return TransferAssessmentService(
        goals=get_goal_repository(),
        context_builder=get_context_builder(),
        exercises=get_exercise_repository(),
        orchestrator=orchestrator,
        clock=get_clock(),
        ids=get_id_generator(),
    )


def get_assessment_session_service(
    transfer_assessment: Annotated[
        TransferAssessmentService, Depends(get_transfer_assessment_service)
    ],
) -> AssessmentSessionService:
    return AssessmentSessionService(
        sessions=get_session_repository(),
        activities=get_activity_repository(),
        exercises=get_exercise_repository(),
        transfer_assessment=transfer_assessment,
        clock=get_clock(),
        ids=get_id_generator(),
    )


def get_activity_content_service(
    exercise_generator: Annotated[
        ExerciseGeneratorService, Depends(get_exercise_generator_service)
    ],
) -> ActivityContentService:
    return ActivityContentService(get_activity_repository(), exercise_generator)


def get_answer_submission_service() -> AnswerSubmissionService:
    return AnswerSubmissionService(
        get_exercise_repository(),
        get_session_repository(),
        get_exercise_attempt_repository(),
        get_clock(),
        get_id_generator(),
    )


def get_evaluator_service(
    orchestrator: Annotated[AIOrchestrator, Depends(get_ai_orchestrator)],
) -> EvaluatorService:
    return EvaluatorService(
        get_exercise_attempt_repository(),
        get_exercise_repository(),
        get_evaluation_repository(),
        orchestrator,
        get_clock(),
        get_id_generator(),
    )


def get_evidence_creation_service() -> EvidenceCreationService:
    return EvidenceCreationService(
        get_evaluation_repository(),
        get_exercise_attempt_repository(),
        get_exercise_repository(),
        get_evidence_repository(),
        get_clock(),
        get_id_generator(),
    )


def get_assessment_completion_service(
    answer_submission: Annotated[AnswerSubmissionService, Depends(get_answer_submission_service)],
    evaluator: Annotated[EvaluatorService, Depends(get_evaluator_service)],
    evidence_creation: Annotated[EvidenceCreationService, Depends(get_evidence_creation_service)],
) -> AssessmentCompletionService:
    return AssessmentCompletionService(answer_submission, evaluator, evidence_creation)


def get_mistake_tracker() -> MistakeTracker:
    return MistakeTracker(get_mistake_repository(), get_clock(), get_id_generator())


def get_mistake_update_service(
    mistake_tracker: Annotated[MistakeTracker, Depends(get_mistake_tracker)],
) -> MistakeUpdateService:
    return MistakeUpdateService(
        get_evaluation_repository(),
        get_exercise_attempt_repository(),
        get_exercise_repository(),
        mistake_tracker,
    )


def get_mastery_engine() -> MasteryEngine:
    return MasteryEngine(get_evidence_repository())


def get_mastery_update_service(
    mastery_engine: Annotated[MasteryEngine, Depends(get_mastery_engine)],
) -> MasteryUpdateService:
    return MasteryUpdateService(get_concept_repository(), mastery_engine)


def get_review_scheduler() -> ReviewScheduler:
    return ReviewScheduler(get_clock(), get_id_generator())


def get_review_creation_service(
    review_scheduler: Annotated[ReviewScheduler, Depends(get_review_scheduler)],
) -> ReviewCreationService:
    return ReviewCreationService(get_review_repository(), review_scheduler)


def get_answer_flow_service(
    answer_submission: Annotated[AnswerSubmissionService, Depends(get_answer_submission_service)],
    evaluator: Annotated[EvaluatorService, Depends(get_evaluator_service)],
    evidence_creation: Annotated[EvidenceCreationService, Depends(get_evidence_creation_service)],
    mistake_update: Annotated[MistakeUpdateService, Depends(get_mistake_update_service)],
    mastery_update: Annotated[MasteryUpdateService, Depends(get_mastery_update_service)],
    review_creation: Annotated[ReviewCreationService, Depends(get_review_creation_service)],
    adaptive_activity: Annotated[AdaptiveActivityService, Depends(get_adaptive_activity_service)],
    activity_content: Annotated[ActivityContentService, Depends(get_activity_content_service)],
) -> AnswerFlowService:
    return AnswerFlowService(
        sessions=get_session_repository(),
        activities=get_activity_repository(),
        answer_submission=answer_submission,
        evaluator=evaluator,
        evidence_creation=evidence_creation,
        mistake_update=mistake_update,
        mastery_update=mastery_update,
        review_creation=review_creation,
        adaptive_activity=adaptive_activity,
        activity_content=activity_content,
    )


def get_todays_reviews_service() -> TodaysReviewsService:
    return TodaysReviewsService(get_review_repository(), get_clock())


def get_review_completion_service(
    review_creation: Annotated[ReviewCreationService, Depends(get_review_creation_service)],
) -> ReviewCompletionService:
    return ReviewCompletionService(
        get_review_repository(),
        get_evidence_repository(),
        review_creation,
        get_clock(),
        get_id_generator(),
    )


def get_retention_update_service() -> RetentionUpdateService:
    return RetentionUpdateService(get_concept_repository(), get_evidence_repository())


def get_review_flow_service(
    review_completion: Annotated[ReviewCompletionService, Depends(get_review_completion_service)],
    mastery_update: Annotated[MasteryUpdateService, Depends(get_mastery_update_service)],
    retention_update: Annotated[RetentionUpdateService, Depends(get_retention_update_service)],
) -> ReviewFlowService:
    return ReviewFlowService(
        reviews=get_review_repository(),
        sessions=get_session_repository(),
        activities=get_activity_repository(),
        review_completion=review_completion,
        mastery_update=mastery_update,
        retention_update=retention_update,
        clock=get_clock(),
        ids=get_id_generator(),
    )
