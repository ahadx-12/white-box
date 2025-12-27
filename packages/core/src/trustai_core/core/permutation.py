from __future__ import annotations

import torch


def permute(vector: torch.Tensor, shift: int) -> torch.Tensor:
    return torch.roll(vector, shifts=shift, dims=0)


def unpermute(vector: torch.Tensor, shift: int) -> torch.Tensor:
    return torch.roll(vector, shifts=-shift, dims=0)
