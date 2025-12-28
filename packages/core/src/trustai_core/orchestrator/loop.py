from __future__ import annotations

import asyncio
import difflib
from typing import Any

from trustai_core.arbiter import feedback as feedback_builder
from trustai_core.arbiter.evaluator import CLAIM_SUPPORT_THRESHOLD, SCORE_THRESHOLD, Evaluator
from trustai_core.core.encoder import AtomEncoder
from trustai_core.core.memory import ItemMemory
from trustai_core.packs.loader import load_pack
from trustai_core.schemas.atoms import AtomModel, ManifestModel
from trustai_core.schemas.proof import ANSWER_PREVIEW_CHARS, IterationTrace, VerificationResult
from trustai_core.utils.hashing import sha256_canonical_json

FEEDBACK_PREVIEW_CHARS = 320


class VerificationFailure(RuntimeError):
    def __init__(self, message: str, result: VerificationResult) -> None:
        super().__init__(message)
        self.result = result


def _manifest_hash(atoms: list[AtomModel]) -> str:
    return sha256_canonical_json([atom.model_dump() for atom in atoms])


def _build_explain(mismatch) -> dict[str, Any]:
    return {
        "score": round(mismatch.score, 6),
        "threshold": mismatch.threshold,
        "unsupported_claims": [atom.model_dump() for atom in mismatch.unsupported_claims],
        "missing_required": [atom.model_dump() for atom in mismatch.missing_required],
        "ontology_conflicts": list(mismatch.ontology_conflicts),
        "contradictions": [
            {"left": pair.left.model_dump(), "right": pair.right.model_dump()}
            for pair in mismatch.contradictions
        ],
        "summary": (
            f"Score {mismatch.score:.4f} vs {mismatch.threshold:.2f}; "
            f"unsupported={len(mismatch.unsupported_claims)}, "
            f"missing={len(mismatch.missing_required)}, "
            f"conflicts={len(mismatch.ontology_conflicts)}"
        ),
    }


def _evaluate_with_fallback(
    arbiter,
    evidence_atoms,
    claim_atoms,
    pack,
    encoder,
    threshold,
    support,
):
    try:
        return arbiter.evaluate(evidence_atoms, claim_atoms, pack)
    except TypeError:
        return arbiter.evaluate(
            evidence_atoms=evidence_atoms,
            claim_atoms=claim_atoms,
            pack=pack,
            encoder=encoder,
            score_threshold=threshold,
            claim_support_threshold=support,
        )


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _format_atom(atom: AtomModel) -> str:
    return f"({atom.subject}, {atom.predicate}, {atom.obj}, {atom.is_true})"


def _format_conflict(pair) -> str:
    return f"{_format_atom(pair.left)} vs {_format_atom(pair.right)}"


def _top_conflicts(mismatch) -> list[str]:
    conflicts: list[str] = []
    for pair in mismatch.contradictions:
        conflicts.append(f"contradiction: {_format_conflict(pair)}")
    for atom in mismatch.unsupported_claims:
        conflicts.append(f"unsupported: {_format_atom(atom)}")
    for atom in mismatch.missing_required:
        conflicts.append(f"missing: {_format_atom(atom)}")
    return conflicts


def _summarize_answer_delta(previous: str | None, current: str) -> str:
    if previous is None:
        return "initial_answer"
    if previous == current:
        return "no_change"
    prev_tokens = previous.split()
    curr_tokens = current.split()
    matcher = difflib.SequenceMatcher(a=prev_tokens, b=curr_tokens)
    added = removed = replaced = 0
    for tag, _, _, _, _ in matcher.get_opcodes():
        if tag == "insert":
            added += 1
        elif tag == "delete":
            removed += 1
        elif tag == "replace":
            replaced += 1
    return f"delta tokens: +{added} -{removed} ~{replaced}"


async def verify_and_fix(
    user_text: str,
    pack_name: str,
    perceiver,
    reasoner,
    arbiter,
    max_iters: int = 5,
    threshold: float = SCORE_THRESHOLD,
    claim_support_threshold: float = CLAIM_SUPPORT_THRESHOLD,
    enable_parallel_prepass: bool = False,
    regenerate_with_evidence: bool = False,
) -> VerificationResult:
    if hasattr(arbiter, "encoder"):
        encoder = arbiter.encoder
        memory = encoder.memory
    else:
        memory = ItemMemory()
        encoder = AtomEncoder(memory)
        if arbiter is None:
            arbiter = Evaluator(
                encoder,
                score_threshold=threshold,
                claim_support_threshold=claim_support_threshold,
            )

    pack = load_pack(pack_name, memory)

    evidence_manifest: ManifestModel
    preliminary_answer: str | None = None
    if enable_parallel_prepass:
        evidence_task = asyncio.create_task(perceiver.extract_evidence_atoms(user_text, pack))
        draft_task = asyncio.create_task(reasoner.generate_answer(user_text, pack, None, None))
        evidence_manifest, preliminary_answer = await asyncio.gather(evidence_task, draft_task)
    else:
        evidence_manifest = await perceiver.extract_evidence_atoms(user_text, pack)

    evidence_hash = _manifest_hash(evidence_manifest.atoms)

    iterations: list[IterationTrace] = []
    feedback: str | None = None
    last_mismatch = None
    previous_answer: str | None = None

    for i in range(1, max_iters + 1):
        if preliminary_answer is not None and i == 1:
            answer = preliminary_answer
        else:
            answer = await reasoner.generate_answer(user_text, pack, evidence_manifest, feedback)

        if regenerate_with_evidence and evidence_manifest.atoms and i == 1 and preliminary_answer:
            answer = await reasoner.generate_answer(user_text, pack, evidence_manifest, feedback)

        claim_manifest = await perceiver.extract_claim_atoms(answer, pack)
        mismatch = _evaluate_with_fallback(
            arbiter,
            evidence_manifest.atoms,
            claim_manifest.atoms,
            pack,
            encoder,
            threshold,
            claim_support_threshold,
        )
        last_mismatch = mismatch
        feedback_text = feedback_builder.build_feedback(mismatch)
        feedback_summary = feedback_text.splitlines()[0] if feedback_text else ""
        answer_delta_summary = _summarize_answer_delta(previous_answer, answer)
        previous_answer = answer
        top_conflicts = _top_conflicts(mismatch)

        iterations.append(
            IterationTrace(
                i=i,
                answer_preview=answer[:ANSWER_PREVIEW_CHARS],
                score=mismatch.score,
                mismatch=mismatch,
                feedback_summary=feedback_summary,
                claim_manifest_hash=_manifest_hash(claim_manifest.atoms),
                top_conflicts=top_conflicts,
                unsupported_claims=mismatch.unsupported_claims,
                missing_required=mismatch.missing_required,
                feedback_text=_truncate(feedback_text, FEEDBACK_PREVIEW_CHARS),
                answer_delta_summary=answer_delta_summary,
            )
        )

        if mismatch.score >= threshold:
            explain = _build_explain(mismatch)
            iterations_payload = [item.model_dump() for item in iterations]
            result_payload: dict[str, Any] = {
                "status": "verified",
                "pack": pack.name,
                "pack_fingerprint": pack.fingerprint,
                "evidence_manifest_hash": evidence_hash,
                "final_answer": answer,
                "iterations": iterations_payload,
                "explain": explain,
            }
            proof_id = VerificationResult.compute_proof_id(result_payload)
            return VerificationResult(
                proof_id=proof_id,
                status="verified",
                pack=pack.name,
                pack_fingerprint=pack.fingerprint,
                evidence_manifest_hash=evidence_hash,
                final_answer=answer,
                iterations=iterations,
                explain=explain,
            )

        feedback = feedback_text
    explain = _build_explain(last_mismatch)
    iterations_payload = [item.model_dump() for item in iterations]
    failure_payload: dict[str, Any] = {
        "status": "failed",
        "pack": pack.name,
        "pack_fingerprint": pack.fingerprint,
        "evidence_manifest_hash": evidence_hash,
        "final_answer": None,
        "iterations": iterations_payload,
        "explain": explain,
    }
    proof_id = VerificationResult.compute_proof_id(failure_payload)
    result = VerificationResult(
        proof_id=proof_id,
        status="failed",
        pack=pack.name,
        pack_fingerprint=pack.fingerprint,
        evidence_manifest_hash=evidence_hash,
        final_answer=None,
        iterations=iterations,
        explain=explain,
    )
    raise VerificationFailure("Verification failed after max iterations", result)
