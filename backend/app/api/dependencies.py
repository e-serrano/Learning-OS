from functools import lru_cache

from app.config import ConfigStore, CredentialStore, Settings


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_config_store() -> ConfigStore:
    return ConfigStore(get_settings().db_path)


def get_credential_store() -> CredentialStore:
    return CredentialStore()
