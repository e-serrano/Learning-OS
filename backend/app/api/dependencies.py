import uuid
from datetime import UTC, datetime
from functools import lru_cache

from sqlalchemy import Engine

from app.config import ConfigStore, CredentialStore, Settings
from app.persistence.engine import create_sqlite_engine
from app.persistence.repositories.goal import SqlGoalRepository
from app.services.goal_service import GoalApplicationService


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
