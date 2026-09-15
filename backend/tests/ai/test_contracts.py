import pytest
from pydantic import ValidationError

from app.ai.adapters.mock import MockProvider
from app.ai.contracts import (
    CalibrationBreakdown,
    CuratorOperation,
    CuratorResponse,
    DiagnosticianResponse,
    DiagnosticItem,
    EvaluatorResponse,
    ExerciseGeneratorResponse,
    HighLeverageConcept,
    PlannerResponse,
    ProgressResponse,
    TutorResponse,
)
from app.ai.protocol import AIRequest
from app.domain.enums import ExerciseType, ProposalOperation


def test_planner_response_defaults_are_empty_lists() -> None:
    response = PlannerResponse()
    assert response.high_leverage_concepts == []
    assert response.deferred_topics == []


def test_planner_response_with_high_leverage_concepts() -> None:
    response = PlannerResponse(
        high_leverage_concepts=[
            HighLeverageConcept(
                concept_id="concept_1", title="Window Functions", importance=5, reason="core skill"
            )
        ]
    )
    assert response.high_leverage_concepts[0].importance == 5


def test_diagnostician_response_validates_evidence_type() -> None:
    with pytest.raises(ValidationError):
        DiagnosticItem(
            concept_id="c1", evidence_type="not_a_real_type", question="?", difficulty=1
        )


def test_diagnostician_response_accepts_valid_items() -> None:
    response = DiagnosticianResponse(
        items=[
            DiagnosticItem(concept_id="c1", evidence_type="recall", question="?", difficulty=2)
        ]
    )
    assert response.items[0].evidence_type == "recall"


def test_tutor_response_validates_mode() -> None:
    with pytest.raises(ValidationError):
        TutorResponse(mode="not_a_mode", content="...")


def test_tutor_response_optional_fields_default_none() -> None:
    response = TutorResponse(mode="explain", content="Window functions...")
    assert response.check_for_understanding is None
    assert response.next_activity is None


def test_exercise_generator_response_uses_domain_exercise_type() -> None:
    response = ExerciseGeneratorResponse(
        type=ExerciseType.SQL, difficulty=3, prompt="...", solution="..."
    )
    assert response.type == ExerciseType.SQL


def test_evaluator_response_rejects_out_of_range_scores() -> None:
    with pytest.raises(ValidationError):
        EvaluatorResponse(
            correctness=1.5,
            reasoning=0.5,
            completeness=0.5,
            independence=0.5,
            transfer=0.5,
            feedback="...",
            recommended_action="...",
        )


def test_evaluator_response_accepts_boundary_scores() -> None:
    response = EvaluatorResponse(
        correctness=0.0,
        reasoning=1.0,
        completeness=0.5,
        independence=0.5,
        transfer=0.5,
        feedback="Good effort",
        recommended_action="practice_more",
    )
    assert response.correctness == 0.0
    assert response.reasoning == 1.0


def test_curator_response_operation_is_limited_enum() -> None:
    with pytest.raises(ValidationError):
        CuratorOperation(path="note.md", operation="delete_everything", content="x")


def test_curator_response_accepts_valid_operations() -> None:
    response = CuratorResponse(
        operations=[
            CuratorOperation(
                path="note.md",
                operation=ProposalOperation.REPLACE_MANAGED_SECTION,
                section="SUMMARY",
                content="New summary",
            )
        ]
    )
    assert response.operations[0].operation == ProposalOperation.REPLACE_MANAGED_SECTION


def test_progress_response_requires_calibration() -> None:
    with pytest.raises(ValidationError):
        ProgressResponse(progress_summary="Doing well")  # type: ignore[call-arg]


def test_progress_response_with_calibration() -> None:
    response = ProgressResponse(
        progress_summary="Doing well",
        calibration=CalibrationBreakdown(overconfidence=0.2, underconfidence=0.1),
    )
    assert response.calibration.overconfidence == 0.2


@pytest.mark.asyncio
async def test_mock_provider_can_serve_every_contract() -> None:
    """The provider abstraction (T017) works with any of these schemas."""
    provider = MockProvider()
    request = AIRequest(role="evaluator", prompt_version="evaluator.v1")

    evaluation = EvaluatorResponse(
        correctness=0.8,
        reasoning=0.7,
        completeness=0.9,
        independence=0.6,
        transfer=0.5,
        feedback="Solid",
        recommended_action="continue",
    )
    provider.set_response(EvaluatorResponse, evaluation)

    result = await provider.generate(request, EvaluatorResponse)
    assert result == evaluation
