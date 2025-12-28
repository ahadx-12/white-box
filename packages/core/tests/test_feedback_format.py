from __future__ import annotations

from trustai_core.arbiter.feedback import build_feedback
from trustai_core.schemas.atoms import AtomModel
from trustai_core.schemas.proof import ContradictionPair, MismatchReport


def test_feedback_format_includes_patch_instructions() -> None:
    unsupported = AtomModel(
        subject="door",
        predicate="state",
        obj="closed",
        is_true=True,
        confidence=1.0,
    )
    missing = AtomModel(
        subject="door",
        predicate="state",
        obj="open",
        is_true=True,
        confidence=1.0,
    )
    contradiction = ContradictionPair(left=missing, right=unsupported)
    mismatch = MismatchReport(
        score=0.5,
        threshold=0.92,
        unsupported_claims=[unsupported],
        missing_required=[missing],
        ontology_conflicts=["door:state:closed|open"],
        contradictions=[contradiction],
    )

    feedback = build_feedback(mismatch)

    assert "MUST REMOVE:" in feedback
    assert "MUST ADD:" in feedback
    assert "CONTRADICTIONS:" in feedback
    assert "REWRITE RULE:" in feedback
    assert "door" in feedback
