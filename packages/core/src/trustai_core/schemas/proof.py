from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from trustai_core.schemas.atoms import AtomModel


class MismatchReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    score: float
    threshold: float
    unsupported_claims: list[AtomModel]
    missing_evidence: list[AtomModel]
    ontology_conflicts: list[str]


class ProofObject(BaseModel):
    model_config = ConfigDict(frozen=True)

    pack: str
    pack_fingerprint: str
    evidence_atoms: list[AtomModel]
    claim_atoms: list[AtomModel]
    score: float
    mismatch: MismatchReport
