from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process-level infrastructure settings, sourced from the environment.

    Distinct from AppConfig: this is fixed per-process (host/port/paths),
    while AppConfig is user-managed state mutated through onboarding.
    """

    model_config = SettingsConfigDict(env_prefix="LEARNINGOS_", env_file=".env")

    host: str = "127.0.0.1"
    port: int = 8000
    db_path: str = "./data/learning_os.sqlite3"
    log_level: str = "INFO"
