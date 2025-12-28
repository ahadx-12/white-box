from __future__ import annotations

from typing import Any

import orjson
from pydantic import BaseModel, ConfigDict

from trustai_core.schemas.atoms import AtomModel
from trustai_core.utils.hashing import sha256_canonical_json

ANSWER_PREVIEW_CHARS = 160


class ContradictionPair(BaseModel):
    model_config = ConfigDict(frozen=True)

    left: AtomModel
    right: AtomModel


class MismatchReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    score: float
    threshold: float
    unsupported_claims: list[AtomModel]
    missing_required: list[AtomModel]
    ontology_conflicts: list[str]
    contradictions: list[ContradictionPair] = []


class IterationTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    i: int
    answer_preview: str
    score: float
    mismatch: MismatchReport
    feedback_summary: str
    claim_manifest_hash: str
    top_conflicts: list[str]
    unsupported_claims: list[AtomModel]
    missing_required: list[AtomModel]
    feedback_text: str
    answer_delta_summary: str


class VerificationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    proof_id: str
    pack: str
    pack_fingerprint: str
    evidence_manifest_hash: str
    final_answer: str | None
    iterations: list[IterationTrace]
    explain: dict[str, Any]

    @staticmethod
    def compute_proof_id(payload: dict[str, Any]) -> str:
        return sha256_canonical_json(payload)

    def canonical_json(self) -> bytes:
        return orjson.dumps(self.model_dump(), option=orjson.OPT_SORT_KEYS)


class ProofObject(BaseModel):
    model_config = ConfigDict(frozen=True)

    pack: str
    pack_fingerprint: str
    evidence_atoms: list[AtomModel]
    claim_atoms: list[AtomModel]
    score: float
    mismatch: MismatchReport
