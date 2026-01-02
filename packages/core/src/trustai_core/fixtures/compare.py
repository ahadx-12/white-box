from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from trustai_core.fixtures.models import FinalIterationSummary, FixtureRecording, GoldenInvariantsSpec

DUTY_RATE_TOLERANCE_PCT = 0.05
TARIFF_CRITICAL_GATES = (
    "gri_sequence_violation",
    "essential_character_mismatch",
    "ontology_mutex_conflict",
    "too_many_what_if_candidates",
    "missing_what_if_candidates",
    "citation_gate_failed",
)


class GoldenInvariantComparison(BaseModel):
    model_config = ConfigDict(frozen=True)

    ok: bool
    reasons: list[str] = Field(default_factory=list)
    recorded: GoldenInvariantsSpec | None = None
    current: GoldenInvariantsSpec | None = None
    current_summary: FinalIterationSummary | None = None


def _extract_final_iteration(payload: dict[str, Any]) -> dict[str, Any] | None:
    iterations = payload.get("iterations") or []
    if iterations:
        return iterations[-1]
    proof = payload.get("proof") or {}
    proof_iterations = proof.get("iterations") or []
    if proof_iterations:
        return proof_iterations[-1]
    return None


def _extract_tariff_dossier(payload: dict[str, Any]) -> dict[str, Any] | None:
    proof = payload.get("proof") or {}
    return proof.get("tariff_dossier") or payload.get("tariff_dossier")


def _extract_tariff_gates(rejected_because: list[str]) -> dict[str, bool]:
    return {gate: gate not in rejected_because for gate in TARIFF_CRITICAL_GATES}


def extract_final_iteration_summary(payload: dict[str, Any]) -> FinalIterationSummary | None:
    iteration = _extract_final_iteration(payload)
    if not iteration:
        return None
    rejected_because = list(iteration.get("rejected_because") or [])
    critical_gates = _extract_tariff_gates(rejected_because)
    return FinalIterationSummary(
        iteration_index=int(iteration.get("i", 0)),
        accepted=bool(iteration.get("accepted", False)),
        rejected_because=rejected_because,
        critical_gates=critical_gates,
    )


def extract_golden_invariants(payload: dict[str, Any]) -> tuple[GoldenInvariantsSpec, FinalIterationSummary | None]:
    summary = extract_final_iteration_summary(payload)
    accepted = summary.accepted if summary else payload.get("status") == "verified"
    rejected_because = summary.rejected_because if summary else []
    dossier = _extract_tariff_dossier(payload) or {}
    baseline = dossier.get("baseline") or {}
    optimized = dossier.get("optimized") or {}
    final_hts = (optimized.get("hts_code") or baseline.get("hts_code") or None)
    duty_rate_pct = (
        optimized.get("duty_rate_pct")
        if optimized.get("duty_rate_pct") is not None
        else baseline.get("duty_rate_pct")
    )
    duty_rate_delta_pct = None
    if baseline.get("duty_rate_pct") is not None and optimized.get("duty_rate_pct") is not None:
        duty_rate_delta_pct = optimized.get("duty_rate_pct") - baseline.get("duty_rate_pct")
    refusal_category = None
    if not accepted:
        refusal_category = rejected_because[0] if rejected_because else "failed"
    critical_gates = summary.critical_gates if summary else {}
    return (
        GoldenInvariantsSpec(
            accepted=accepted,
            final_hts_code=final_hts,
            duty_rate_pct=duty_rate_pct,
            duty_rate_delta_pct=duty_rate_delta_pct,
            critical_gates=critical_gates,
            refusal_category=refusal_category,
        ),
        summary,
    )


def compare_golden_invariants(
    recording: FixtureRecording,
    current_payload: dict[str, Any],
) -> GoldenInvariantComparison:
    recorded = recording.golden_invariants
    current, current_summary = extract_golden_invariants(current_payload)
    reasons: list[str] = []

    if recorded.accepted != current.accepted:
        reasons.append(
            f"acceptance mismatch: recorded={recorded.accepted} current={current.accepted}"
        )

    if recorded.allowed_codes:
        if current.final_hts_code not in recorded.allowed_codes:
            reasons.append(
                "hts code mismatch: "
                f"{current.final_hts_code} not in {recorded.allowed_codes}"
            )
    elif recorded.final_hts_code:
        if current.final_hts_code != recorded.final_hts_code:
            reasons.append(
                f"hts code mismatch: recorded={recorded.final_hts_code} "
                f"current={current.final_hts_code}"
            )

    if recorded.duty_rate_pct is not None:
        if current.duty_rate_pct is None:
            reasons.append("duty rate missing in current run")
        elif abs(current.duty_rate_pct - recorded.duty_rate_pct) > DUTY_RATE_TOLERANCE_PCT:
            reasons.append(
                "duty rate mismatch: "
                f"recorded={recorded.duty_rate_pct} current={current.duty_rate_pct}"
            )

    if recorded.duty_rate_delta_pct is not None:
        if current.duty_rate_delta_pct is None:
            reasons.append("duty rate delta missing in current run")
        elif abs(current.duty_rate_delta_pct - recorded.duty_rate_delta_pct) > DUTY_RATE_TOLERANCE_PCT:
            reasons.append(
                "duty rate delta mismatch: "
                f"recorded={recorded.duty_rate_delta_pct} current={current.duty_rate_delta_pct}"
            )

    for gate_id, expected in recorded.critical_gates.items():
        actual = current.critical_gates.get(gate_id)
        if actual is None:
            reasons.append(f"critical gate missing: {gate_id}")
            continue
        if actual != expected:
            reasons.append(
                f"critical gate mismatch: {gate_id} recorded={expected} current={actual}"
            )

    if recorded.refusal_category and recorded.refusal_category != current.refusal_category:
        reasons.append(
            "refusal category mismatch: "
            f"recorded={recorded.refusal_category} current={current.refusal_category}"
        )

    return GoldenInvariantComparison(
        ok=not reasons,
        reasons=reasons,
        recorded=recorded,
        current=current,
        current_summary=current_summary,
    )
