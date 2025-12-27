from pathlib import Path

from trustai_core.arbiter.evaluator import SCORE_THRESHOLD, evaluate
from trustai_core.core.encoder import AtomEncoder
from trustai_core.core.memory import ItemMemory, ItemMemoryConfig
from trustai_core.packs.loader import load_pack
from trustai_core.schemas.atoms import AtomModel


def test_contradiction_conflict_detected():
    memory = ItemMemory(ItemMemoryConfig())
    pack = load_pack("general", memory, storage_root=Path("storage/packs"))
    encoder = AtomEncoder(memory)

    evidence = [AtomModel(subject="door", predicate="state", obj="open", is_true=True)]
    claim = [AtomModel(subject="door", predicate="state", obj="closed", is_true=True)]

    mismatch = evaluate(evidence, claim, pack, encoder)
    assert mismatch.score < SCORE_THRESHOLD
    assert mismatch.ontology_conflicts


def test_unsupported_claims_flagged():
    memory = ItemMemory(ItemMemoryConfig())
    pack = load_pack("general", memory, storage_root=Path("storage/packs"))
    encoder = AtomEncoder(memory)

    claim = [AtomModel(subject="sky", predicate="color", obj="green", is_true=True)]
    mismatch = evaluate([], claim, pack, encoder)
    assert mismatch.unsupported_claims
