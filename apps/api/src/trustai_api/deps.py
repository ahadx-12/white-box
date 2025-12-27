from __future__ import annotations

from collections.abc import Generator
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from trustai_api.db.models import Base
from trustai_api.db.session import create_engine_from_url, create_sessionmaker
from trustai_api.queue.rq import create_queue
from trustai_api.services.verifier_service import VerifierService
from trustai_api.settings import Settings, get_settings


def init_app_state(app) -> None:
    settings = get_settings()
    engine = create_engine_from_url(settings.database_url)
    SessionLocal = create_sessionmaker(engine)
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    app.state.settings = settings
    app.state.engine = engine
    app.state.SessionLocal = SessionLocal
    app.state.queue = create_queue(settings.redis_url)
    app.state.verifier_service = VerifierService(settings)


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Generator[Session, None, None]:
    session_local = request.app.state.SessionLocal
    db = session_local()
    try:
        yield db
    finally:
        db.close()


def get_queue(request: Request) -> Any:
    return request.app.state.queue


def get_verifier_service(request: Request) -> VerifierService:
    return request.app.state.verifier_service
