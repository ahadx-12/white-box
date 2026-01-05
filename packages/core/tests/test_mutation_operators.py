from __future__ import annotations

from trustai_core.packs.tariff.mutations.models import ProductDossier
from trustai_core.packs.tariff.mutations.operators import build_default_operators


def test_operator_diffs_deterministic() -> None:
    dossier = ProductDossier(
        product_id="FW-100",
        product_summary="Athletic footwear",
        upper_materials=[
            {"material": "textile", "pct": 60.0},
            {"material": "leather", "pct": 40.0},
        ],
        outsole_materials=[
            {"material": "rubber", "pct": 70.0},
            {"material": "textile", "pct": 30.0},
        ],
        sold_as_set=True,
        components=[
            {"name": "Adapter", "component_type": "adapter", "material": "plastic"},
            {"name": "Cable", "component_type": "cable", "material": "copper"},
        ],
        connector_material="metal",
        adapter_housing_material="metal",
        material_grade="carbon steel",
        finish="plain",
        housing_material="cast iron",
    )

    operators = build_default_operators()
    first = [candidate.model_dump() for op in operators for candidate in op.generate(dossier)]
    second = [candidate.model_dump() for op in operators for candidate in op.generate(dossier)]

    assert first == second
