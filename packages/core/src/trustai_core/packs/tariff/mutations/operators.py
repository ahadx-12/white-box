from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from trustai_core.packs.tariff.mutations.models import (
    MutationBounds,
    MutationCandidate,
    ProductDiff,
    ProductDossier,
)


@dataclass(frozen=True)
class MutationOperator:
    operator_id: str
    label: str
    category: str
    required_inputs: list[str]
    assumptions: list[str]
    bounds: MutationBounds
    compliance_framing: str

    def generate(self, dossier: ProductDossier) -> list[MutationCandidate]:
        raise NotImplementedError

    def _has_required_inputs(self, dossier: ProductDossier) -> bool:
        for key in self.required_inputs:
            if _get_value(dossier, key) is None:
                return False
        return True

    def _candidate(self, diff: list[ProductDiff]) -> MutationCandidate:
        return MutationCandidate(
            operator_id=self.operator_id,
            label=self.label,
            category=self.category,
            required_inputs=self.required_inputs,
            diff=diff,
            assumptions=self.assumptions,
            bounds=self.bounds,
            compliance_framing=self.compliance_framing,
        )


class UpperMaterialShiftOperator(MutationOperator):
    def generate(self, dossier: ProductDossier) -> list[MutationCandidate]:
        if not self._has_required_inputs(dossier):
            return []
        materials = [
            share for share in dossier.upper_materials if share.material and share.pct is not None
        ]
        if len(materials) < 2:
            return []
        materials_sorted = sorted(materials, key=lambda item: (-item.pct, item.material))
        primary = materials_sorted[0]
        secondary = materials_sorted[1]
        delta = min(0.1, primary.pct * 0.25)
        if delta <= 0:
            return []
        diff = [
            ProductDiff(
                path=f"upper_materials.{primary.material}",
                from_value=primary.pct,
                to_value=round(primary.pct - delta, 4),
                details={"material_delta_pct": round(delta, 4)},
            ),
            ProductDiff(
                path=f"upper_materials.{secondary.material}",
                from_value=secondary.pct,
                to_value=round(secondary.pct + delta, 4),
                details={"material_delta_pct": round(delta, 4)},
            ),
        ]
        return [self._candidate(diff)]


class OutsoleMaterialShiftOperator(MutationOperator):
    def generate(self, dossier: ProductDossier) -> list[MutationCandidate]:
        if not self._has_required_inputs(dossier):
            return []
        materials = [
            share for share in dossier.outsole_materials if share.material and share.pct is not None
        ]
        if len(materials) < 2:
            return []
        materials_sorted = sorted(materials, key=lambda item: (-item.pct, item.material))
        primary = materials_sorted[0]
        secondary = materials_sorted[1]
        delta = min(0.08, primary.pct * 0.2)
        if delta <= 0:
            return []
        diff = [
            ProductDiff(
                path=f"outsole_materials.{primary.material}",
                from_value=primary.pct,
                to_value=round(primary.pct - delta, 4),
                details={"material_delta_pct": round(delta, 4)},
            ),
            ProductDiff(
                path=f"outsole_materials.{secondary.material}",
                from_value=secondary.pct,
                to_value=round(secondary.pct + delta, 4),
                details={"material_delta_pct": round(delta, 4)},
            ),
        ]
        return [self._candidate(diff)]


class RemoveMetalToeOperator(MutationOperator):
    def generate(self, dossier: ProductDossier) -> list[MutationCandidate]:
        if not self._has_required_inputs(dossier):
            return []
        if not dossier.has_metal_toe:
            return []
        diff = [
            ProductDiff(
                path="features.has_metal_toe",
                from_value=True,
                to_value=False,
                details={"component_removal_pct": 0.1},
            )
        ]
        return [self._candidate(diff)]


class SplitSetComponentsOperator(MutationOperator):
    def generate(self, dossier: ProductDossier) -> list[MutationCandidate]:
        if not self._has_required_inputs(dossier):
            return []
        if not dossier.sold_as_set:
            return []
        if len(dossier.components) < 2:
            return []
        diff = [
            ProductDiff(
                path="packaging.sold_as_set",
                from_value=True,
                to_value=False,
                details={"components_split": [component.name for component in dossier.components]},
            ),
            ProductDiff(
                path="components",
                op="split",
                details={"split_count": len(dossier.components)},
            ),
        ]
        return [self._candidate(diff)]


class ConnectorMaterialChangeOperator(MutationOperator):
    def generate(self, dossier: ProductDossier) -> list[MutationCandidate]:
        if not self._has_required_inputs(dossier):
            return []
        current = (dossier.connector_material or "").lower()
        if not current:
            return []
        target = "plastic" if "metal" in current else "metal"
        diff = [
            ProductDiff(
                path="connector.material",
                from_value=dossier.connector_material,
                to_value=target,
                details={"material_delta_pct": 0.05},
            )
        ]
        return [self._candidate(diff)]


class AdapterHousingMaterialOperator(MutationOperator):
    def generate(self, dossier: ProductDossier) -> list[MutationCandidate]:
        if not self._has_required_inputs(dossier):
            return []
        current = (dossier.adapter_housing_material or "").lower()
        if not current:
            return []
        target = "plastic" if "metal" in current else "metal"
        diff = [
            ProductDiff(
                path="adapter_housing.material",
                from_value=dossier.adapter_housing_material,
                to_value=target,
                details={"material_delta_pct": 0.08, "cost_delta_pct": 0.12},
            )
        ]
        return [self._candidate(diff)]


class MaterialGradeShiftOperator(MutationOperator):
    def generate(self, dossier: ProductDossier) -> list[MutationCandidate]:
        if not self._has_required_inputs(dossier):
            return []
        current = (dossier.material_grade or "").lower()
        if not current:
            return []
        if "stainless" in current:
            target = "carbon steel"
        elif "carbon" in current:
            target = "stainless steel"
        else:
            target = "stainless steel"
        diff = [
            ProductDiff(
                path="material.grade",
                from_value=dossier.material_grade,
                to_value=target,
                details={"material_delta_pct": 0.12, "cost_delta_pct": 0.15},
            )
        ]
        return [self._candidate(diff)]


class FinishChangeOperator(MutationOperator):
    def generate(self, dossier: ProductDossier) -> list[MutationCandidate]:
        if not self._has_required_inputs(dossier):
            return []
        current = (dossier.finish or "").lower()
        if not current:
            return []
        target = "plated" if "plain" in current or "uncoated" in current else "plain"
        diff = [
            ProductDiff(
                path="finish",
                from_value=dossier.finish,
                to_value=target,
                details={"cost_delta_pct": 0.05},
            )
        ]
        return [self._candidate(diff)]


class ComponentSeparationOperator(MutationOperator):
    def generate(self, dossier: ProductDossier) -> list[MutationCandidate]:
        if not self._has_required_inputs(dossier):
            return []
        if not dossier.sold_as_set:
            return []
        types = {component.component_type for component in dossier.components}
        if "motor" not in types or "pump" not in types:
            return []
        diff = [
            ProductDiff(
                path="packaging.sold_as_set",
                from_value=True,
                to_value=False,
                details={"components_split": sorted([type_name for type_name in types if type_name])},
            ),
            ProductDiff(
                path="components",
                op="split",
                details={"split_count": len(dossier.components)},
            ),
        ]
        return [self._candidate(diff)]


class HousingMaterialChangeOperator(MutationOperator):
    def generate(self, dossier: ProductDossier) -> list[MutationCandidate]:
        if not self._has_required_inputs(dossier):
            return []
        current = (dossier.housing_material or "").lower()
        if not current:
            return []
        target = "plastic" if "iron" in current else "cast iron"
        diff = [
            ProductDiff(
                path="housing.material",
                from_value=dossier.housing_material,
                to_value=target,
                details={"material_delta_pct": 0.15, "cost_delta_pct": 0.18},
            )
        ]
        return [self._candidate(diff)]


class ImpellerMaterialShiftOperator(MutationOperator):
    def generate(self, dossier: ProductDossier) -> list[MutationCandidate]:
        if not self._has_required_inputs(dossier):
            return []
        impellers = [
            component
            for component in dossier.components
            if (component.component_type or "").lower() == "impeller" and component.material
        ]
        if not impellers:
            return []
        current = impellers[0].material or ""
        target = "plastic" if "metal" in current.lower() else "metal"
        diff = [
            ProductDiff(
                path="components.impeller.material",
                from_value=current,
                to_value=target,
                details={"material_delta_pct": 0.1, "cost_delta_pct": 0.12},
            )
        ]
        return [self._candidate(diff)]


def build_default_operators() -> list[MutationOperator]:
    compliance = "Design/packaging change; not a declaration change."
    return [
        UpperMaterialShiftOperator(
            operator_id="op64_upper_material_shift",
            label="Shift upper material mix toward secondary textile",
            category="material",
            required_inputs=["upper_materials"],
            assumptions=["Upper material mix can be adjusted without altering intended use."],
            bounds=MutationBounds(max_cost_delta=0.2, max_material_delta=0.3),
            compliance_framing=compliance,
        ),
        OutsoleMaterialShiftOperator(
            operator_id="op64_outsole_material_shift",
            label="Shift outsole material mix toward secondary material",
            category="material",
            required_inputs=["outsole_materials"],
            assumptions=["Outsole material mix can change without compromising durability."],
            bounds=MutationBounds(max_cost_delta=0.15, max_material_delta=0.25),
            compliance_framing=compliance,
        ),
        RemoveMetalToeOperator(
            operator_id="op64_remove_metal_toe",
            label="Remove metal toe safety feature",
            category="construction",
            required_inputs=["has_metal_toe"],
            assumptions=["Safety rating can be adjusted with alternate protection."],
            bounds=MutationBounds(max_cost_delta=0.1, max_material_delta=0.2, max_component_removal=0.2),
            compliance_framing=compliance,
        ),
        SplitSetComponentsOperator(
            operator_id="op85_split_set_components",
            label="Separate set components into distinct retail items",
            category="packaging",
            required_inputs=["sold_as_set", "components"],
            assumptions=["Items can be sold separately without changing consumer use."],
            bounds=MutationBounds(max_cost_delta=0.2, max_material_delta=0.3),
            compliance_framing="Design/packaging change; not a declaration change.",
        ),
        ConnectorMaterialChangeOperator(
            operator_id="op85_change_connector_material",
            label="Change connector material composition",
            category="material",
            required_inputs=["connector_material"],
            assumptions=["Connector material can shift within performance specs."],
            bounds=MutationBounds(max_cost_delta=0.15, max_material_delta=0.2),
            compliance_framing=compliance,
        ),
        AdapterHousingMaterialOperator(
            operator_id="op85_adapter_housing_material",
            label="Adjust adapter housing material",
            category="material",
            required_inputs=["adapter_housing_material"],
            assumptions=["Housing material can shift with equivalent safety rating."],
            bounds=MutationBounds(max_cost_delta=0.2, max_material_delta=0.25),
            compliance_framing=compliance,
        ),
        MaterialGradeShiftOperator(
            operator_id="op73_material_grade_shift",
            label="Shift fastener material grade",
            category="material",
            required_inputs=["material_grade"],
            assumptions=["Material grade change is feasible with engineering approval."],
            bounds=MutationBounds(max_cost_delta=0.2, max_material_delta=0.25),
            compliance_framing=compliance,
        ),
        FinishChangeOperator(
            operator_id="op73_finish_change",
            label="Change surface finish or coating",
            category="construction",
            required_inputs=["finish"],
            assumptions=["Finish change does not affect regulatory performance requirements."],
            bounds=MutationBounds(max_cost_delta=0.1, max_material_delta=0.1),
            compliance_framing=compliance,
        ),
        ComponentSeparationOperator(
            operator_id="op84_component_separation",
            label="Separate pump and motor into distinct items",
            category="assembly",
            required_inputs=["sold_as_set", "components"],
            assumptions=["Pump and motor can ship separately without changing function."],
            bounds=MutationBounds(max_cost_delta=0.2, max_material_delta=0.2),
            compliance_framing="Design/assembly change; not a declaration change.",
        ),
        HousingMaterialChangeOperator(
            operator_id="op84_material_housing_change",
            label="Change pump housing material",
            category="material",
            required_inputs=["housing_material"],
            assumptions=["Housing material can change while preserving performance."],
            bounds=MutationBounds(max_cost_delta=0.25, max_material_delta=0.3),
            compliance_framing=compliance,
        ),
        ImpellerMaterialShiftOperator(
            operator_id="op84_impeller_material_shift",
            label="Shift impeller material",
            category="material",
            required_inputs=["components"],
            assumptions=["Impeller material change maintains pump performance."],
            bounds=MutationBounds(max_cost_delta=0.2, max_material_delta=0.2),
            compliance_framing=compliance,
        ),
    ]


def _get_value(dossier: ProductDossier, key: str) -> Any:
    if not key:
        return None
    if hasattr(dossier, key):
        return getattr(dossier, key)
    data = dossier.model_dump()
    parts = key.split(".")
    current: Any = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current
