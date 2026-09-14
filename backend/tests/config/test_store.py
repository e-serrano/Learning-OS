from pathlib import Path

from app.config.models import AppConfig, OnboardingStep
from app.config.store import ConfigStore


def test_load_missing_file_returns_defaults(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "app_config.json")
    config = store.load()
    assert config == AppConfig()


def test_save_then_load_roundtrips(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "nested" / "app_config.json")
    original = AppConfig(
        vault_path="/home/user/vault",
        provider_id="ollama",
        model="llama3",
        language="es",
        onboarding_step=OnboardingStep.VAULT_SCAN,
    )
    store.save(original)

    loaded = store.load()
    assert loaded == original


def test_save_is_atomic_no_leftover_temp_files(tmp_path: Path) -> None:
    target = tmp_path / "app_config.json"
    store = ConfigStore(target)
    store.save(AppConfig(vault_path="/vault"))

    files = list(tmp_path.iterdir())
    assert files == [target]


def test_save_overwrites_previous_content(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "app_config.json")
    store.save(AppConfig(language="en"))
    store.save(AppConfig(language="fr"))

    assert store.load().language == "fr"
