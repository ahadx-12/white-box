from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field

from trustai_core.packs.tariff.evidence.models import EvidenceSource
from trustai_core.packs.tariff.models import TariffCitation, TariffDossier


class CitationGateResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    ok: bool
    violations: list[str] = Field(default_factory=list)
    revision_guidance: str = ""
    missing_claim_types: list[str] = Field(default_factory=list)


def run_citation_gate(
    dossier: TariffDossier,
    evidence_bundle: Iterable[EvidenceSource],
) -> CitationGateResult:
    bundle = {source.source_id: source for source in evidence_bundle}
    citations = collect_citations(dossier)
    violations: list[str] = []
    missing_claim_types: list[str] = []

    _validate_citation_sources(citations, bundle, violations)

    if _has_hts_claim(dossier) and not _has_claim_type(citations, "hts_classification"):
        missing_claim_types.append("hts_classification")
        violations.append("missing_citations: hts_classification")

    if not _gri_steps_have_citations(dossier, bundle, violations):
        missing_claim_types.append("gri_application")

    if not _essential_character_citations_ok(dossier, bundle, violations):
        missing_claim_types.append("essential_character")

    ok = not violations
    revision_guidance = _build_revision_guidance(missing_claim_types, violations)
    return CitationGateResult(
        ok=ok,
        violations=sorted(set(violations)),
        revision_guidance=revision_guidance,
        missing_claim_types=sorted(set(missing_claim_types)),
    )


def collect_citations(dossier: TariffDossier) -> list[TariffCitation]:
    citations: list[TariffCitation] = []
    citations.extend(dossier.citations)
    citations.extend(dossier.essential_character.citations)
    for step in dossier.gri_trace.steps:
        citations.extend(step.citations)
    return citations


def _validate_citation_sources(
    citations: Iterable[TariffCitation],
    bundle: dict[str, EvidenceSource],
    violations: list[str],
) -> None:
    for citation in citations:
        source = bundle.get(citation.source_id)
        if not source:
            violations.append(f"invalid_source_id: {citation.source_id}")
            continue
        if citation.quote not in source.text:
            violations.append(f"quote_not_found: {citation.source_id}")


def _gri_steps_have_citations(
    dossier: TariffDossier,
    bundle: dict[str, EvidenceSource],
    violations: list[str],
) -> bool:
    ok = True
    for step in dossier.gri_trace.steps:
        step_citations = [
            citation
            for citation in step.citations
            if citation.claim_type == "gri_application"
        ]
        if not step_citations:
            violations.append(f"missing_gri_citation: {step.step.value}")
            ok = False
            continue
        if not any(citation.source_id.startswith("GRI.") for citation in step_citations):
            violations.append(f"gri_citation_not_gri_source: {step.step.value}")
            ok = False
        for citation in step_citations:
            source = bundle.get(citation.source_id)
            if source and citation.quote not in source.text:
                ok = False
    return ok


def _essential_character_citations_ok(
    dossier: TariffDossier,
    bundle: dict[str, EvidenceSource],
    violations: list[str],
) -> bool:
    citations = [
        citation
        for citation in dossier.essential_character.citations
        if citation.claim_type == "essential_character"
    ]
    if not citations:
        violations.append("missing_citations: essential_character")
        return False
    ok = False
    for citation in citations:
        source = bundle.get(citation.source_id)
        if not source:
            continue
        if source.source_type in {"chapter_note", "section_note"} or citation.source_id == "GRI.3":
            ok = True
    if not ok:
        violations.append("essential_character_missing_note_or_gri3")
    return ok


def _has_claim_type(citations: Iterable[TariffCitation], claim_type: str) -> bool:
    return any(citation.claim_type == claim_type for citation in citations)


def _has_hts_claim(dossier: TariffDossier) -> bool:
    return bool(dossier.baseline.hts_code or dossier.optimized.hts_code)


def _build_revision_guidance(missing: list[str], violations: list[str]) -> str:
    if not missing and not violations:
        return ""
    parts: list[str] = []
    if missing:
        parts.append(
            "Add citations for: " + ", ".join(sorted(set(missing))) + "."
        )
    if violations:
        parts.append(
            "Use only provided SOURCE_IDs and include verbatim quotes from the evidence bundle."
        )
    return " ".join(parts)
