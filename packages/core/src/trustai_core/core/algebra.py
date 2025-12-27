from __future__ import annotations

from typing import Iterable

import torch


def bind(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    return a * b


def bundle(vectors: Iterable[torch.Tensor]) -> torch.Tensor:
    stacked = torch.stack(list(vectors), dim=0)
    summed = stacked.sum(dim=0)
    pos = torch.tensor(1.0, device=summed.device)
    neg = torch.tensor(-1.0, device=summed.device)
    return torch.where(summed >= 0, pos, neg)


def bundle_batch(vectors: torch.Tensor) -> torch.Tensor:
    summed = vectors.sum(dim=0)
    pos = torch.tensor(1.0, device=summed.device)
    neg = torch.tensor(-1.0, device=summed.device)
    return torch.where(summed >= 0, pos, neg)


def cosine_similarity(a: torch.Tensor, b: torch.Tensor, eps: float = 1e-8) -> float:
    dot = torch.dot(a, b)
    denom = torch.norm(a) * torch.norm(b) + eps
    return (dot / denom).item()
