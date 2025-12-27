from __future__ import annotations

from pathlib import Path
from typing import Any

import orjson

from trustai_core.core.memory import ItemMemory
from trustai_core.packs.types import OntologyModel, PackModel
from trustai_core.schemas.atoms import AtomModel
from trustai_core.utils.canonicalize import canonicalize_atom, canonicalize_token, normalize_token
from trustai_core.utils.hashing import sha256_canonical_json


def _load_json(path: Path) -> Any:
    return orjson.loads(path.read_bytes())


def load_pack(pack_name: str, memory: ItemMemory, storage_root: Path | None = None) -> PackModel:
    root = storage_root or Path("storage/packs")
    pack_path = root / pack_name
    ontology_path = pack_path / "ontology.json"
    axioms_path = pack_path / "axioms.json"

    ontology_raw = _load_json(ontology_path)
    axioms_raw = _load_json(axioms_path)

    aliases = {
        normalize_token(k): normalize_token(v)
        for k, v in ontology_raw.get("aliases", {}).items()
    }
    opposites = [
        [canonicalize_token(item[0], aliases), canonicalize_token(item[1], aliases)]
        for item in ontology_raw.get("opposites", [])
    ]
    mutex_sets = [
        [canonicalize_token(token, aliases) for token in mutex]
        for mutex in ontology_raw.get("mutex_sets", [])
    ]

    axioms = [
        canonicalize_atom(AtomModel(**atom), aliases)
        for atom in axioms_raw
    ]

    for left, right in opposites:
        anchor = min(left, right)
        other = right if anchor == left else left
        base = memory.get(anchor)
        memory.set(other, -base)

    canonical_ontology = {
        "aliases": aliases,
        "opposites": [sorted(pair) for pair in opposites],
        "mutex_sets": [sorted(mutex) for mutex in mutex_sets],
    }
    canonical_axioms = [atom.model_dump() for atom in axioms]
    fingerprint = sha256_canonical_json(
        {"ontology": canonical_ontology, "axioms": canonical_axioms}
    )

    return PackModel(
        name=pack_name,
        ontology=OntologyModel(
            opposites=opposites,
            mutex_sets=mutex_sets,
            aliases=aliases,
        ),
        axioms=axioms,
        fingerprint=fingerprint,
    )
