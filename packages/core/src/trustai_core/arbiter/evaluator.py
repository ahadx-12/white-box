from __future__ import annotations

from collections import defaultdict

import torch

from trustai_core.core.algebra import bundle, cosine_similarity
from trustai_core.core.encoder import AtomEncoder
from trustai_core.packs.types import PackModel
from trustai_core.schemas.atoms import AtomModel
from trustai_core.schemas.proof import MismatchReport
from trustai_core.utils.canonicalize import sort_atoms

CLAIM_SUPPORT_THRESHOLD = 0.2
SCORE_THRESHOLD = 0.92


def _manifest_vector(encoder: AtomEncoder, atoms: list[AtomModel]) -> torch.Tensor:
    if not atoms:
        return encoder.memory.get("__EMPTY__")
    vectors = [encoder.encode_atom(atom) for atom in atoms]
    return bundle(vectors)


def _collect_mutex_pairs(ontology: PackModel) -> set[frozenset[str]]:
    pairs: set[frozenset[str]] = set()
    for left, right in ontology.ontology.opposites:
        pairs.add(frozenset({left, right}))
    for mutex in ontology.ontology.mutex_sets:
        for i in range(len(mutex)):
            for j in range(i + 1, len(mutex)):
                pairs.add(frozenset({mutex[i], mutex[j]}))
    return pairs


def _find_conflicts(atoms: list[AtomModel], ontology: PackModel) -> list[str]:
    mutex_pairs = _collect_mutex_pairs(ontology)
    grouped: dict[tuple[str, str], set[str]] = defaultdict(set)
    for atom in atoms:
        if atom.is_true:
            grouped[(atom.subject, atom.predicate)].add(atom.obj)

    conflicts: set[str] = set()
    for (subject, predicate), objects in grouped.items():
        objects_list = sorted(objects)
        for i, left in enumerate(objects_list):
            for right in objects_list[i + 1 :]:
                if frozenset({left, right}) in mutex_pairs:
                    conflicts.add(f"{subject}:{predicate}:{left}|{right}")

    return sorted(conflicts)


def evaluate(
    evidence_atoms: list[AtomModel],
    claim_atoms: list[AtomModel],
    pack: PackModel,
    encoder: AtomEncoder,
    score_threshold: float = SCORE_THRESHOLD,
    claim_support_threshold: float = CLAIM_SUPPORT_THRESHOLD,
) -> MismatchReport:
    evidence_vectors = evidence_atoms + pack.axioms
    evidence_vector = _manifest_vector(encoder, evidence_vectors)
    claim_vector = _manifest_vector(encoder, claim_atoms)
    score = cosine_similarity(evidence_vector, claim_vector)

    unsupported_claims: list[AtomModel] = []
    for atom in claim_atoms:
        support = cosine_similarity(evidence_vector, encoder.encode_atom(atom))
        if support < claim_support_threshold:
            unsupported_claims.append(atom)

    claim_set = {atom.sort_key() for atom in claim_atoms}
    missing_evidence = [atom for atom in evidence_atoms if atom.sort_key() not in claim_set]

    conflicts = _find_conflicts(claim_atoms, pack)

    return MismatchReport(
        score=score,
        threshold=score_threshold,
        unsupported_claims=sort_atoms(unsupported_claims),
        missing_evidence=sort_atoms(missing_evidence),
        ontology_conflicts=conflicts,
    )
