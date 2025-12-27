import torch
from trustai_core.core.memory import ItemMemory, ItemMemoryConfig
from trustai_core.core.permutation import permute, unpermute


def test_unpermute_round_trip():
    memory = ItemMemory(ItemMemoryConfig())
    v = memory.get("vector")
    assert torch.equal(unpermute(permute(v, 3), 3), v)


def test_permutation_changes_vector():
    memory = ItemMemory(ItemMemoryConfig())
    v = memory.get("vector")
    assert not torch.equal(permute(v, 1), v)
