from __future__ import annotations

from dataclasses import dataclass

import torch

from trustai_core.utils.hashing import stable_token_seed


@dataclass(frozen=True)
class ItemMemoryConfig:
    dim: int = 10000
    seed: int = 1337


class ItemMemory:
    def __init__(self, config: ItemMemoryConfig | None = None) -> None:
        self.config = config or ItemMemoryConfig()
        self._store: dict[str, torch.Tensor] = {}

    def _generate_vector(self, token: str) -> torch.Tensor:
        token_seed = stable_token_seed(token)
        seed = (self.config.seed + token_seed) % 2**32
        generator = torch.Generator(device="cpu")
        generator.manual_seed(seed)
        bits = torch.randint(0, 2, (self.config.dim,), generator=generator, dtype=torch.int8)
        vector = torch.where(bits == 0, torch.tensor(-1.0), torch.tensor(1.0))
        return vector

    def get(self, token: str) -> torch.Tensor:
        if token not in self._store:
            self._store[token] = self._generate_vector(token)
        return self._store[token]

    def set(self, token: str, vector: torch.Tensor) -> None:
        self._store[token] = self._ensure_bipolar(vector)

    def _ensure_bipolar(self, vector: torch.Tensor) -> torch.Tensor:
        cleaned = torch.where(vector >= 0, torch.tensor(1.0), torch.tensor(-1.0))
        return cleaned

    def export_matrix(self) -> torch.Tensor:
        if not self._store:
            return torch.empty((0, self.config.dim))
        tokens = sorted(self._store)
        vectors = [self._store[token] for token in tokens]
        return torch.stack(vectors, dim=0)
