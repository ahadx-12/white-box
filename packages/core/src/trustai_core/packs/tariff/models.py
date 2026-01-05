from __future__ import annotations

from enum import Enum
from typing import Any, Literal

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


class GriStep(str, Enum):
    GRI_1 = "GRI_1"
    GRI_2 = "GRI_2"
    GRI_3 = "GRI_3"
    GRI_4 = "GRI_4"
    GRI_5 = "GRI_5"
    GRI_6 = "GRI_6"


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
    rationale: str
    legal_rationale: str
    risk_level: str
    constraints: list[str]
    required_evidence: list[str]


class TariffCitation(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim_type: str
    claim: str
    source_id: str
    quote: str


class GriStepResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    step: GriStep
    applied: bool
    reasoning: str
    citations: list[TariffCitation] = Field(default_factory=list)
    rejected_because: list[str] = Field(default_factory=list)


class GriTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    steps: list[GriStepResult]
    final_step_used: GriStep
    sequence_ok: bool
    violations: list[str] = Field(default_factory=list)
    step_vector: list[bool] = Field(default_factory=list)


class CompositionComponent(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    pct: float | None = None
    cost_pct: float | None = None
    mass_pct: float | None = None


class EssentialCharacter(BaseModel):
    model_config = ConfigDict(frozen=True)

    basis: Literal["value", "weight", "bulk", "function"]
    weights: dict[str, float]
    conclusion: str
    justification: str
    citations: list[TariffCitation] = Field(default_factory=list)


class WhatIfCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    mutation_id: str
    change: str
    rationale: str
    expected_heading_shift: str
    estimated_duty_delta: float | None = None
    legal_risks: list[str]
    citations_required: bool
    constraints: list[str] = Field(default_factory=list)


class SavingsEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    per_unit: float | None = None
    annualized: float | None = None
    formula: str | None = None


class TariffDossier(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_summary: str
    candidate_chapters: list[str] = Field(default_factory=list)
    assumptions: list[str]
    gri_trace: GriTrace
    composition_table: list[CompositionComponent]
    essential_character: EssentialCharacter
    baseline: TariffBaseline
    mutations: list[Mutation]
    best_option_id: str | None = None
    optimized: TariffOptimized
    what_if_candidates: list[WhatIfCandidate] = Field(default_factory=list)
    chosen_mutation: str | None = None
    savings_estimate: SavingsEstimate | None = None
    compliance_notes: list[str] = Field(default_factory=list)
    questions_for_user: list[str]
    citations: list[TariffCitation]


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
    gri_trace: GriTrace | None = None
    sequence_violations: list[str] = Field(default_factory=list)
    essential_character_score: float | None = None
    citation_gate_result: dict[str, Any] | None = None
    missing_evidence_gate_result: dict[str, Any] | None = None


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
    proposal_history: list[TariffDossier] = Field(default_factory=list)
    evidence_bundle: list[dict[str, Any]] | None = None
    citation_gate_result: dict[str, Any] | None = None
    citations: list[TariffCitation] | None = None
