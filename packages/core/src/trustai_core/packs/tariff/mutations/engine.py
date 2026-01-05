from __future__ import annotations

from typing import Any

import orjson

from trustai_core.packs.tariff.evidence.models import EvidenceSource
from trustai_core.packs.tariff.gates import run_citation_gate, run_missing_evidence_gate
from trustai_core.packs.tariff.models import TariffDossier, TariffVerificationResult
from trustai_core.packs.tariff.mutations.models import (
    LeverProof,
    LeverSavingsEstimate,
    LeverSequenceStep,
    LeverVerificationSummary,
    MutationCandidate,
    ProductDossier,
    SelectedLever,
)
from trustai_core.packs.tariff.mutations.operators import build_default_operators
from trustai_core.packs.tariff.mutations.search import SearchConfig, run_beam_search
from trustai_core.packs.tariff.gri import validate_gri_sequence


def parse_product_dossier(input_text: str) -> ProductDossier | None:
    input_text = input_text.strip()
    if not input_text:
        return None
    if not (input_text.startswith("{") and input_text.endswith("}")):
        return None
    try:
        payload = orjson.loads(input_text)
    except orjson.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    candidate = payload.get("product_dossier") or payload.get("product") or payload
    if not isinstance(candidate, dict):
        return None
    try:
        return ProductDossier.model_validate(candidate)
    except Exception:
        return None


def build_lever_proof(
    product_dossier: ProductDossier | None,
    tariff_dossier: TariffDossier | None,
    evidence_bundle: list[EvidenceSource],
    evidence_payload: list[dict[str, Any]],
    top_k: int = 3,
    search_config: SearchConfig | None = None,
) -> LeverProof:
    baseline_summary = _build_baseline_summary(product_dossier, tariff_dossier)
    if not product_dossier or not tariff_dossier:
        return LeverProof(
            baseline_summary=baseline_summary,
            mutation_candidates=[],
            selected_levers=[],
        )

    search_config = search_config or SearchConfig()
    search_result = run_beam_search(
        product_dossier=product_dossier,
        tariff_dossier=tariff_dossier,
        evidence_bundle=evidence_bundle,
        operators=build_default_operators(),
        verifier=_verify_mutation,
        config=search_config,
    )

    accepted: list[SelectedLever] = []
    for sequence in search_result.sequences:
        savings_estimate = _estimate_savings(tariff_dossier, sequence)
        score = _score_sequence(savings_estimate)
        steps = [
            LeverSequenceStep(
                operator_id=candidate.operator_id,
                label=candidate.label,
                category=candidate.category,
                diff=candidate.diff,
                compliance_result=compliance_result,
            )
            for candidate, compliance_result in zip(sequence.sequence, sequence.compliance_results)
        ]
        accepted.append(
            SelectedLever(
                sequence=steps,
                baseline_summary=baseline_summary,
                final=_build_mutated_summary(sequence.dossier, tariff_dossier),
                verification=sequence.verification_summary,
                savings_estimate=savings_estimate,
                score=score,
                evidence_bundle=evidence_payload,
                citations=[citation.model_dump() for citation in tariff_dossier.citations],
                gate_results={
                    "plausibility": sequence.compliance_results,
                    "verification": sequence.verification_summary.model_dump()
                    if sequence.verification_summary
                    else None,
                },
                search_meta={
                    "state_hash": sequence.state_hash,
                    "parent_hashes": sequence.parent_hashes,
                },
            )
        )

    ranked = sorted(accepted, key=lambda item: (-item.score, _sequence_key(item.sequence)))
    return LeverProof(
        baseline_summary=baseline_summary,
        mutation_candidates=search_result.audits,
        selected_levers=ranked[: max(1, top_k)],
        search_summary=search_result.search_summary,
        rejected_sequences=search_result.rejected_sequences,
    )


def _verify_mutation(
    dossier: TariffDossier,
    evidence_bundle: list[EvidenceSource],
) -> LeverVerificationSummary:
    citation_gate = run_citation_gate(dossier, evidence_bundle)
    missing_evidence_gate = run_missing_evidence_gate(dossier, evidence_bundle)
    sequence_ok, sequence_violations = validate_gri_sequence(dossier.gri_trace)
    rejected: list[str] = []
    if not citation_gate.ok:
        rejected.append("citation_gate_failed")
    if not missing_evidence_gate.ok:
        rejected.append("missing_evidence")
    if not sequence_ok:
        rejected.append("gri_sequence_violation")
    return LeverVerificationSummary(
        ok=not rejected,
        rejected_because=rejected,
        citation_gate_result=citation_gate.model_dump(),
        missing_evidence_gate_result=missing_evidence_gate.model_dump(),
        sequence_ok=sequence_ok,
        sequence_violations=sequence_violations,
    )


def _estimate_savings(
    dossier: TariffDossier,
    sequence: Any,
) -> LeverSavingsEstimate:
    baseline_rate = _resolve_duty_rate(dossier.baseline)
    optimized_rate = _resolve_duty_rate(dossier.optimized)
    duty_savings = None
    if baseline_rate is not None and optimized_rate is not None:
        duty_savings = round(max(0.0, baseline_rate - optimized_rate), 4)
    plausibility_penalty = _sequence_plausibility_penalty(sequence.sequence)
    gate_confidence = 0.1 if dossier.citations else 0.0
    proxy_score = None if duty_savings is not None else max(0.0, 1.0 - plausibility_penalty)
    cost_impact = _sequence_cost_impact(sequence.sequence)
    risk_penalty = _sequence_risk_penalty(dossier, sequence.compliance_results)
    overall_score = 0.05 + 0.4 * max(0, len(sequence.sequence) - 1)
    if sequence.verification_summary and sequence.verification_summary.ok:
        overall_score += 0.05
    savings_type = "duty_savings" if duty_savings is not None else "proxy"
    return LeverSavingsEstimate(
        duty_savings_pct=duty_savings,
        proxy_score=proxy_score,
        savings_estimate_type=savings_type,
        plausibility_penalty=plausibility_penalty,
        gate_confidence=gate_confidence,
        cost_impact=cost_impact,
        overall_score=overall_score,
        risk_penalty=risk_penalty,
    )


def _plausibility_penalty(candidate: MutationCandidate) -> float:
    penalties: list[float] = []
    max_material = candidate.bounds.max_material_delta or 0.0
    max_cost = candidate.bounds.max_cost_delta or 0.0
    for diff in candidate.diff:
        material_delta = diff.details.get("material_delta_pct")
        if material_delta is not None and max_material:
            penalties.append(min(1.0, float(material_delta) / max_material))
        cost_delta = diff.details.get("cost_delta_pct")
        if cost_delta is not None and max_cost:
            penalties.append(min(1.0, float(cost_delta) / max_cost))
    if not penalties:
        return 0.0
    return round(sum(penalties) / len(penalties), 4)


def _resolve_duty_rate(duty_summary: object) -> float | None:
    if hasattr(duty_summary, "duty_breakdown"):
        breakdown = getattr(duty_summary, "duty_breakdown")
        if breakdown is not None and getattr(breakdown, "total_rate_pct", None) is not None:
            return float(breakdown.total_rate_pct)
    if hasattr(duty_summary, "duty_rate_pct"):
        value = getattr(duty_summary, "duty_rate_pct")
        if value is not None:
            return float(value)
    return None


def _sequence_plausibility_penalty(sequence: list[MutationCandidate]) -> float:
    if not sequence:
        return 0.0
    penalties = [_plausibility_penalty(candidate) for candidate in sequence]
    return round(sum(penalties) / len(penalties), 4)


def _sequence_cost_impact(sequence: list[MutationCandidate]) -> float:
    deltas: list[float] = []
    for candidate in sequence:
        for diff in candidate.diff:
            cost_delta = diff.details.get("cost_delta_pct")
            if cost_delta is not None:
                deltas.append(abs(float(cost_delta)))
    if not deltas:
        return 0.0
    return round(sum(deltas) / len(deltas), 4)


def _sequence_risk_penalty(dossier: TariffDossier, compliance_results: list[dict[str, Any]]) -> float:
    risk_flags = set(dossier.optimized.risk_flags or [])
    for result in compliance_results:
        for flag in result.get("risk_flags") or []:
            risk_flags.add(flag)
    return round(0.05 * len(risk_flags), 4)


def _score_sequence(savings: LeverSavingsEstimate) -> float:
    base = savings.duty_savings_pct if savings.duty_savings_pct is not None else (savings.proxy_score or 0.0)
    score = (
        base
        - savings.plausibility_penalty
        - savings.cost_impact
        - savings.risk_penalty
        + savings.gate_confidence
        + savings.overall_score
    )
    return round(score, 6)


def _sequence_key(sequence: list[LeverSequenceStep]) -> str:
    return "|".join(step.operator_id for step in sequence)


def _build_baseline_summary(
    product_dossier: ProductDossier | None,
    tariff_dossier: TariffDossier | None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    if product_dossier:
        summary["product_summary"] = product_dossier.product_summary
    if tariff_dossier:
        summary["hts_code"] = tariff_dossier.baseline.hts_code
        summary["duty_rate_pct"] = _resolve_duty_rate(tariff_dossier.baseline)
    return summary


def _build_mutated_summary(
    product_dossier: ProductDossier,
    tariff_dossier: TariffDossier,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "product_summary": product_dossier.product_summary,
        "hts_code": tariff_dossier.optimized.hts_code or tariff_dossier.baseline.hts_code,
        "duty_rate_pct": _resolve_duty_rate(tariff_dossier.optimized),
    }
    return summary


def extract_lever_proof(result: TariffVerificationResult) -> dict[str, Any] | None:
    if hasattr(result, "lever_proof"):
        return result.lever_proof
    return None
