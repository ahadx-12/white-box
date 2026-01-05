from __future__ import annotations

from trustai_core.packs.tariff.mutations.models import MutationCandidate


def can_compose(sequence: list[MutationCandidate], candidate: MutationCandidate) -> tuple[bool, str | None]:
    incompat_reason = _check_composable_with(sequence, candidate)
    if incompat_reason:
        return False, incompat_reason

    conflict_reason = _check_conflicts(sequence, candidate)
    if conflict_reason:
        return False, conflict_reason
    return True, None


def _check_composable_with(sequence: list[MutationCandidate], candidate: MutationCandidate) -> str | None:
    for existing in sequence:
        if existing.composable_with is not None and candidate.operator_id not in existing.composable_with:
            return f"incompatible: {existing.operator_id} cannot compose with {candidate.operator_id}"
        if candidate.composable_with is not None and existing.operator_id not in candidate.composable_with:
            return f"incompatible: {candidate.operator_id} cannot compose with {existing.operator_id}"
    return None


def _check_conflicts(sequence: list[MutationCandidate], candidate: MutationCandidate) -> str | None:
    touch_paths = set(candidate.touch_paths or [])
    if _touches_sold_as_set(candidate):
        touch_paths.add("packaging.sold_as_set")
    for existing in sequence:
        existing_paths = set(existing.touch_paths or [])
        if _touches_sold_as_set(existing):
            existing_paths.add("packaging.sold_as_set")
        if _components_split_conflict(existing, candidate):
            return f"conflict:components split by {existing.operator_id} and {candidate.operator_id}"
        overlap = sorted(touch_paths.intersection(existing_paths))
        if overlap:
            path = overlap[0]
            return f"conflict:path {path} touched by {existing.operator_id} and {candidate.operator_id}"
    return None


def _touches_sold_as_set(candidate: MutationCandidate) -> bool:
    for diff in candidate.diff:
        if diff.path in {"packaging.sold_as_set", "sold_as_set"}:
            return True
    return False


def _components_split_conflict(existing: MutationCandidate, candidate: MutationCandidate) -> bool:
    return _has_component_split(existing) and _has_component_split(candidate)


def _has_component_split(candidate: MutationCandidate) -> bool:
    for diff in candidate.diff:
        if diff.path == "components" and diff.op == "split":
            return True
    return False
