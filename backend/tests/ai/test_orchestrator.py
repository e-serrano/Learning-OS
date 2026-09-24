from pathlib import Path

import pytest
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.ai.adapters.mock import MockProvider
from app.ai.errors import AIProviderUnavailableError
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.persistence.base import Base
from app.persistence.engine import create_sqlite_engine
from app.persistence.models import AIRunModel


class Greeting(BaseModel):
    text: str


def _engine(tmp_path: Path):  # type: ignore[no-untyped-def]
    engine = create_sqlite_engine(str(tmp_path / "test.sqlite3"))
    Base.metadata.create_all(engine)
    return engine


@pytest.mark.asyncio
async def test_successful_call_returns_result_and_logs_ai_run(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    provider = MockProvider()
    provider.set_response(Greeting, Greeting(text="hello"))
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")

    result = await orchestrator.generate(
        AIRequest(role="tutor", prompt_version="tutor.v1"), Greeting
    )

    assert result == Greeting(text="hello")
    with DbSession(engine) as db:
        runs = list(db.scalars(select(AIRunModel)))
        assert len(runs) == 1
        assert runs[0].success is True
        assert runs[0].error_type is None
        assert runs[0].provider == "mock"
        assert runs[0].model == "mock-1"
        assert runs[0].role == "tutor"
        assert runs[0].output_schema == "Greeting"


@pytest.mark.asyncio
async def test_failed_call_still_logs_ai_run_and_reraises(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    provider = MockProvider()
    provider.set_error(AIProviderUnavailableError("simulated outage"))
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")

    with pytest.raises(AIProviderUnavailableError):
        await orchestrator.generate(AIRequest(role="tutor", prompt_version="tutor.v1"), Greeting)

    with DbSession(engine) as db:
        runs = list(db.scalars(select(AIRunModel)))
        assert len(runs) == 1
        assert runs[0].success is False
        assert runs[0].error_type == "AIProviderUnavailableError"


@pytest.mark.asyncio
async def test_ai_run_never_stores_raw_request_or_response_content(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    provider = MockProvider()
    provider.set_response(Greeting, Greeting(text="secret-looking-content-xyz"))
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")

    await orchestrator.generate(AIRequest(role="tutor", prompt_version="tutor.v1"), Greeting)

    with DbSession(engine) as db:
        run = db.scalars(select(AIRunModel)).first()
        assert run is not None
        # only a hash and schema name are stored, never the actual content
        assert "secret-looking-content-xyz" not in (run.input_hash or "")
        assert "secret-looking-content-xyz" not in (run.output_schema or "")


@pytest.mark.asyncio
async def test_latency_is_recorded_as_non_negative_integer(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    provider = MockProvider()
    provider.set_response(Greeting, Greeting(text="hi"))
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")

    await orchestrator.generate(AIRequest(role="tutor", prompt_version="tutor.v1"), Greeting)

    with DbSession(engine) as db:
        run = db.scalars(select(AIRunModel)).first()
        assert run is not None
        assert run.latency_ms is not None
        assert run.latency_ms >= 0


@pytest.mark.asyncio
async def test_session_id_is_recorded_when_provided(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    provider = MockProvider()
    provider.set_response(Greeting, Greeting(text="hi"))
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")

    await orchestrator.generate(
        AIRequest(role="tutor", prompt_version="tutor.v1"), Greeting, session_id="session_1"
    )

    with DbSession(engine) as db:
        run = db.scalars(select(AIRunModel)).first()
        assert run is not None
        assert run.session_id == "session_1"


@pytest.mark.asyncio
async def test_generate_defaults_to_english_when_no_language_configured(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    provider = MockProvider()
    seen: list[AIRequest] = []
    provider.set_response(Greeting, lambda req: (seen.append(req), Greeting(text="hi"))[1])
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")

    await orchestrator.generate(AIRequest(role="tutor", prompt_version="tutor.v1"), Greeting)

    assert seen[0].constraints["language"] == "en"


@pytest.mark.asyncio
async def test_generate_injects_the_orchestrator_configured_language(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    provider = MockProvider()
    seen: list[AIRequest] = []
    provider.set_response(Greeting, lambda req: (seen.append(req), Greeting(text="hi"))[1])
    orchestrator = AIOrchestrator(
        engine, provider, provider_name="mock", model="mock-1", language="es"
    )

    await orchestrator.generate(AIRequest(role="curator", prompt_version="curator.v1"), Greeting)

    assert seen[0].constraints["language"] == "es"


@pytest.mark.asyncio
async def test_generate_never_overrides_an_explicit_language_constraint(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    provider = MockProvider()
    seen: list[AIRequest] = []
    provider.set_response(Greeting, lambda req: (seen.append(req), Greeting(text="hi"))[1])
    orchestrator = AIOrchestrator(
        engine, provider, provider_name="mock", model="mock-1", language="es"
    )

    await orchestrator.generate(
        AIRequest(role="tutor", prompt_version="tutor.v1", constraints={"language": "fr"}),
        Greeting,
    )

    assert seen[0].constraints["language"] == "fr"


@pytest.mark.asyncio
async def test_multiple_calls_each_get_their_own_ai_run_row(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    provider = MockProvider()
    provider.set_response(Greeting, Greeting(text="hi"))
    orchestrator = AIOrchestrator(engine, provider, provider_name="mock", model="mock-1")

    for _ in range(3):
        await orchestrator.generate(AIRequest(role="tutor", prompt_version="tutor.v1"), Greeting)

    with DbSession(engine) as db:
        runs = list(db.scalars(select(AIRunModel)))
        assert len(runs) == 3
        assert len({r.id for r in runs}) == 3
