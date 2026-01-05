from __future__ import annotations

from typing import Any

from trustai_core.packs.tariff.mutations.models import MutationCandidate, ProductDossier


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
