from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ProductComponent(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    material: str | None = None
    pct: float | None = None
    cost_pct: float | None = None
    removable: bool | None = None
    contains_electronics: bool | None = None
    component_type: str | None = None


class MaterialShare(BaseModel):
    model_config = ConfigDict(frozen=True)

    material: str
    pct: float


class ProductDossier(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    product_id: str | None = None
    product_summary: str | None = None
    chapter: str | None = None
    sold_as_set: bool | None = None
    packaging_description: str | None = None
    components: list[ProductComponent] = Field(default_factory=list)
    upper_materials: list[MaterialShare] = Field(default_factory=list)
    outsole_materials: list[MaterialShare] = Field(default_factory=list)
    connector_material: str | None = None
    adapter_housing_material: str | None = None
    housing_material: str | None = None
    material_grade: str | None = None
    finish: str | None = None
    contains_electronics: bool | None = None
    safety_footwear: bool | None = None
    has_metal_toe: bool | None = None
    cost_total: float | None = None


class ProductDiff(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    path: str
    op: Literal["replace", "split", "remove"] = "replace"
    from_value: Any | None = Field(default=None, alias="from", serialization_alias="from")
    to_value: Any | None = Field(default=None, alias="to", serialization_alias="to")
    details: dict[str, Any] = Field(default_factory=dict)


class MutationBounds(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_cost_delta: float | None = None
    max_material_delta: float | None = None
    max_component_removal: float | None = None


class MutationCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    operator_id: str
    label: str
    category: Literal["packaging", "material", "construction", "assembly"]
    required_inputs: list[str]
    diff: list[ProductDiff]
    assumptions: list[str]
    bounds: MutationBounds
    compliance_framing: str
    touch_paths: list[str] = Field(default_factory=list)
    composable_with: list[str] | None = None


class LeverVerificationSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    ok: bool
    rejected_because: list[str]
    citation_gate_result: dict[str, Any] | None = None
    missing_evidence_gate_result: dict[str, Any] | None = None
    sequence_ok: bool | None = None
    sequence_violations: list[str] = Field(default_factory=list)


class MutationCandidateAudit(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate: MutationCandidate
    compliance_gate_result: dict[str, Any]
    verification_summary: LeverVerificationSummary | None = None
    accepted: bool
    rejection_reasons: list[str] = Field(default_factory=list)


class LeverSavingsEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    duty_savings_pct: float | None = None
    proxy_score: float | None = None
    savings_estimate_type: Literal["duty_savings", "proxy"] = "proxy"
    plausibility_penalty: float = 0.0
    gate_confidence: float = 0.0
    cost_impact: float = 0.0
    overall_score: float = 0.0
    risk_penalty: float = 0.0


class LeverSequenceStep(BaseModel):
    model_config = ConfigDict(frozen=True)

    operator_id: str
    label: str
    category: str
    diff: list[ProductDiff]
    compliance_result: dict[str, Any]


class SelectedLever(BaseModel):
    model_config = ConfigDict(frozen=True)

    sequence: list[LeverSequenceStep]
    baseline_summary: dict[str, Any]
    final: dict[str, Any]
    verification: LeverVerificationSummary | None = None
    savings_estimate: LeverSavingsEstimate
    score: float
    evidence_bundle: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    gate_results: dict[str, Any] = Field(default_factory=dict)
    search_meta: dict[str, Any] = Field(default_factory=dict)


class SearchSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_depth: int
    beam_width: int
    max_expansions: int
    visited: int
    expanded: int
    pruned: int
    unique: int
    dedup_hits: int


class RejectedSequence(BaseModel):
    model_config = ConfigDict(frozen=True)

    sequence: list[str]
    reason: str
    state_hash: str | None = None


class LeverProof(BaseModel):
    model_config = ConfigDict(frozen=True)

    baseline_summary: dict[str, Any]
    mutation_candidates: list[MutationCandidateAudit]
    selected_levers: list[SelectedLever]
    search_summary: SearchSummary | None = None
    rejected_sequences: list[RejectedSequence] = Field(default_factory=list)
