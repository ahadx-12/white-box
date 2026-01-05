from __future__ import annotations

from trustai_core.packs.tariff.evidence.models import EvidenceSource
from trustai_core.packs.tariff.gates.missing_evidence_gate import run_missing_evidence_gate
from trustai_core.packs.tariff.models import (
    CompositionComponent,
    EssentialCharacter,
    GriStep,
    GriStepResult,
    GriTrace,
    TariffBaseline,
    TariffCitation,
    TariffDossier,
    TariffOptimized,
)


def _base_gri_trace() -> GriTrace:
    steps = []
    for step in (
        GriStep.GRI_1,
        GriStep.GRI_2,
        GriStep.GRI_3,
        GriStep.GRI_4,
        GriStep.GRI_5,
        GriStep.GRI_6,
    ):
        steps.append(
            GriStepResult(
                step=step,
                applied=False,
                reasoning="Test",
                citations=[],
                rejected_because=[],
            )
        )
    return GriTrace(
        steps=steps,
        final_step_used=GriStep.GRI_1,
        sequence_ok=True,
        violations=[],
        step_vector=[False, False, False, False, False, False],
    )


def _base_dossier(hts_code: str, citations: list[TariffCitation]) -> TariffDossier:
    return TariffDossier(
        product_summary="Test product",
        candidate_chapters=[],
        assumptions=[],
        gri_trace=_base_gri_trace(),
        composition_table=[CompositionComponent(name="component", pct=100.0)],
        essential_character=EssentialCharacter(
            basis="value",
            weights={"component": 100.0},
            conclusion="component",
            justification="test",
            citations=[],
        ),
        baseline=TariffBaseline(
            hts_code=hts_code,
            duty_rate_pct=5.0,
            duty_basis="ad valorem",
            rationale="test",
            confidence=0.5,
        ),
        mutations=[],
        best_option_id=None,
        optimized=TariffOptimized(
            hts_code=hts_code,
            duty_rate_pct=5.0,
            estimated_savings_per_unit=None,
            rationale="test",
            risk_flags=[],
        ),
        what_if_candidates=[],
        chosen_mutation=None,
        savings_estimate=None,
        compliance_notes=[],
        questions_for_user=[],
        citations=citations,
    )


def test_missing_evidence_gate_fails_without_heading() -> None:
    dossier = _base_dossier(
        "8504.10",
        [
            TariffCitation(
                claim_type="hts_classification",
                claim="Classify under transformers.",
                source_id="HTS.8504",
                quote="Electrical transformers",
            )
        ],
    )
    evidence_bundle = [
        EvidenceSource(
            source_id="CH85.NOTE1",
            source_type="chapter_note",
            title="Chapter 85 Note 1",
            effective_date="2024-01-01",
            url=None,
            text="This chapter covers electrical machinery.",
        )
    ]
    result = run_missing_evidence_gate(dossier, evidence_bundle)
    assert not result.ok
    assert any("missing_heading_chapter" in violation for violation in result.violations)


def test_missing_evidence_gate_fails_without_notes() -> None:
    dossier = _base_dossier(
        "7318.15",
        [
            TariffCitation(
                claim_type="hts_classification",
                claim="Classify under fasteners.",
                source_id="HTS.7318",
                quote="Screws, bolts",
            )
        ],
    )
    evidence_bundle = [
        EvidenceSource(
            source_id="HTS.7318",
            source_type="heading",
            title="HTS 7318",
            effective_date="2024-01-01",
            url=None,
            text="Screws, bolts, nuts.",
        )
    ]
    result = run_missing_evidence_gate(dossier, evidence_bundle)
    assert not result.ok
    assert any("missing_chapter_notes" in violation for violation in result.violations)


def test_missing_evidence_gate_fails_on_unrelated_citation() -> None:
    dossier = _base_dossier(
        "8544.11",
        [
            TariffCitation(
                claim_type="hts_classification",
                claim="Classify as footwear.",
                source_id="HTS.6404",
                quote="Footwear with outer soles",
            )
        ],
    )
    evidence_bundle = [
        EvidenceSource(
            source_id="HTS.8544",
            source_type="heading",
            title="HTS 8544",
            effective_date="2024-01-01",
            url=None,
            text="Insulated wire and cable",
        ),
        EvidenceSource(
            source_id="CH85.NOTE1",
            source_type="chapter_note",
            title="Chapter 85 Note 1",
            effective_date="2024-01-01",
            url=None,
            text="This chapter covers electrical machinery.",
        ),
    ]
    result = run_missing_evidence_gate(dossier, evidence_bundle)
    assert not result.ok
    assert any("unrelated_chapter_citation" in violation for violation in result.violations)


def test_missing_evidence_gate_passes_with_heading_and_notes() -> None:
    dossier = _base_dossier(
        "8413.70",
        [
            TariffCitation(
                claim_type="hts_classification",
                claim="Classify pumps for liquids.",
                source_id="HTS.8413",
                quote="Pumps for liquids",
            )
        ],
    )
    evidence_bundle = [
        EvidenceSource(
            source_id="HTS.8413",
            source_type="heading",
            title="HTS 8413",
            effective_date="2024-01-01",
            url=None,
            text="Pumps for liquids, whether or not fitted with a measuring device.",
        ),
        EvidenceSource(
            source_id="CH84.NOTE1",
            source_type="chapter_note",
            title="Chapter 84 Note 1",
            effective_date="2024-01-01",
            url=None,
            text="This chapter covers machinery and mechanical appliances.",
        ),
    ]
    result = run_missing_evidence_gate(dossier, evidence_bundle)
    assert result.ok
