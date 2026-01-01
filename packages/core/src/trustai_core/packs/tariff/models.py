from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TariffBaseline(BaseModel):
    model_config = ConfigDict(frozen=True)

    hts_code: str | None = None
    duty_rate_pct: float | None = None
    duty_basis: str
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)


class TariffOptimized(BaseModel):
    model_config = ConfigDict(frozen=True)

    hts_code: str | None = None
    duty_rate_pct: float | None = None
    estimated_savings_per_unit: float | None = None
    rationale: str
    risk_flags: list[str]


class Mutation(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    category: str
    change: str
    expected_effect: str
    expected_hts_change: str | None = None
    expected_duty_rate_pct: float | None = None
    expected_savings_note: str
    legal_rationale: str
    risk_level: str
    constraints: list[str]
    required_evidence: list[str]


class TariffDossier(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_summary: str
    assumptions: list[str]
    baseline: TariffBaseline
    mutations: list[Mutation]
    best_option_id: str | None = None
    optimized: TariffOptimized
    questions_for_user: list[str]
    citations: list[str]


class TariffCritique(BaseModel):
    model_config = ConfigDict(frozen=True)

    unsupported: list[str]
    missing: list[str]
    conflicts: list[str]
    suggested_fixes: list[str]
    revised_questions_for_user: list[str]


class TariffVerifyIteration(BaseModel):
    model_config = ConfigDict(frozen=True)

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
    hdc_score: float | None = None
    mismatch_report: str | None = None


class TariffVerificationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    proof_id: str
    pack: str
    pack_fingerprint: str
    evidence_manifest_hash: str
    final_answer: str | None
    iterations: list[TariffVerifyIteration]
    explain: dict[str, Any]
    tariff_dossier: TariffDossier | None
    critic_outputs: list[TariffCritique]
    model_routing: dict[str, Any]
