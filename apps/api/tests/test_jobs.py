from __future__ import annotations

from trustai_api.db.models import Job
from trustai_api.routes.utils import normalize_verification_result
from trustai_api.services.proof_store import ProofStore
from trustai_core.schemas.proof import IterationTrace, MismatchReport, VerificationResult


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


def test_get_job_with_result(client, app):
    session_local = app.state.SessionLocal
    session = session_local()
    try:
        result = _build_result()
        proof_store = ProofStore()
        normalized = normalize_verification_result(result)
        proof_store.create(session, payload=normalized)
        job = Job(
            job_id="job-123",
            status="done",
            pack="general",
            input_text="Hello",
            proof_id=result.proof_id,
        )
        session.add(job)
        session.commit()
    finally:
        session.close()

    response = client.get("/v1/jobs/job-123")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "done"
    assert payload["proof_id"] == result.proof_id
    assert payload["result"]["proof_id"] == result.proof_id
    assert payload["result"]["proof"]["status"] == "verified"
