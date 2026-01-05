from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from trustai_core.packs.tariff.mutations.models import MutationCandidate, ProductDossier

DOCUMENT_ONLY_FIELDS = {
    "description",
    "declared_hts",
    "documentation",
    "paperwork",
    "invoice",
}
BANNED_KEYWORDS = {
    "misdeclare",
    "misrepresentation",
    "falsify",
    "fake",
    "fraud",
    "evade",
    "evasion",
    "hide",
    "smuggle",
}


class PlausibilityGateResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    ok: bool
    violations: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    guidance: str = ""


def run_plausibility_gate(
    candidate: MutationCandidate,
    dossier: ProductDossier,
) -> PlausibilityGateResult:
    violations: list[str] = []
    risk_flags: list[str] = []

    if _is_document_only(candidate):
        violations.append("documentary_change_only")

    if _contains_banned_terms(candidate):
        violations.append("illegal_or_evasive_language")

    bounds_violations = _bounds_violations(candidate)
    violations.extend(bounds_violations)

    contradictions = _contradiction_violations(candidate, dossier)
    violations.extend(contradictions)

    if dossier.safety_footwear and _removes_protection(candidate):
        violations.append("safety_feature_removed")

    guidance = _build_guidance(violations)
    return PlausibilityGateResult(
        ok=not violations,
        violations=sorted(set(violations)),
        risk_flags=sorted(set(risk_flags)),
        guidance=guidance,
    )


def _is_document_only(candidate: MutationCandidate) -> bool:
    paths = [diff.path.lower() for diff in candidate.diff]
    if not paths:
        return True
    for path in paths:
        if not any(token in path for token in DOCUMENT_ONLY_FIELDS):
            return False
    return True


def _contains_banned_terms(candidate: MutationCandidate) -> bool:
    tokens = " ".join([
        candidate.label,
        candidate.compliance_framing,
        " ".join(candidate.assumptions),
    ]).lower()
    return any(term in tokens for term in BANNED_KEYWORDS)


def _bounds_violations(candidate: MutationCandidate) -> list[str]:
    violations: list[str] = []
    max_material = candidate.bounds.max_material_delta
    max_cost = candidate.bounds.max_cost_delta
    max_remove = candidate.bounds.max_component_removal
    for diff in candidate.diff:
        material_delta = diff.details.get("material_delta_pct")
        if material_delta is not None and max_material is not None:
            if float(material_delta) > max_material:
                violations.append("material_delta_exceeds_bounds")
        cost_delta = diff.details.get("cost_delta_pct")
        if cost_delta is not None and max_cost is not None:
            if float(cost_delta) > max_cost:
                violations.append("cost_delta_exceeds_bounds")
        removal = diff.details.get("component_removal_pct")
        if removal is not None and max_remove is not None:
            if float(removal) > max_remove:
                violations.append("component_removal_exceeds_bounds")
    return violations


def _contradiction_violations(candidate: MutationCandidate, dossier: ProductDossier) -> list[str]:
    violations: list[str] = []
    electronics_present = _electronics_present(dossier)
    if electronics_present and _claims_no_electronics(candidate):
        violations.append("contradiction_electronics_present")
    return violations


def _electronics_present(dossier: ProductDossier) -> bool:
    if dossier.contains_electronics:
        return True
    for component in dossier.components:
        if component.contains_electronics:
            return True
        if component.component_type and "sensor" in component.component_type.lower():
            return True
    return False


def _claims_no_electronics(candidate: MutationCandidate) -> bool:
    text = " ".join([candidate.label, " ".join(candidate.assumptions)]).lower()
    if "no electronics" in text or "remove electronics" in text:
        return True
    for diff in candidate.diff:
        if "electronics" in diff.path.lower():
            if diff.to_value is False or diff.op == "remove":
                return True
    return False


def _removes_protection(candidate: MutationCandidate) -> bool:
    for diff in candidate.diff:
        if "metal_toe" in diff.path.lower() or "protect" in diff.path.lower():
            if diff.to_value is False or diff.op == "remove":
                return True
    return False


def _build_guidance(violations: list[str]) -> str:
    if not violations:
        return ""
    if "documentary_change_only" in violations:
        return "Provide a design/manufacturing change with measurable inputs (materials, components)."
    if any("bounds" in violation for violation in violations):
        return "Adjust the proposal to stay within configured material/cost bounds."
    if any("contradiction" in violation for violation in violations):
        return "Align the mutation with known product facts (e.g., electronics, safety features)."
    if "illegal_or_evasive_language" in violations:
        return "Remove any language suggesting misrepresentation or evasion."
    if "safety_feature_removed" in violations:
        return "Provide an alternate compliant safety design or avoid removing protective features."
    return "Revise mutation to be lawful, plausible, and supported by product facts."
