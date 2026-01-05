from __future__ import annotations

import re
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field

from trustai_core.packs.tariff.evidence.models import EvidenceSource
from trustai_core.packs.tariff.models import TariffCitation, TariffDossier

SECTION_BY_CHAPTER = {
    "64": "SEC12",
    "73": "SEC15",
    "84": "SEC16",
    "85": "SEC16",
}


class MissingEvidenceGateResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    ok: bool
    violations: list[str] = Field(default_factory=list)
    revision_guidance: str = ""
    refusal_category: str | None = None


def run_missing_evidence_gate(
    dossier: TariffDossier,
    evidence_bundle: Iterable[EvidenceSource],
) -> MissingEvidenceGateResult:
    final_hts = _final_hts_code(dossier)
    if not final_hts:
        return MissingEvidenceGateResult(ok=True)
    final_chapter = _extract_hts_chapter(final_hts)
    if not final_chapter:
        return MissingEvidenceGateResult(ok=True)

    bundle = list(evidence_bundle)
    violations: list[str] = []

    if not _has_heading_for_chapter(bundle, final_chapter):
        violations.append(f"missing_heading_chapter: {final_chapter}")
    if not _has_chapter_note(bundle, final_chapter):
        violations.append(f"missing_chapter_notes: {final_chapter}")

    citations = _critical_citations(dossier)
    unrelated = _find_unrelated_citations(citations, final_chapter)
    violations.extend(unrelated)

    if _claims_chapter_note(citations) and not _has_chapter_note(bundle, final_chapter):
        violations.append(f"chapter_note_claim_missing_sources: {final_chapter}")

    ok = not violations
    revision_guidance = _build_revision_guidance(final_chapter, violations)
    return MissingEvidenceGateResult(
        ok=ok,
        violations=sorted(set(violations)),
        revision_guidance=revision_guidance,
        refusal_category=None if ok else "missing_evidence",
    )


def _final_hts_code(dossier: TariffDossier) -> str | None:
    optimized = (dossier.optimized.hts_code or "").strip()
    if optimized:
        return optimized
    baseline = (dossier.baseline.hts_code or "").strip()
    return baseline or None


def _extract_hts_chapter(hts_code: str) -> str | None:
    digits = re.sub(r"\D", "", hts_code)
    if len(digits) < 2:
        return None
    return digits[:2]


def _has_heading_for_chapter(bundle: Iterable[EvidenceSource], chapter: str) -> bool:
    return any(
        source.source_type in {"heading", "subheading"}
        and source.source_id.startswith(f"HTS.{chapter}")
        for source in bundle
    )


def _has_chapter_note(bundle: Iterable[EvidenceSource], chapter: str) -> bool:
    return any(
        source.source_type in {"chapter_note", "section_note", "note"}
        and source.source_id.startswith(f"CH{chapter}.")
        for source in bundle
    )


def _critical_citations(dossier: TariffDossier) -> list[TariffCitation]:
    citations: list[TariffCitation] = []
    citations.extend(
        citation
        for citation in dossier.citations
        if citation.claim_type in {"hts_classification", "essential_character"}
    )
    citations.extend(
        citation
        for citation in dossier.essential_character.citations
        if citation.claim_type in {"hts_classification", "essential_character"}
    )
    return citations


def _find_unrelated_citations(
    citations: Iterable[TariffCitation],
    final_chapter: str,
) -> list[str]:
    allowed_prefixes = [
        f"HTS.{final_chapter}",
        f"CH{final_chapter}.",
        "GRI.",
    ]
    section = SECTION_BY_CHAPTER.get(final_chapter)
    if section:
        allowed_prefixes.append(f"{section}.")
    violations: list[str] = []
    for citation in citations:
        source_id = citation.source_id
        if any(source_id.startswith(prefix) for prefix in allowed_prefixes):
            continue
        violations.append(f"unrelated_chapter_citation: {source_id}")
    return violations


def _claims_chapter_note(citations: Iterable[TariffCitation]) -> bool:
    for citation in citations:
        claim = citation.claim.lower()
        if "chapter note" in claim or "note" in claim or "exclusion" in claim:
            return True
    return False


def _build_revision_guidance(final_chapter: str, violations: list[str]) -> str:
    if not violations:
        return ""
    missing_markers = {"missing_heading_chapter", "missing_chapter_notes", "chapter_note_claim_missing_sources"}
    if any(any(marker in violation for marker in missing_markers) for violation in violations):
        return f"retrieve/attach missing chapter evidence: CH{final_chapter} notes + headings"
    return "request missing product facts needed to disambiguate chapters"
