from __future__ import annotations

from typing import Any

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


def test_verify_sync(client, app):
    result = _build_result()
    app.state.verifier_service = FakeVerifier(result)

    response = client.post("/v1/verify", json={"input": "Hello"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["proof_id"] == result.proof_id
    assert payload["status"] == "verified"
    assert payload["final_answer"] == "Answer"
