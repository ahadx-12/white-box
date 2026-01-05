from __future__ import annotations

from trustai_core.packs.tariff.models import GriStep, GriTrace

GRI_ORDER = [
    GriStep.GRI_1,
    GriStep.GRI_2,
    GriStep.GRI_3,
    GriStep.GRI_4,
    GriStep.GRI_5,
    GriStep.GRI_6,
]


def validate_gri_sequence(gri_trace: GriTrace | None) -> tuple[bool, list[str]]:
    if gri_trace is None:
        return False, ["missing_gri_trace"]
    violations: list[str] = []
    if [step.step for step in gri_trace.steps] != GRI_ORDER:
        violations.append("GRI steps must be ordered GRI_1 through GRI_6")
    if gri_trace.step_vector and len(gri_trace.step_vector) != len(GRI_ORDER):
        violations.append("Step vector must include 6 entries")
    applied_indices = [i for i, step in enumerate(gri_trace.steps) if step.applied]
    if applied_indices:
        first_applied = applied_indices[0]
        for idx in range(first_applied):
            if gri_trace.steps[idx].applied:
                violations.append(
                    f"Sequence Violation: {gri_trace.steps[idx].step} applied before "
                    f"{gri_trace.steps[first_applied].step}"
                )
            if not gri_trace.steps[idx].rejected_because:
                violations.append(
                    f"Sequence Violation: {gri_trace.steps[first_applied].step} used before "
                    f"rejecting {gri_trace.steps[idx].step}"
                )
        for idx in range(first_applied + 1, len(gri_trace.steps)):
            if gri_trace.steps[idx].applied:
                violations.append(
                    f"Sequence Violation: {gri_trace.steps[idx].step} applied after "
                    f"{gri_trace.steps[first_applied].step}"
                )
    if gri_trace.step_vector:
        applied_vector = [step.applied for step in gri_trace.steps]
        if applied_vector != gri_trace.step_vector:
            violations.append("Step vector does not match applied steps")
    return (not violations), violations[:10]
