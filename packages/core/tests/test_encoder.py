from trustai_core.core.algebra import cosine_similarity
from trustai_core.core.encoder import AtomEncoder
from trustai_core.core.memory import ItemMemory, ItemMemoryConfig
from trustai_core.schemas.atoms import AtomModel


def test_order_sensitivity():
    memory = ItemMemory(ItemMemoryConfig())
    encoder = AtomEncoder(memory)
    atom_ab = AtomModel(subject="a", predicate="kills", obj="b", is_true=True, confidence=1.0)
    atom_ba = AtomModel(subject="b", predicate="kills", obj="a", is_true=True, confidence=1.0)
    v_ab = encoder.encode_atom(atom_ab)
    v_ba = encoder.encode_atom(atom_ba)
    assert cosine_similarity(v_ab, v_ba) < 0.2


def test_manifest_shuffle_invariance():
    memory = ItemMemory(ItemMemoryConfig())
    encoder = AtomEncoder(memory)
    atoms = [
        AtomModel(subject="door", predicate="state", obj="open", is_true=True, confidence=1.0),
        AtomModel(subject="door", predicate="color", obj="red", is_true=True, confidence=1.0),
    ]
    vec_a = encoder.encode_manifest(atoms)
    vec_b = encoder.encode_manifest(list(reversed(atoms)))
    assert (vec_a == vec_b).all()
