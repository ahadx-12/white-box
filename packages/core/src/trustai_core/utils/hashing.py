from __future__ import annotations

import hashlib
from typing import Any

import orjson

FNV_OFFSET_BASIS_32 = 2166136261
FNV_PRIME_32 = 16777619


def stable_token_seed(token: str) -> int:
    """Return a stable 32-bit FNV-1a hash for a token."""
    data = token.encode("utf-8")
    hash_value = FNV_OFFSET_BASIS_32
    for byte in data:
        hash_value ^= byte
        hash_value = (hash_value * FNV_PRIME_32) % 2**32
    return hash_value


def sha256_canonical_json(obj: Any) -> str:
    """Return SHA256 hex digest of canonical JSON serialization."""
    payload = orjson.dumps(obj, option=orjson.OPT_SORT_KEYS)
    return hashlib.sha256(payload).hexdigest()
