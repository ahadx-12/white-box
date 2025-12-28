from __future__ import annotations

import os
from typing import Any

import pytest
from fastapi.testclient import TestClient
from trustai_api.main import create_app
from trustai_api.settings import get_settings


class DummyQueue:
    def __init__(self) -> None:
        self.enqueued: list[tuple[str, dict[str, Any]]] = []

    def enqueue(self, func: str, job_id: str, payload: dict[str, Any], **kwargs: Any) -> None:
        self.enqueued.append((job_id, payload))


@pytest.fixture(autouse=True)
def _settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("TRUSTAI_DB_AUTOCREATE", "1")
    monkeypatch.setenv("TRUSTAI_PACKS_ROOT", os.path.abspath("storage/packs"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        app.state.queue = DummyQueue()
        yield client
