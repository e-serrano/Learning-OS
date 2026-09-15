from datetime import UTC, datetime

from sqlalchemy import Engine

from app.domain.entities import Mistake
from app.domain.enums import MistakeSeverity, MistakeType
from app.domain.ports import MistakeRepository
from app.persistence.repositories import SqlMistakeRepository

NOW = datetime.now(UTC)


def _accepts_port(port: MistakeRepository) -> MistakeRepository:
    return port


def _make_mistake(seeded: dict, **overrides: object) -> Mistake:  # type: ignore[type-arg]
    defaults: dict[str, object] = dict(
        id="mistake_1",
        concept_id=seeded["concept_id"],
        goal_id=seeded["goal_id"],
        type=MistakeType.MISCONCEPTION,
        description="Confuses ROW_NUMBER and RANK",
        severity=MistakeSeverity.MEDIUM,
        occurrences=1,
        first_seen=NOW,
        last_seen=NOW,
    )
    defaults.update(overrides)
    return Mistake(**defaults)  # type: ignore[arg-type]


def test_satisfies_mistake_repository_port(engine: Engine) -> None:
    _accepts_port(SqlMistakeRepository(engine))


def test_add_then_list_by_concept_roundtrips(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlMistakeRepository(engine)
    mistake = _make_mistake(seeded)
    repo.add(mistake)

    assert repo.list_by_concept(seeded["concept_id"]) == [mistake]


def test_update_increments_occurrences(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlMistakeRepository(engine)
    repo.add(_make_mistake(seeded))
    repo.update(_make_mistake(seeded, occurrences=2, last_seen=NOW))

    loaded = repo.list_by_concept(seeded["concept_id"])[0]
    assert loaded.occurrences == 2


def test_list_by_concept_excludes_other_concepts(engine: Engine, seeded: dict) -> None:  # type: ignore[type-arg]
    repo = SqlMistakeRepository(engine)
    repo.add(_make_mistake(seeded))

    assert repo.list_by_concept("some_other_concept") == []
