from __future__ import annotations

import math
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import orjson

from trustai_core.utils.hashing import stable_token_seed


HDC_DIMENSION = 10000
COMPOSITION_MIN_WEIGHT = 1e-6


@dataclass(frozen=True)
class HDCScore:
    similarity: float
    drift: float


@lru_cache(maxsize=2048)
def _token_vector(token: str, dim: int = HDC_DIMENSION) -> list[int]:
    seed = stable_token_seed(token)
    state = seed
    vector = [0] * dim
    for i in range(dim):
        state ^= (state << 13) & 0xFFFFFFFF
        state ^= (state >> 17) & 0xFFFFFFFF
        state ^= (state << 5) & 0xFFFFFFFF
        vector[i] = 1 if state & 1 else -1
    return vector


def bundle_tokens(tokens: list[str], dim: int = HDC_DIMENSION) -> list[int]:
    if not tokens:
        return [0] * dim
    bundle = [0] * dim
    for token in tokens:
        vec = _token_vector(token, dim)
        for i, value in enumerate(vec):
            bundle[i] += value
    return bundle


def cosine_similarity(vec_a: list[int], vec_b: list[int]) -> float:
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vec_a, vec_b, strict=True):
        dot += a * b
        norm_a += a * a
        norm_b += b * b
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / math.sqrt(norm_a * norm_b)


def compare_bundles(previous: list[int] | None, current: list[int]) -> HDCScore:
    if previous is None:
        return HDCScore(similarity=1.0, drift=0.0)
    similarity = cosine_similarity(previous, current)
    drift = 1.0 - similarity
    return HDCScore(similarity=similarity, drift=drift)


@lru_cache(maxsize=1)
def _load_tariff_ontology() -> dict[str, Any]:
    root = Path(os.getenv("TRUSTAI_PACKS_ROOT", "storage/packs"))
    path = root / "tariff" / "ontology.json"
    if not path.exists():
        return {"aliases": {}, "material_axes": [], "component_axes": [], "mutex_sets": []}
    return orjson.loads(path.read_bytes())


def normalize_component_name(name: str) -> str:
    normalized = name.strip().lower()
    ontology = _load_tariff_ontology()
    aliases = ontology.get("aliases", {}) or {}
    return aliases.get(normalized, normalized)


def _component_axes() -> list[str]:
    ontology = _load_tariff_ontology()
    axes = list(ontology.get("material_axes", []) or [])
    axes.extend(ontology.get("component_axes", []) or [])
    if "other" not in axes:
        axes.append("other")
    return axes


def tariff_mutex_sets() -> list[list[str]]:
    ontology = _load_tariff_ontology()
    return list(ontology.get("mutex_sets", []) or [])


def _axis_vector(axis: str, axes: list[str]) -> list[float]:
    vector = [0.0] * len(axes)
    if axis in axes:
        vector[axes.index(axis)] = 1.0
    else:
        vector[axes.index("other")] = 1.0
    return vector


def build_composition_vector(components: list[dict[str, Any]]) -> list[float]:
    axes = _component_axes()
    if not components:
        return [0.0] * len(axes)
    vector = [0.0] * len(axes)
    total_weight = 0.0
    for component in components:
        name = normalize_component_name(str(component.get("name", "")))
        pct = component.get("pct")
        cost_pct = component.get("cost_pct")
        mass_pct = component.get("mass_pct")
        weight = pct if pct is not None else cost_pct if cost_pct is not None else mass_pct
        if weight is None:
            weight = 0.0
        weight = float(weight)
        total_weight += weight
        axis = "other"
        for candidate in axes:
            if candidate != "other" and candidate in name:
                axis = candidate
                break
        axis_vector = _axis_vector(axis, axes)
        for i, value in enumerate(axis_vector):
            vector[i] += value * weight
    if total_weight <= COMPOSITION_MIN_WEIGHT:
        return vector
    return [value / total_weight for value in vector]


def essential_character_score(claim_vector: list[float], composition_vector: list[float]) -> float:
    if not claim_vector or not composition_vector:
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(claim_vector, composition_vector, strict=True):
        dot += a * b
        norm_a += a * a
        norm_b += b * b
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / math.sqrt(norm_a * norm_b)
