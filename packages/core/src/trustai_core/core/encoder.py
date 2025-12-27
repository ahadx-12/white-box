from __future__ import annotations

import torch

from trustai_core.core.algebra import bundle
from trustai_core.core.memory import ItemMemory
from trustai_core.core.permutation import permute
from trustai_core.schemas.atoms import AtomModel


class AtomEncoder:
    def __init__(self, memory: ItemMemory) -> None:
        self.memory = memory

    def encode_atom(self, atom: AtomModel) -> torch.Tensor:
        subject_v = permute(self.memory.get(atom.subject), 1)
        predicate_v = permute(self.memory.get(atom.predicate), 2)
        object_v = permute(self.memory.get(atom.obj), 3)
        truth_token = "TRUE" if atom.is_true else "FALSE"
        truth_v = permute(self.memory.get(truth_token), 4)
        return subject_v * predicate_v * object_v * truth_v

    def encode_manifest(self, atoms: list[AtomModel]) -> torch.Tensor:
        if not atoms:
            return self.memory.get("__EMPTY__")
        vectors = [self.encode_atom(atom) for atom in atoms]
        return bundle(vectors)
