from pathlib import Path

import pytest
from trustai_core.core.algebra import cosine_similarity
from trustai_core.core.memory import ItemMemory, ItemMemoryConfig
from trustai_core.packs.loader import load_pack
from trustai_core.utils.canonicalize import canonicalize_token


def test_opposites_anchored():
    memory = ItemMemory(ItemMemoryConfig())
    pack = load_pack("general", memory, storage_root=Path("storage/packs"))
    safe_v = memory.get("safe")
    unsafe_v = memory.get("unsafe")
    assert cosine_similarity(safe_v, unsafe_v) == pytest.approx(-1.0, abs=1e-6)
    assert pack.ontology.opposites


def test_alias_mapping():
    memory = ItemMemory(ItemMemoryConfig())
    pack = load_pack("general", memory, storage_root=Path("storage/packs"))
    assert canonicalize_token("hazardous", pack.ontology.aliases) == "unsafe"
