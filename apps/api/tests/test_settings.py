from __future__ import annotations

from trustai_api.settings import get_settings


def test_database_url_normalizes_postgres_scheme(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost:5432/trustai")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.database_url.startswith("postgresql://")
    assert settings.database_url == "postgresql://user:pass@localhost:5432/trustai"


def test_database_url_defaults_to_sqlite(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.database_url == "sqlite:///./trustai_dev.db"


def test_auto_create_tables_env(monkeypatch) -> None:
    monkeypatch.setenv("TRUSTAI_DB_AUTOCREATE", "0")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.auto_create_tables is False
    monkeypatch.setenv("TRUSTAI_DB_AUTOCREATE", "1")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.auto_create_tables is True
