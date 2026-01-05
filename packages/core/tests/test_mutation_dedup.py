from __future__ import annotations

from trustai_core.packs.tariff.mutations.dedup import state_hash
from trustai_core.packs.tariff.mutations.models import ProductDossier


def test_state_hash_stable_with_component_order() -> None:
    dossier_a = ProductDossier(
        product_summary="Test product",
        components=[
            {"name": "Motor", "component_type": "motor", "material": "steel"},
            {"name": "Pump", "component_type": "pump", "material": "plastic"},
        ],
        upper_materials=[
            {"material": "textile", "pct": 60.0},
            {"material": "leather", "pct": 40.0},
        ],
    )
    dossier_b = ProductDossier(
        product_summary="Test product",
        components=[
            {"name": "Pump", "component_type": "pump", "material": "plastic"},
            {"name": "Motor", "component_type": "motor", "material": "steel"},
        ],
        upper_materials=[
            {"material": "leather", "pct": 40.0},
            {"material": "textile", "pct": 60.0},
        ],
    )
    assert state_hash(dossier_a) == state_hash(dossier_b)
