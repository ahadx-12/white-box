from __future__ import annotations

from fastapi import HTTPException
from trustai_core.schemas.atoms import AtomModel
from trustai_core.schemas.proof import VerificationResult

from trustai_api.settings import Settings


def list_packs(settings: Settings) -> list[str]:
    if not settings.storage_root.exists():
        return []
    return sorted([path.name for path in settings.storage_root.iterdir() if path.is_dir()])


def resolve_pack(settings: Settings, pack_header: str | None) -> str:
    available = list_packs(settings)
    pack = pack_header or "general"
    if pack not in available:
        raise HTTPException(
            status_code=400,
            detail={"message": "Invalid pack", "available_packs": available},
        )
    return pack


def _atom_to_text(atom: AtomModel) -> str:
    truth = "true" if atom.is_true else "false"
    return f"{atom.subject} {atom.predicate} {atom.obj} ({truth})"


def _normalize_atom_list(atoms: list[AtomModel]) -> list[str]:
    return [_atom_to_text(atom) for atom in sorted(atoms, key=lambda item: item.sort_key())]


def _normalize_explain_entries(entries: list[object]) -> list[str]:
    normalized: list[str] = []
    for entry in entries:
        if isinstance(entry, AtomModel):
            normalized.append(_atom_to_text(entry))
        elif isinstance(entry, dict):
            try:
                atom = AtomModel(**entry)
            except TypeError:
                normalized.append(str(entry))
            else:
                normalized.append(_atom_to_text(atom))
        else:
            normalized.append(str(entry))
    return sorted(normalized)


def normalize_verification_result(result: VerificationResult) -> dict[str, object]:
    iterations: list[dict[str, object]] = []
    similarity_history: list[float] = []
    for iteration in result.iterations:
        mismatch = iteration.mismatch
        conflicts = sorted(mismatch.ontology_conflicts)
        unsupported = _normalize_atom_list(list(mismatch.unsupported_claims))
        missing = _normalize_atom_list(list(mismatch.missing_evidence))
        accepted = iteration.score >= mismatch.threshold
        rejected_because: list[str] = []
        if not accepted:
            rejected_because.append("score_below_threshold")
            if unsupported:
                rejected_because.append("unsupported_claims")
            if missing:
                rejected_because.append("missing_evidence")
            if conflicts:
                rejected_because.append("ontology_conflicts")
        iterations.append(
            {
                "i": iteration.i,
                "score": round(iteration.score, 6),
                "accepted": accepted,
                "rejected_because": rejected_because,
                "conflicts": conflicts,
                "unsupported": unsupported,
                "missing": missing,
            }
        )
        similarity_history.append(round(iteration.score, 6))

    explain_payload = result.explain or {}
    key_conflicts = _normalize_explain_entries(list(explain_payload.get("ontology_conflicts", [])))
    unsupported_claims = _normalize_explain_entries(
        list(explain_payload.get("unsupported_claims", []))
    )
    missing_evidence = _normalize_explain_entries(list(explain_payload.get("missing_evidence", [])))
    summary = explain_payload.get("summary")
    if not summary:
        summary = (
            f"Score {similarity_history[-1] if similarity_history else 0.0:.4f}; "
            f"unsupported={len(unsupported_claims)}, "
            f"missing={len(missing_evidence)}, "
            f"conflicts={len(key_conflicts)}"
        )

    return {
        "status": result.status,
        "proof_id": result.proof_id,
        "pack": result.pack,
        "pack_fingerprint": result.pack_fingerprint,
        "evidence_manifest_hash": result.evidence_manifest_hash,
        "final_answer": result.final_answer,
        "iterations": iterations,
        "similarity_history": similarity_history,
        "explain": {
            "summary": summary,
            "key_conflicts": key_conflicts,
            "unsupported_claims": unsupported_claims,
            "missing_evidence": missing_evidence,
        },
        "proof": result.model_dump(),
    }
