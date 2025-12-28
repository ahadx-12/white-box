from __future__ import annotations

from trustai_core.schemas.atoms import AtomModel
from trustai_core.schemas.proof import MismatchReport


def _format_atoms(atoms: list[AtomModel]) -> str:
    if not atoms:
        return "- none"
    lines = [f"- ({atom.subject}, {atom.predicate}, {atom.obj}, {atom.is_true})" for atom in atoms]
    return "\n".join(lines)


def _format_contradictions(pairs: list) -> str:
    if not pairs:
        return "- none"
    lines = [
        f"- ({pair.left.subject}, {pair.left.predicate}, {pair.left.obj}, {pair.left.is_true}) vs "
        f"({pair.right.subject}, {pair.right.predicate}, {pair.right.obj}, {pair.right.is_true})"
        for pair in pairs
    ]
    return "\n".join(lines)


def build_feedback(mismatch: MismatchReport, force_claims: list[AtomModel] | None = None) -> str:
    force_claims = force_claims or []
    parts = [
        "MUST REMOVE:",
        _format_atoms(mismatch.unsupported_claims),
        "MUST ADD:",
        _format_atoms(mismatch.missing_required + force_claims),
        "CONTRADICTIONS:",
        _format_contradictions(mismatch.contradictions),
        (
            "REWRITE RULE: keep answer consistent with Evidence Atoms; "
            "do not introduce new factual claims."
        ),
    ]
    return "\n".join(parts)
