from app.config.settings import Settings


def test_cors_origins_default_matches_the_vite_dev_server() -> None:
    settings = Settings()
    assert settings.cors_origins_list == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_cors_origins_list_splits_and_strips_a_comma_separated_string() -> None:
    settings = Settings(cors_origins="http://a.example, http://b.example ,http://c.example")
    assert settings.cors_origins_list == [
        "http://a.example",
        "http://b.example",
        "http://c.example",
    ]


def test_cors_origins_list_drops_empty_entries() -> None:
    settings = Settings(cors_origins="http://a.example,,")
    assert settings.cors_origins_list == ["http://a.example"]


def test_cors_origins_list_is_empty_for_a_blank_string() -> None:
    settings = Settings(cors_origins="")
    assert settings.cors_origins_list == []
