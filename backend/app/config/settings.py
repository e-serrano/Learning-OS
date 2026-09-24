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
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    """Comma-separated allowed origins for `CORSMiddleware` (docs/TASKS.md
    T143). A plain comma-separated string, not a JSON list, so it stays a
    one-line, no-quoting-gotchas value in a `.env` file (Docker's most
    common case) -- see `cors_origins_list`. The default matches the Vite
    dev server exactly, so `.env`-less native dev is unaffected."""

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
