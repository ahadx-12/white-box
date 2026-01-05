from __future__ import annotations

from trustai_core.packs.tariff.gates.plausibility_gate import run_plausibility_gate
from trustai_core.packs.tariff.mutations.models import MutationBounds, MutationCandidate, ProductDiff, ProductDossier


def test_plausibility_gate_blocks_document_only_changes() -> None:
    candidate = MutationCandidate(
        operator_id="op_doc_only",
        label="Documentation update",
        category="packaging",
        required_inputs=["description"],
        diff=[
            ProductDiff(
                path="description",
                from_value="Old",
                to_value="New",
            )
        ],
        assumptions=["No design change."],
        bounds=MutationBounds(max_cost_delta=0.1, max_material_delta=0.1),
        compliance_framing="Documentation change.",
    )
    dossier = ProductDossier(product_summary="Test product")
    result = run_plausibility_gate(candidate, dossier)
    assert not result.ok
    assert "documentary_change_only" in result.violations


def test_plausibility_gate_blocks_out_of_bounds_material_delta() -> None:
    candidate = MutationCandidate(
        operator_id="op_material_shift",
        label="Material shift",
        category="material",
        required_inputs=["upper_materials"],
        diff=[
            ProductDiff(
                path="upper_materials.textile",
                from_value=0.6,
                to_value=0.3,
                details={"material_delta_pct": 0.3},
            )
        ],
        assumptions=["Shift material content."],
        bounds=MutationBounds(max_cost_delta=0.2, max_material_delta=0.1),
        compliance_framing="Design change; not a declaration change.",
    )
    dossier = ProductDossier(product_summary="Test product")
    result = run_plausibility_gate(candidate, dossier)
    assert not result.ok
    assert "material_delta_exceeds_bounds" in result.violations
