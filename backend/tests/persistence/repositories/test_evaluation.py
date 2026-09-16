from datetime import UTC, datetime

from sqlalchemy import Engine
from sqlalchemy.orm import Session as DbSession

from app.domain.entities import Evaluation
from app.domain.ports import EvaluationRepository
from app.persistence.models import ExerciseAttemptModel, ExerciseModel
from app.persistence.repositories import SqlEvaluationRepository

NOW = datetime.now(UTC)


def _accepts_port(port: EvaluationRepository) -> EvaluationRepository:
    return port


def _seed_attempt(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    with DbSession(engine) as db:
        db.add(
            ExerciseModel(
                id="exercise_1",
                type="sql",
                difficulty=2,
                goal_id=seeded["goal_id"],
                prompt="Write a query",
                solution="SELECT 1",
                metadata_json="{}",
                created_at=NOW.isoformat(),
            )
        )
        db.flush()
        db.add(
            ExerciseAttemptModel(
                id="attempt_1",
                exercise_id="exercise_1",
                session_id=seeded["session_id"],
                answer="SELECT 1;",
                confidence=72,
                submitted_at=NOW.isoformat(),
            )
        )
        db.commit()


def _make_evaluation(**overrides: object) -> Evaluation:
    defaults: dict[str, object] = dict(
        id="evaluation_1",
        attempt_id="attempt_1",
        correctness=0.9,
        reasoning=0.8,
        completeness=0.7,
        independence=0.6,
        transfer=0.5,
        misconceptions=["Confuses ROW_NUMBER and RANK"],
        feedback="Good, but check tie handling.",
        recommended_action="review_transfer",
        provider="mock",
        model="mock-1",
        prompt_version="evaluator.v1",
        created_at=NOW,
    )
    defaults.update(overrides)
    return Evaluation(**defaults)  # type: ignore[arg-type]


def test_satisfies_evaluation_repository_port(engine: Engine) -> None:
    _accepts_port(SqlEvaluationRepository(engine))


def test_add_then_get_roundtrips(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    _seed_attempt(engine, seeded)
    repo = SqlEvaluationRepository(engine)
    evaluation = _make_evaluation()
    repo.add(evaluation)

    assert repo.get("evaluation_1") == evaluation


def test_get_missing_returns_none(engine: Engine) -> None:
    assert SqlEvaluationRepository(engine).get("missing") is None


def test_no_update_or_delete_method(engine: Engine) -> None:
    repo = SqlEvaluationRepository(engine)
    assert not hasattr(repo, "update")
    assert not hasattr(repo, "delete")
