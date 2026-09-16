import json

from sqlalchemy import Engine
from sqlalchemy.orm import Session as DbSession

from app.domain.entities import Evaluation
from app.persistence.models import EvaluationModel
from app.persistence.repositories._util import dt_to_str, str_to_dt


def _to_model(evaluation: Evaluation) -> EvaluationModel:
    return EvaluationModel(
        id=evaluation.id,
        attempt_id=evaluation.attempt_id,
        correctness=evaluation.correctness,
        reasoning=evaluation.reasoning,
        completeness=evaluation.completeness,
        independence=evaluation.independence,
        transfer=evaluation.transfer,
        feedback=evaluation.feedback,
        misconceptions_json=json.dumps(evaluation.misconceptions),
        recommended_action=evaluation.recommended_action,
        provider=evaluation.provider,
        model=evaluation.model,
        prompt_version=evaluation.prompt_version,
        created_at=dt_to_str(evaluation.created_at),
    )


def _to_entity(model: EvaluationModel) -> Evaluation:
    return Evaluation(
        id=model.id,
        attempt_id=model.attempt_id,
        correctness=model.correctness,
        reasoning=model.reasoning,
        completeness=model.completeness,
        independence=model.independence,
        transfer=model.transfer,
        misconceptions=json.loads(model.misconceptions_json),
        feedback=model.feedback,
        recommended_action=model.recommended_action,
        provider=model.provider,  # type: ignore[arg-type]
        model=model.model,  # type: ignore[arg-type]
        prompt_version=model.prompt_version,  # type: ignore[arg-type]
        created_at=str_to_dt(model.created_at),  # type: ignore[arg-type]
    )


class SqlEvaluationRepository:
    """Implements app.domain.ports.EvaluationRepository against
    evaluations (T033 table, T073 port/adapter). Append-only -- see
    docs/AGENTS.md #23. No update/delete method.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, evaluation: Evaluation) -> None:
        with DbSession(self._engine) as db:
            db.add(_to_model(evaluation))
            db.commit()

    def get(self, evaluation_id: str) -> Evaluation | None:
        with DbSession(self._engine) as db:
            model = db.get(EvaluationModel, evaluation_id)
            return _to_entity(model) if model is not None else None
