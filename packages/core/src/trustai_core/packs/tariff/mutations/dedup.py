from __future__ import annotations

import hashlib
import json
from typing import Any

from trustai_core.packs.tariff.mutations.models import ProductDossier


def canonicalize_product_dossier(dossier: ProductDossier) -> dict[str, Any]:
    return _canonicalize(dossier.model_dump(), path="")


def _canonicalize(value: Any, path: str) -> Any:
    if isinstance(value, dict):
        return {key: _canonicalize(value[key], _extend(path, key)) for key in sorted(value.keys())}
    if isinstance(value, list):
        if path.endswith("components"):
            items = [_canonicalize(item, _extend(path, "[]")) for item in value]
            return sorted(items, key=_component_sort_key)
        if path.endswith("upper_materials") or path.endswith("outsole_materials"):
            items = [_canonicalize(item, _extend(path, "[]")) for item in value]
            return sorted(items, key=lambda item: str(item.get("material", "")).lower())
        return [_canonicalize(item, _extend(path, "[]")) for item in value]
    return value


def _extend(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def _component_sort_key(item: dict[str, Any]) -> tuple[str, str, str]:
    name = str(item.get("name", "")).lower()
    comp_type = str(item.get("component_type", "")).lower()
    material = str(item.get("material", "")).lower()
    return (name, comp_type, material)


def state_hash(dossier: ProductDossier) -> str:
    canonical = canonicalize_product_dossier(dossier)
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
