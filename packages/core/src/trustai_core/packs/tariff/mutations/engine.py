from __future__ import annotations

from typing import Any

import orjson

from trustai_core.packs.tariff.evidence.models import EvidenceSource
from trustai_core.packs.tariff.gates import run_citation_gate, run_missing_evidence_gate
from trustai_core.packs.tariff.gates.plausibility_gate import run_plausibility_gate
from trustai_core.packs.tariff.models import TariffDossier, TariffVerificationResult
from trustai_core.packs.tariff.mutations.models import (
    LeverProof,
    LeverSavingsEstimate,
    LeverVerificationSummary,
    MutationCandidate,
    MutationCandidateAudit,
    ProductDossier,
    SelectedLever,
)
from trustai_core.packs.tariff.mutations.operators import build_default_operators
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
) -> LeverProof:
    baseline_summary = _build_baseline_summary(product_dossier, tariff_dossier)
    if not product_dossier or not tariff_dossier:
        return LeverProof(
            baseline_summary=baseline_summary,
            mutation_candidates=[],
            selected_levers=[],
        )

    candidates = _generate_candidates(product_dossier)
    audits: list[MutationCandidateAudit] = []
    accepted: list[SelectedLever] = []

    for candidate in candidates:
        compliance_result = run_plausibility_gate(candidate, product_dossier)
        rejection_reasons = list(compliance_result.violations)
        verification_summary: LeverVerificationSummary | None = None
        accepted_flag = False

        if compliance_result.ok:
            mutated = apply_diff(product_dossier, candidate)
            verification_summary = _verify_mutation(tariff_dossier, evidence_bundle)
            if not verification_summary.ok:
                rejection_reasons.extend(verification_summary.rejected_because)
            accepted_flag = verification_summary.ok
        audits.append(
            MutationCandidateAudit(
                candidate=candidate,
                compliance_gate_result=compliance_result.model_dump(),
                verification_summary=verification_summary,
                accepted=accepted_flag,
                rejection_reasons=rejection_reasons,
            )
        )
        if accepted_flag:
            savings_estimate = _estimate_savings(tariff_dossier, candidate)
            score = _score_candidate(savings_estimate)
            accepted.append(
                SelectedLever(
                    candidate=candidate,
                    baseline_summary=baseline_summary,
                    mutated_summary=_build_mutated_summary(mutated, tariff_dossier),
                    savings_estimate=savings_estimate,
                    score=score,
                    evidence_bundle=evidence_payload,
                    citations=[citation.model_dump() for citation in tariff_dossier.citations],
                    gate_results={
                        "plausibility": compliance_result.model_dump(),
                        "verification": verification_summary.model_dump() if verification_summary else None,
                    },
                )
            )

    ranked = sorted(accepted, key=lambda item: (-item.score, item.candidate.operator_id))
    return LeverProof(
        baseline_summary=baseline_summary,
        mutation_candidates=audits,
        selected_levers=ranked[: max(1, top_k)],
    )


def _generate_candidates(product_dossier: ProductDossier) -> list[MutationCandidate]:
    candidates: list[MutationCandidate] = []
    for operator in build_default_operators():
        candidates.extend(operator.generate(product_dossier))
    return sorted(candidates, key=lambda item: item.operator_id)


def apply_diff(product_dossier: ProductDossier, candidate: MutationCandidate) -> ProductDossier:
    data = product_dossier.model_dump()
    for diff in candidate.diff:
        _apply_path(data, diff.path, diff.to_value, diff.op)
    return ProductDossier.model_validate(data)


def _apply_path(payload: dict[str, Any], path: str, value: Any, op: str) -> None:
    if not path:
        return
    if op == "remove":
        _remove_path(payload, path)
        return
    parts = path.split(".")
    if parts[0] in {"upper_materials", "outsole_materials"} and len(parts) > 1:
        _apply_material_share(payload, parts[0], parts[1], value)
        return
    if parts[0] == "components" and len(parts) > 1:
        _apply_component_field(payload, parts[1:], value)
        return
    cursor: Any = payload
    for part in parts[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            cursor[part] = {}
        cursor = cursor[part]
    if op == "split":
        cursor[parts[-1]] = value if value is not None else cursor.get(parts[-1])
        return
    cursor[parts[-1]] = value


def _apply_material_share(
    payload: dict[str, Any],
    key: str,
    material: str,
    value: Any,
) -> None:
    items = payload.get(key)
    if not isinstance(items, list):
        return
    updated = False
    for item in items:
        if item.get("material") == material:
            item["pct"] = value
            updated = True
            break
    if not updated and value is not None:
        items.append({"material": material, "pct": value})


def _apply_component_field(
    payload: dict[str, Any],
    parts: list[str],
    value: Any,
) -> None:
    components = payload.get("components")
    if not isinstance(components, list):
        return
    identifier = parts[0].lower() if parts else ""
    field_path = parts[1:]
    if not field_path:
        return
    for component in components:
        name = str(component.get("name", "")).lower()
        comp_type = str(component.get("component_type", "")).lower()
        if identifier and identifier not in {name, comp_type}:
            continue
        _apply_nested_field(component, field_path, value)
        return


def _apply_nested_field(component: dict[str, Any], field_path: list[str], value: Any) -> None:
    cursor: Any = component
    for part in field_path[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            cursor[part] = {}
        cursor = cursor[part]
    cursor[field_path[-1]] = value


def _remove_path(payload: dict[str, Any], path: str) -> None:
    parts = path.split(".")
    cursor: Any = payload
    for part in parts[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            return
        cursor = cursor[part]
    cursor.pop(parts[-1], None)


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
    candidate: MutationCandidate,
) -> LeverSavingsEstimate:
    baseline_rate = dossier.baseline.duty_rate_pct
    optimized_rate = dossier.optimized.duty_rate_pct
    duty_savings = None
    if baseline_rate is not None and optimized_rate is not None:
        duty_savings = round(max(0.0, baseline_rate - optimized_rate), 4)
    plausibility_penalty = _plausibility_penalty(candidate)
    gate_confidence = 0.1 if dossier.citations else 0.0
    proxy_score = None if duty_savings is not None else max(0.0, 1.0 - plausibility_penalty)
    return LeverSavingsEstimate(
        duty_savings_pct=duty_savings,
        proxy_score=proxy_score,
        plausibility_penalty=plausibility_penalty,
        gate_confidence=gate_confidence,
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


def _score_candidate(savings: LeverSavingsEstimate) -> float:
    base = savings.duty_savings_pct if savings.duty_savings_pct is not None else (savings.proxy_score or 0.0)
    return round(base - savings.plausibility_penalty + savings.gate_confidence, 6)


def _build_baseline_summary(
    product_dossier: ProductDossier | None,
    tariff_dossier: TariffDossier | None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    if product_dossier:
        summary["product_summary"] = product_dossier.product_summary
    if tariff_dossier:
        summary["hts_code"] = tariff_dossier.baseline.hts_code
        summary["duty_rate_pct"] = tariff_dossier.baseline.duty_rate_pct
    return summary


def _build_mutated_summary(
    product_dossier: ProductDossier,
    tariff_dossier: TariffDossier,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "product_summary": product_dossier.product_summary,
        "hts_code": tariff_dossier.optimized.hts_code or tariff_dossier.baseline.hts_code,
        "duty_rate_pct": tariff_dossier.optimized.duty_rate_pct,
    }
    return summary


def extract_lever_proof(result: TariffVerificationResult) -> dict[str, Any] | None:
    if hasattr(result, "lever_proof"):
        return result.lever_proof
    return None
