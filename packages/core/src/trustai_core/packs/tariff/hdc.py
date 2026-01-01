from __future__ import annotations

import math
from functools import lru_cache
from dataclasses import dataclass

from trustai_core.utils.hashing import stable_token_seed


HDC_DIMENSION = 10000


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
