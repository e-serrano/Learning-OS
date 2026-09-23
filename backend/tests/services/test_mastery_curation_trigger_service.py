from datetime import UTC, datetime

import pytest

from app.ai.contracts import CuratorOperation
from app.ai.errors import AIInvalidOutputError, AIProviderUnavailableError
from app.domain.entities import Concept
from app.domain.enums import ConceptStatus, ProposalOperation
from app.obsidian.change_proposal import ChangeProposal, ProposalStatus
from app.services.mastery_curation_trigger_service import MasteryCurationTriggerService
from app.services.proposal_validator import RejectedOperation, ValidationResult

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _concept(**overrides: object) -> Concept:
    defaults: dict[str, object] = dict(
        id="concept_1",
        title="Window Functions",
        domain="sql",
        status=ConceptStatus.MASTERED,
        mastery=4.5,
        confidence=90,
        importance=3,
        retention=85,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    return Concept(**defaults)  # type: ignore[arg-type]


def _operation() -> CuratorOperation:
    return CuratorOperation(
        path="03_Knowledge/Concepts/Window Functions.md",
        operation=ProposalOperation.CREATE_FILE,
        section=None,
        content="# Window Functions\n\nSummary.\n",
    )


def _proposal() -> ChangeProposal:
    return ChangeProposal(
        id="proposal_1",
        path="03_Knowledge/Concepts/Window Functions.md",
        operation=ProposalOperation.CREATE_FILE,
        content="# Window Functions\n\nSummary.\n",
        status=ProposalStatus.PENDING,
        created_at=NOW,
        updated_at=NOW,
    )


class FakeCuratorService:
    def __init__(
        self, operations: list[CuratorOperation] | None = None, error: Exception | None = None
    ) -> None:
        self._operations = operations if operations is not None else [_operation()]
        self._error = error
        self.calls: list[tuple[str, str]] = []

    async def propose(
        self, goal_id: str, concept_id: str, session_outcome: str | None = None
    ) -> list[CuratorOperation]:
        self.calls.append((goal_id, concept_id))
        if self._error is not None:
            raise self._error
        return self._operations


class FakeProposalValidator:
    def __init__(self, result: ValidationResult | None = None) -> None:
        self._result = result
        self.calls: list[tuple[list[CuratorOperation], Concept]] = []

    def validate_and_persist(
        self, operations: list[CuratorOperation], concept: Concept
    ) -> ValidationResult:
        self.calls.append((operations, concept))
        if self._result is not None:
            return self._result
        return ValidationResult(accepted=[_proposal()], rejected=[])


@pytest.mark.asyncio
async def test_fires_on_transition_into_mastered_and_returns_the_accepted_proposal() -> None:
    curator = FakeCuratorService()
    validator = FakeProposalValidator()
    trigger = MasteryCurationTriggerService(curator, validator)  # type: ignore[arg-type]
    updated = _concept(status=ConceptStatus.MASTERED)

    result = await trigger.trigger_if_newly_mastered("goal_1", ConceptStatus.STRONG, updated)

    assert result is not None
    assert result.id == "proposal_1"
    assert curator.calls == [("goal_1", "concept_1")]
    assert len(validator.calls) == 1


@pytest.mark.asyncio
async def test_does_not_fire_when_already_mastered_before() -> None:
    curator = FakeCuratorService()
    validator = FakeProposalValidator()
    trigger = MasteryCurationTriggerService(curator, validator)  # type: ignore[arg-type]
    updated = _concept(status=ConceptStatus.MASTERED)

    result = await trigger.trigger_if_newly_mastered("goal_1", ConceptStatus.MASTERED, updated)

    assert result is None
    assert curator.calls == []
    assert validator.calls == []


@pytest.mark.asyncio
async def test_does_not_fire_when_the_new_status_is_not_mastered() -> None:
    curator = FakeCuratorService()
    validator = FakeProposalValidator()
    trigger = MasteryCurationTriggerService(curator, validator)  # type: ignore[arg-type]
    updated = _concept(status=ConceptStatus.STRONG)

    result = await trigger.trigger_if_newly_mastered("goal_1", ConceptStatus.WEAK, updated)

    assert result is None
    assert curator.calls == []
    assert validator.calls == []


@pytest.mark.asyncio
async def test_refires_after_dropping_out_of_mastered_and_returning() -> None:
    curator = FakeCuratorService()
    validator = FakeProposalValidator()
    trigger = MasteryCurationTriggerService(curator, validator)  # type: ignore[arg-type]
    updated = _concept(status=ConceptStatus.MASTERED)

    result = await trigger.trigger_if_newly_mastered("goal_1", ConceptStatus.USABLE, updated)

    assert result is not None
    assert len(curator.calls) == 1


@pytest.mark.asyncio
async def test_swallows_ai_invalid_output_error() -> None:
    curator = FakeCuratorService(error=AIInvalidOutputError("bad output"))
    validator = FakeProposalValidator()
    trigger = MasteryCurationTriggerService(curator, validator)  # type: ignore[arg-type]
    updated = _concept(status=ConceptStatus.MASTERED)

    result = await trigger.trigger_if_newly_mastered("goal_1", ConceptStatus.STRONG, updated)

    assert result is None
    assert validator.calls == []


@pytest.mark.asyncio
async def test_swallows_ai_provider_unavailable_error() -> None:
    curator = FakeCuratorService(error=AIProviderUnavailableError("no provider"))
    validator = FakeProposalValidator()
    trigger = MasteryCurationTriggerService(curator, validator)  # type: ignore[arg-type]
    updated = _concept(status=ConceptStatus.MASTERED)

    result = await trigger.trigger_if_newly_mastered("goal_1", ConceptStatus.STRONG, updated)

    assert result is None


@pytest.mark.asyncio
async def test_returns_none_when_the_validator_rejects_every_operation() -> None:
    curator = FakeCuratorService()
    rejected_result = ValidationResult(
        accepted=[],
        rejected=[
            RejectedOperation(
                operation=_operation(), reason="path does not belong to the curated concept"
            )
        ],
    )
    validator = FakeProposalValidator(result=rejected_result)
    trigger = MasteryCurationTriggerService(curator, validator)  # type: ignore[arg-type]
    updated = _concept(status=ConceptStatus.MASTERED)

    result = await trigger.trigger_if_newly_mastered("goal_1", ConceptStatus.STRONG, updated)

    assert result is None
