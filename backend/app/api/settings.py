from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies import get_config_store, is_vault_a_git_repo
from app.api.errors import api_error
from app.config.languages import SUPPORTED_LANGUAGES
from app.config.store import ConfigStore

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

ConfigStoreDep = Annotated[ConfigStore, Depends(get_config_store)]


class SettingsResponse(BaseModel):
    language: str
    supported_languages: dict[str, str]
    git_auto_commit: bool
    git_available: bool


class UpdateLanguageRequest(BaseModel):
    language: str


class UpdateGitAutoCommitRequest(BaseModel):
    enabled: bool


def _response(store: ConfigStore) -> SettingsResponse:
    config = store.load()
    return SettingsResponse(
        language=config.language,
        supported_languages=SUPPORTED_LANGUAGES,
        git_auto_commit=config.git_auto_commit,
        git_available=is_vault_a_git_repo(store),
    )


@router.get("", response_model=SettingsResponse)
def get_settings(store: ConfigStoreDep) -> SettingsResponse:
    return _response(store)


@router.patch("/language", response_model=SettingsResponse)
def update_language(request: UpdateLanguageRequest, store: ConfigStoreDep) -> SettingsResponse:
    if request.language not in SUPPORTED_LANGUAGES:
        raise api_error(
            "VALIDATION_ERROR",
            f"Unsupported language {request.language!r}. Supported: {sorted(SUPPORTED_LANGUAGES)}",
            400,
        )

    config = store.load()
    config.language = request.language
    store.save(config)
    return _response(store)


@router.patch("/git-auto-commit", response_model=SettingsResponse)
def update_git_auto_commit(
    request: UpdateGitAutoCommitRequest, store: ConfigStoreDep
) -> SettingsResponse:
    config = store.load()
    config.git_auto_commit = request.enabled
    store.save(config)
    return _response(store)
