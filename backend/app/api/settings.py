from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies import get_config_store
from app.api.errors import api_error
from app.config.languages import SUPPORTED_LANGUAGES
from app.config.store import ConfigStore

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

ConfigStoreDep = Annotated[ConfigStore, Depends(get_config_store)]


class SettingsResponse(BaseModel):
    language: str
    supported_languages: dict[str, str]


class UpdateLanguageRequest(BaseModel):
    language: str


@router.get("", response_model=SettingsResponse)
def get_settings(store: ConfigStoreDep) -> SettingsResponse:
    return SettingsResponse(language=store.load().language, supported_languages=SUPPORTED_LANGUAGES)


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
    return SettingsResponse(language=config.language, supported_languages=SUPPORTED_LANGUAGES)
