from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class VerifyOptions(BaseModel):
    max_iters: int | None = Field(default=None, ge=1)
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class VerifyRequest(BaseModel):
    input: str
    mode: Literal["sync", "async"] | None = None
    options: VerifyOptions | None = None


class IterationTraceResponse(BaseModel):
    i: int
    score: float
    accepted: bool
    rejected_because: list[str]
    conflicts: list[str]
    top_conflicts: list[str]
    unsupported: list[str]
    missing: list[str]
    feedback_text: str
    answer_delta_summary: str


class ExplainSummaryResponse(BaseModel):
    summary: str
    key_conflicts: list[str]
    unsupported_claims: list[str]
    missing_required: list[str]


class VerificationResultResponse(BaseModel):
    status: str
    proof_id: str
    pack: str
    pack_fingerprint: str
    evidence_manifest_hash: str
    final_answer: str | None
    iterations: list[IterationTraceResponse]
    similarity_history: list[float]
    explain: ExplainSummaryResponse
    proof: dict[str, Any]
    debug: dict[str, Any] | None = None


class VerifyAsyncResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    proof_id: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


class ProofResponse(BaseModel):
    proof_id: str
    payload: dict[str, Any]


class PacksResponse(BaseModel):
    packs: list[str]
