import pytest
import torch
from trustai_core.core.algebra import bundle, cosine_similarity
from trustai_core.core.memory import ItemMemory, ItemMemoryConfig


def test_orthogonality_mean_cosine_near_zero():
    memory = ItemMemory(ItemMemoryConfig())
    vectors = [memory.get(f"token_{i}") for i in range(1000)]
    cosines = [cosine_similarity(vectors[i], vectors[i + 1]) for i in range(len(vectors) - 1)]
    mean_cos = sum(cosines) / len(cosines)
    assert abs(mean_cos) < 0.02


def test_bundling_bipolar_no_zeros():
    memory = ItemMemory(ItemMemoryConfig())
    vectors = [memory.get(f"bundle_{i}") for i in range(11)]
    bundled = bundle(vectors)
    assert torch.all((bundled == 1) | (bundled == -1))


def test_cosine_symmetry():
    memory = ItemMemory(ItemMemoryConfig())
    a = memory.get("alpha")
    b = memory.get("beta")
    assert cosine_similarity(a, b) == pytest.approx(cosine_similarity(b, a))
