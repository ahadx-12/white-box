from __future__ import annotations

from typing import Any

from trustai_core.schemas.proof import IterationTrace, MismatchReport, VerificationResult


def _build_result() -> VerificationResult:
    mismatch = MismatchReport(
        score=0.95,
        threshold=0.92,
        unsupported_claims=[],
        missing_required=[],
        ontology_conflicts=[],
        contradictions=[],
    )
    iteration = IterationTrace(
        i=1,
        answer_preview="Answer",
        score=0.95,
        mismatch=mismatch,
        feedback_summary="",
        claim_manifest_hash="hash",
        top_conflicts=[],
        unsupported_claims=[],
        missing_required=[],
        feedback_text="",
        answer_delta_summary="initial_answer",
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
    def __init__(self, result: VerificationResult) -> None:
        self._result = result
        self.calls: list[tuple[str, str, Any]] = []

    async def verify_sync(
        self,
        input_text: str,
        pack: str,
        options: Any = None,
    ) -> VerificationResult:
        self.calls.append((input_text, pack, options))
        return self._result


def test_idempotency_reuses_response(client, app):
    result = _build_result()
    verifier = FakeVerifier(result)
    app.state.verifier_service = verifier

    headers = {"X-Request-Id": "req-123"}
    response1 = client.post("/v1/verify", json={"input": "Hello"}, headers=headers)
    response2 = client.post("/v1/verify", json={"input": "Hello"}, headers=headers)

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json()["proof_id"] == result.proof_id
    assert response2.json()["proof_id"] == result.proof_id
    assert len(verifier.calls) == 1
