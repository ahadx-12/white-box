from __future__ import annotations

from trustai_core.packs.tariff.mutations.compose import can_compose
from trustai_core.packs.tariff.mutations.models import MutationBounds, MutationCandidate, ProductDiff


def _candidate(operator_id: str, path: str, op: str = "replace") -> MutationCandidate:
    return MutationCandidate(
        operator_id=operator_id,
        label="test",
        category="material",
        required_inputs=[],
        diff=[ProductDiff(path=path, op=op)],
        assumptions=[],
        bounds=MutationBounds(),
        compliance_framing="Design change",
        touch_paths=[path],
    )


def test_conflict_same_path_rejected() -> None:
    first = _candidate("op_a", "housing.material")
    second = _candidate("op_b", "housing.material")
    ok, reason = can_compose([first], second)
    assert not ok
    assert reason == "conflict:path housing.material touched by op_a and op_b"


def test_component_split_conflict_rejected() -> None:
    first = _candidate("op_a", "components", op="split")
    second = _candidate("op_b", "components", op="split")
    ok, reason = can_compose([first], second)
    assert not ok
    assert reason == "conflict:components split by op_a and op_b"
