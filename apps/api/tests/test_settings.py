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


def test_llm_mode_defaults_to_fixture(monkeypatch) -> None:
    monkeypatch.delenv("TRUSTAI_LLM_MODE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPEN_AI_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_AI_KEY", raising=False)
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.llm_mode == "fixture"


def test_live_mode_requires_keys(monkeypatch) -> None:
    monkeypatch.setenv("TRUSTAI_LLM_MODE", "live")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPEN_AI_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_AI_KEY", raising=False)
    get_settings.cache_clear()
    try:
        get_settings()
    except ValueError as exc:
        assert "TRUSTAI_LLM_MODE=live requires" in str(exc)
    else:
        raise AssertionError("Expected live mode to require keys")


def test_debug_default_env(monkeypatch) -> None:
    monkeypatch.setenv("TRUSTAI_DEBUG_DEFAULT", "1")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.debug_default is True
