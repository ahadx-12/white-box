from __future__ import annotations

from trustai_core.schemas.atoms import AtomModel
from trustai_core.schemas.proof import MismatchReport


def _format_atoms(atoms: list[AtomModel]) -> str:
    if not atoms:
        return "- none"
    lines = [f"- ({atom.subject}, {atom.predicate}, {atom.obj}, {atom.is_true})" for atom in atoms]
    return "\n".join(lines)


def build_feedback(mismatch: MismatchReport) -> str:
    parts = [
        f"Score: {mismatch.score:.4f} (threshold {mismatch.threshold:.2f})",
        "Unsupported claims:",
        _format_atoms(mismatch.unsupported_claims),
        "Missing evidence:",
        _format_atoms(mismatch.missing_evidence),
        "Ontology conflicts:",
    ]
    if mismatch.ontology_conflicts:
        parts.extend([f"- {item}" for item in mismatch.ontology_conflicts])
    else:
        parts.append("- none")
    return "\n".join(parts)
