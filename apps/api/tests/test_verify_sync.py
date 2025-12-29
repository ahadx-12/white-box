from __future__ import annotations

from typing import Any

from trustai_core.llm.base import LLMError
from trustai_api.routes.utils import normalize_verification_result
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
        self.debug_calls = {"perceiver": [], "reasoner": []}

    async def verify_sync(
        self,
        input_text: str,
        pack: str,
        options: Any = None,
    ) -> VerificationResult:
        self.calls.append((input_text, pack, options))
        return self._result

    def debug_info(self) -> dict[str, object]:
        return self.debug_calls


class ErrorVerifier:
    async def verify_sync(
        self,
        input_text: str,
        pack: str,
        options: Any = None,
    ) -> VerificationResult:
        raise LLMError("model not found")

    def debug_info(self) -> dict[str, object]:
        return {}


def test_verify_sync(client, app):
    result = _build_result()
    app.state.verifier_service = FakeVerifier(result)

    response = client.post("/v1/verify", json={"input": "Hello"})

    assert response.status_code == 200
    payload = response.json()
    normalized = normalize_verification_result(result)
    assert payload["proof_id"] == normalized["proof_id"]
    assert payload["status"] == "verified"
    assert payload["final_answer"] == "Answer"
    assert payload["explain"]["summary"]
    assert payload["iterations"][0]["accepted"] is True
    assert payload["proof"]["status"] == "verified"


def test_verify_sync_debug_header_adds_debug(client, app):
    result = _build_result()
    fake_verifier = FakeVerifier(result)
    fake_verifier.debug_calls = {"perceiver": [{"role": "perceiver"}], "reasoner": []}
    app.state.verifier_service = fake_verifier

    response = client.post("/v1/verify", json={"input": "Hello"}, headers={"X-TrustAI-Debug": "1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["debug"]["perceiver"]


def test_verify_sync_llm_error_returns_503(client, app):
    app.state.verifier_service = ErrorVerifier()

    response = client.post("/v1/verify", json={"input": "Hello"})

    assert response.status_code == 503
    payload = response.json()
    assert payload["detail"] == "Upstream LLM error: model not found"
