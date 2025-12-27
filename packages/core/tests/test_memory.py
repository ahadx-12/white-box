from trustai_core.core.algebra import cosine_similarity
from trustai_core.core.memory import ItemMemory, ItemMemoryConfig


def test_determinism_across_instances():
    config = ItemMemoryConfig(seed=1337)
    a = ItemMemory(config).get("x")
    b = ItemMemory(config).get("x")
    assert (a == b).all()


def test_different_tokens_not_identical():
    memory = ItemMemory(ItemMemoryConfig())
    vectors = [memory.get(f"token_{i}") for i in range(200)]
    cosines = [cosine_similarity(vectors[i], vectors[i + 1]) for i in range(len(vectors) - 1)]
    mean_cos = sum(cosines) / len(cosines)
    assert abs(mean_cos) < 0.05
