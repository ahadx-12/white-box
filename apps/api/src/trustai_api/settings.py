from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str
    redis_url: str
    storage_root: Path
    openai_model: str
    claude_model: str
    auto_create_tables: bool
    llm_mode: str


def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return f"postgresql://{database_url[len('postgres://'):]}"
    return database_url


@lru_cache
def get_settings() -> Settings:
    raw_database_url = os.getenv("DATABASE_URL")
    if not raw_database_url:
        raw_database_url = "sqlite:///./trustai_dev.db"
    database_url = _normalize_database_url(raw_database_url)
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    storage_root = Path(os.getenv("TRUSTAI_PACKS_ROOT", "storage/packs"))
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    claude_model = os.getenv("CLAUDE_MODEL", "claude-3.5-sonnet")
    auto_create_tables_env = os.getenv("TRUSTAI_DB_AUTOCREATE")
    if auto_create_tables_env is None:
        auto_create_tables_env = os.getenv("TRUSTAI_AUTO_CREATE_TABLES", "1")
    auto_create_tables = auto_create_tables_env == "1"
    llm_mode = os.getenv("TRUSTAI_LLM_MODE", "live")
    return Settings(
        database_url=database_url,
        redis_url=redis_url,
        storage_root=storage_root,
        openai_model=openai_model,
        claude_model=claude_model,
        auto_create_tables=auto_create_tables,
        llm_mode=llm_mode,
    )
