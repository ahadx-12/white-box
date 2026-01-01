from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any

from sqlalchemy.orm import Session
from trustai_api.db.models import Base
from trustai_api.db.session import create_engine_from_url, create_sessionmaker
from trustai_api.routes.utils import normalize_verification_result
from trustai_api.services.idempotency import IdempotencyStore
from trustai_api.services.job_store import JobStore
from trustai_api.services.proof_store import ProofStore
from trustai_api.services.verifier_service import VerifierService, VerifyOptions
from trustai_api.settings import get_settings


def _run(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError("Async event loop already running")


@lru_cache
def _sessionmaker():
    settings = get_settings()
    engine = create_engine_from_url(settings.database_url)
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    return create_sessionmaker(engine)


@lru_cache
def _verifier_service() -> VerifierService:
    settings = get_settings()
    return VerifierService(settings)


def _get_session() -> Session:
    session_local = _sessionmaker()
    return session_local()


def run_deep_verify(job_id: str, payload: dict[str, Any]) -> None:
    session = _get_session()
    job_store = JobStore()
    proof_store = ProofStore()
    idempotency_store = IdempotencyStore()
    job = job_store.get(session, job_id)
    if not job:
        session.close()
        return
    job_store.set_running(session, job)
    try:
        options_payload = payload.get("options") if payload else None
        options = None
        if isinstance(options_payload, dict):
            options = VerifyOptions(
                max_iters=options_payload.get("max_iters"),
                threshold=options_payload.get("threshold"),
                min_mutations=options_payload.get("min_mutations"),
            )
        result = _run(
            _verifier_service().verify_sync(
                input_text=payload.get("input", job.input_text),
                pack=payload.get("pack", job.pack),
                options=options,
                evidence=payload.get("evidence"),
            )
        )
        normalized = normalize_verification_result(result)
        proof_store.create(session, payload=normalized)
        job_store.set_done(session, job, proof_id=result.proof_id)
        if job.request_id:
            record = idempotency_store.get(session, job.request_id)
            if record:
                record.proof_id = result.proof_id
                session.add(record)
                session.commit()
    except Exception as exc:  # pragma: no cover - safety net
        job_store.set_failed(session, job, error=str(exc))
    finally:
        session.close()
