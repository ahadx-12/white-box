from __future__ import annotations

import os

import pytest
from trustai_api.routes.utils import normalize_verification_result
from trustai_api.services.job_store import JobStore
from trustai_api.services.proof_store import ProofStore
from trustai_api.settings import get_settings
from trustai_core.schemas.proof import IterationTrace, MismatchReport, VerificationResult
from trustai_worker import tasks


def _build_result() -> VerificationResult:
    mismatch = MismatchReport(
        score=0.95,
        threshold=0.92,
        unsupported_claims=[],
        missing_evidence=[],
        ontology_conflicts=[],
    )
    iteration = IterationTrace(
        i=1,
        answer_preview="Answer",
        score=0.95,
        mismatch=mismatch,
        feedback_summary="",
        claim_manifest_hash="hash",
    )
    payload = {
        "status": "verified",
        "pack": "general",
        "pack_fingerprint": "fingerprint",
        "evidence_manifest_hash": "evidence",
        "final_answer": "Answer",
        "iterations": [iteration.model_dump()],
        "explain": {"score": 0.95, "threshold": 0.92},
    }
    proof_id = VerificationResult.compute_proof_id(payload)
    return VerificationResult(
        proof_id=proof_id,
        status="verified",
        pack="general",
        pack_fingerprint="fingerprint",
        evidence_manifest_hash="evidence",
        final_answer="Answer",
        iterations=[iteration],
        explain={"score": 0.95, "threshold": 0.92},
    )


class FakeVerifier:
    async def verify_sync(self, input_text: str, pack: str, options=None) -> VerificationResult:
        return _build_result()


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("TRUSTAI_AUTO_CREATE_TABLES", "1")
    monkeypatch.setenv("TRUSTAI_PACKS_ROOT", os.path.abspath("storage/packs"))
    get_settings.cache_clear()
    tasks._sessionmaker.cache_clear()
    if hasattr(tasks._verifier_service, "cache_clear"):
        tasks._verifier_service.cache_clear()
    yield
    get_settings.cache_clear()
    tasks._sessionmaker.cache_clear()
    if hasattr(tasks._verifier_service, "cache_clear"):
        tasks._verifier_service.cache_clear()


def test_worker_runs_job(monkeypatch: pytest.MonkeyPatch) -> None:
    session = tasks._get_session()
    job_store = JobStore()
    job_store.create(session, job_id="job-1", pack="general", input_text="Hello")
    session.close()

    monkeypatch.setattr(tasks, "_verifier_service", lambda: FakeVerifier())

    tasks.run_deep_verify("job-1", {"input": "Hello", "pack": "general"})

    session = tasks._get_session()
    proof_store = ProofStore()
    job = job_store.get(session, "job-1")
    assert job is not None
    assert job.status == "done"
    assert job.proof_id is not None
    stored_proof = proof_store.get(session, job.proof_id)
    assert stored_proof is not None
    normalized = normalize_verification_result(_build_result())
    assert stored_proof.proof_id == normalized["proof_id"]
    session.close()
