import json

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as DbSession

from app.domain.entities import Evidence
from app.persistence.models import EvidenceModel
from app.persistence.repositories._util import dt_to_str, str_to_dt


def _to_model(evidence: Evidence) -> EvidenceModel:
    return EvidenceModel(
        id=evidence.id,
        goal_id=evidence.goal_id,
        concept_id=evidence.concept_id,
        session_id=evidence.session_id,
        activity_id=evidence.activity_id,
        source_type=evidence.source_type.value,
        difficulty=evidence.difficulty,
        correctness=evidence.correctness,
        reasoning=evidence.reasoning,
        independence=evidence.independence,
        transfer=evidence.transfer,
        confidence=evidence.confidence,
        timestamp=dt_to_str(evidence.timestamp),
        metadata_json=json.dumps({"metadata": evidence.metadata, "skill_ids": evidence.skill_ids}),
    )


def _to_entity(model: EvidenceModel) -> Evidence:
    extra = json.loads(model.metadata_json)
    return Evidence(
        id=model.id,
        goal_id=model.goal_id,
        concept_id=model.concept_id,
        session_id=model.session_id,
        activity_id=model.activity_id,
        source_type=model.source_type,  # type: ignore[arg-type]
        difficulty=model.difficulty,
        correctness=model.correctness,
        reasoning=model.reasoning,
        independence=model.independence,
        transfer=model.transfer,
        confidence=model.confidence,
        timestamp=str_to_dt(model.timestamp),  # type: ignore[arg-type]
        metadata=extra.get("metadata", {}),
        skill_ids=extra.get("skill_ids", []),
    )


class SqlEvidenceRepository:
    """Implements app.domain.ports.EvidenceRepository against evidence (T033).

    Append-only: no update/delete method, matching docs/AGENTS.md #8.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, evidence: Evidence) -> None:
        with DbSession(self._engine) as db:
            db.add(_to_model(evidence))
            db.commit()

    def list_by_concept(self, concept_id: str) -> list[Evidence]:
        with DbSession(self._engine) as db:
            stmt = select(EvidenceModel).where(EvidenceModel.concept_id == concept_id)
            return [_to_entity(m) for m in db.scalars(stmt)]

    def list_by_goal(self, goal_id: str) -> list[Evidence]:
        with DbSession(self._engine) as db:
            stmt = select(EvidenceModel).where(EvidenceModel.goal_id == goal_id)
            return [_to_entity(m) for m in db.scalars(stmt)]
