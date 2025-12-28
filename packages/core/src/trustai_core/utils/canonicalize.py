from __future__ import annotations

from typing import Iterable

from trustai_core.schemas.atoms import AtomModel


def normalize_token(token: str) -> str:
    return token.strip().lower().replace(" ", "_")


def canonicalize_token(token: str, aliases: dict[str, str] | None = None) -> str:
    normalized = normalize_token(token)
    if aliases and normalized in aliases:
        return aliases[normalized]
    return normalized


def canonicalize_atom(atom: AtomModel, aliases: dict[str, str] | None = None) -> AtomModel:
    return AtomModel(
        subject=canonicalize_token(atom.subject, aliases),
        predicate=canonicalize_token(atom.predicate, aliases),
        obj=canonicalize_token(atom.obj, aliases),
        is_true=atom.is_true,
        confidence=atom.confidence,
        source_span=atom.source_span,
        type=atom.type,
    )


def sort_atoms(atoms: Iterable[AtomModel]) -> list[AtomModel]:
    return sorted(atoms, key=lambda item: item.sort_key())
