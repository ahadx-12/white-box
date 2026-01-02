from __future__ import annotations

from trustai_core.packs.tariff.evidence.store import TariffEvidenceStore
from trustai_core.packs.tariff.gates.citation_gate import run_citation_gate
from trustai_core.packs.tariff.models import (
    CompositionComponent,
    EssentialCharacter,
    GriStep,
    GriStepResult,
    GriTrace,
    Mutation,
    TariffBaseline,
    TariffCitation,
    TariffDossier,
    TariffOptimized,
    WhatIfCandidate,
)

HTS_QUOTE = (
    "Footwear with outer soles of rubber or plastics, leather or composition leather "
    "and uppers of textile materials."
)
GRI_1_QUOTE = (
    "classification shall be determined according to the terms of the headings and any relative "
    "section or chapter notes."
)
GRI_2_QUOTE = "reference to that article incomplete or unfinished"
GRI_3_QUOTE = "material or component which gives them their essential character."
GRI_4_QUOTE = "heading appropriate to the goods to which they are most akin."
GRI_5_QUOTE = "packing materials and packing containers"
GRI_6_QUOTE = (
    "classification of goods in the subheadings of a heading shall be determined according to "
    "the terms of those subheadings"
)


def _bundle():
    store = TariffEvidenceStore()
    return store.list_sources()


def _mutation() -> Mutation:
    return Mutation(
        id="m1",
        title="Mutation",
        category="materials",
        change="swap material",
        expected_effect="unknown",
        expected_hts_change=None,
        expected_duty_rate_pct=None,
        expected_savings_note="Unknown impact.",
        rationale="Test rationale.",
        legal_rationale="Test legal rationale.",
        risk_level="low",
        constraints=["Test constraint"],
        required_evidence=["Spec"],
    )


def _base_dossier(citations: list[TariffCitation]) -> TariffDossier:
    return TariffDossier(
        product_summary="Test product",
        assumptions=["Assumption"],
        gri_trace=_gri_trace(),
        composition_table=[
            CompositionComponent(name="textile upper", pct=60.0),
            CompositionComponent(name="rubber outsole", pct=40.0),
        ],
        essential_character=EssentialCharacter(
            basis="value",
            weights={"textile": 60.0, "rubber": 40.0},
            conclusion="Textile upper imparts essential character under GRI 3(b).",
            justification="Upper material dominates value and surface area.",
            citations=[
                TariffCitation(
                    claim_type="essential_character",
                    claim="Essential character follows GRI 3(b).",
                    source_id="GRI.3",
                    quote=GRI_3_QUOTE,
                )
            ],
        ),
        baseline=TariffBaseline(
            hts_code="6404.11.90",
            duty_rate_pct=20.0,
            duty_basis="ad valorem",
            rationale="Test rationale",
            confidence=0.5,
        ),
        mutations=[_mutation()],
        best_option_id="m1",
        optimized=TariffOptimized(
            hts_code="6402.99",
            duty_rate_pct=5.0,
            estimated_savings_per_unit=0.0,
            rationale="Cannot reduce",
            risk_flags=["None"],
        ),
        what_if_candidates=[
            WhatIfCandidate(
                mutation_id="whatif_test",
                change="Adjust material mix.",
                rationale="Threshold flip may alter classification.",
                expected_heading_shift="Potential shift within subheadings.",
                estimated_duty_delta=-0.01,
                legal_risks=["Requires documentation."],
                citations_required=True,
                constraints=["Maintain compliance"],
            )
        ],
        chosen_mutation="m1",
        savings_estimate=None,
        compliance_notes=["Lawful tariff engineering with documentation."],
        questions_for_user=[],
        citations=citations,
    )


def _gri_trace() -> GriTrace:
    return GriTrace(
        steps=[
            GriStepResult(
                step=GriStep.GRI_1,
                applied=False,
                reasoning="Multiple headings plausible.",
                citations=[
                    TariffCitation(
                        claim_type="gri_application",
                        claim="GRI 1 reference.",
                        source_id="GRI.1",
                        quote=GRI_1_QUOTE,
                    )
                ],
                rejected_because=["Multiple headings plausible"],
            ),
            GriStepResult(
                step=GriStep.GRI_2,
                applied=False,
                reasoning="Incomplete rule not applicable.",
                citations=[
                    TariffCitation(
                        claim_type="gri_application",
                        claim="GRI 2 reference.",
                        source_id="GRI.2",
                        quote=GRI_2_QUOTE,
                    )
                ],
                rejected_because=["Not incomplete"],
            ),
            GriStepResult(
                step=GriStep.GRI_3,
                applied=True,
                reasoning="Essential character needed.",
                citations=[
                    TariffCitation(
                        claim_type="gri_application",
                        claim="GRI 3 reference.",
                        source_id="GRI.3",
                        quote=GRI_3_QUOTE,
                    )
                ],
                rejected_because=[],
            ),
            GriStepResult(
                step=GriStep.GRI_4,
                applied=False,
                reasoning="Earlier step resolved classification.",
                citations=[
                    TariffCitation(
                        claim_type="gri_application",
                        claim="GRI 4 reference.",
                        source_id="GRI.4",
                        quote=GRI_4_QUOTE,
                    )
                ],
                rejected_because=["GRI_3 applied"],
            ),
            GriStepResult(
                step=GriStep.GRI_5,
                applied=False,
                reasoning="Packaging rule not needed.",
                citations=[
                    TariffCitation(
                        claim_type="gri_application",
                        claim="GRI 5 reference.",
                        source_id="GRI.5",
                        quote=GRI_5_QUOTE,
                    )
                ],
                rejected_because=["GRI_3 applied"],
            ),
            GriStepResult(
                step=GriStep.GRI_6,
                applied=False,
                reasoning="Subheading not needed.",
                citations=[
                    TariffCitation(
                        claim_type="gri_application",
                        claim="GRI 6 reference.",
                        source_id="GRI.6",
                        quote=GRI_6_QUOTE,
                    )
                ],
                rejected_because=["GRI_3 applied"],
            ),
        ],
        final_step_used=GriStep.GRI_3,
        sequence_ok=True,
        violations=[],
        step_vector=[False, False, True, False, False, False],
    )


def test_citation_gate_fails_missing_citations() -> None:
    dossier = _base_dossier(citations=[])
    empty_steps = [
        step.model_copy(update={"citations": []}) for step in dossier.gri_trace.steps
    ]
    dossier = dossier.model_copy(
        update={
            "essential_character": dossier.essential_character.model_copy(update={"citations": []}),
            "gri_trace": dossier.gri_trace.model_copy(update={"steps": empty_steps}),
        }
    )
    result = run_citation_gate(dossier, _bundle())
    assert not result.ok
    assert "missing_citations: hts_classification" in result.violations


def test_citation_gate_fails_bad_source_id() -> None:
    dossier = _base_dossier(
        citations=[
            TariffCitation(
                claim_type="hts_classification",
                claim="HTS classification",
                source_id="BAD.SOURCE",
                quote=HTS_QUOTE,
            )
        ]
    )
    result = run_citation_gate(dossier, _bundle())
    assert not result.ok
    assert any("invalid_source_id" in item for item in result.violations)


def test_citation_gate_fails_bad_quote() -> None:
    dossier = _base_dossier(
        citations=[
            TariffCitation(
                claim_type="hts_classification",
                claim="HTS classification",
                source_id="HTS.6404",
                quote="not in text",
            )
        ]
    )
    result = run_citation_gate(dossier, _bundle())
    assert not result.ok
    assert any("quote_not_found" in item for item in result.violations)


def test_citation_gate_passes_with_valid_citations() -> None:
    dossier = _base_dossier(
        citations=[
            TariffCitation(
                claim_type="hts_classification",
                claim="HTS classification",
                source_id="HTS.6404",
                quote=HTS_QUOTE,
            )
        ]
    )
    result = run_citation_gate(dossier, _bundle())
    assert result.ok
