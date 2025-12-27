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


@lru_cache
def get_settings() -> Settings:
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://trustai:trustai@postgres:5432/trustai",
    )
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    storage_root = Path(os.getenv("TRUSTAI_PACKS_ROOT", "storage/packs"))
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    claude_model = os.getenv("CLAUDE_MODEL", "claude-3.5-sonnet")
    auto_create_tables = os.getenv("TRUSTAI_AUTO_CREATE_TABLES", "1") == "1"
    return Settings(
        database_url=database_url,
        redis_url=redis_url,
        storage_root=storage_root,
        openai_model=openai_model,
        claude_model=claude_model,
        auto_create_tables=auto_create_tables,
    )
