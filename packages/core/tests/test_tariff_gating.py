from __future__ import annotations

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
from trustai_core.packs.tariff.pack import _gate_dossier


def _base_mutation(category: str = "materials", change: str = "swap material") -> Mutation:
    return Mutation(
        id="m1",
        title="Mutation",
        category=category,
        change=change,
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


def _base_dossier(mutations: list[Mutation]) -> TariffDossier:
    return TariffDossier(
        product_summary="Test product",
        assumptions=["Assumption"],
        gri_trace=_base_gri_trace(),
        composition_table=[
            CompositionComponent(name="rubber outsole", pct=60.0),
            CompositionComponent(name="plastic upper", pct=40.0),
        ],
        essential_character=EssentialCharacter(
            basis="value",
            weights={"rubber": 60.0, "plastic": 40.0},
            conclusion="Rubber outsole dominates essential character.",
            justification="Outsole material dominates value and use.",
            citations=[],
        ),
        baseline=TariffBaseline(
            hts_code="1234.56",
            duty_rate_pct=10.0,
            duty_basis="ad valorem",
            rationale="Test rationale",
            confidence=0.5,
        ),
        mutations=mutations,
        best_option_id=mutations[0].id if mutations else None,
        optimized=TariffOptimized(
            hts_code="1234.56",
            duty_rate_pct=10.0,
            estimated_savings_per_unit=0.0,
            rationale="Cannot reduce",
            risk_flags=["None"],
        ),
        what_if_candidates=[
            WhatIfCandidate(
                mutation_id="whatif_test",
                change="Adjust material mix to cross a threshold.",
                rationale="Threshold flip may alter classification.",
                expected_heading_shift="Potential shift within subheadings.",
                estimated_duty_delta=-0.01,
                legal_risks=["Requires documentation."],
                citations_required=True,
                constraints=["Maintain compliance"],
            )
        ],
        chosen_mutation=mutations[0].id if mutations else None,
        savings_estimate=None,
        compliance_notes=["Lawful tariff engineering with documentation."],
        questions_for_user=[],
        citations=[
            TariffCitation(
                claim_type="hts_classification",
                claim="Test claim",
                source_id="HTS.0000",
                quote="Test quote",
            )
        ],
    )


def _base_gri_trace() -> GriTrace:
    return GriTrace(
        steps=[
            GriStepResult(
                step=GriStep.GRI_1,
                applied=False,
                reasoning="Multiple headings plausible.",
                citations=[],
                rejected_because=["Multiple headings plausible"],
            ),
            GriStepResult(
                step=GriStep.GRI_2,
                applied=False,
                reasoning="Incomplete rule not applicable.",
                citations=[],
                rejected_because=["Not incomplete"],
            ),
            GriStepResult(
                step=GriStep.GRI_3,
                applied=True,
                reasoning="Essential character needed.",
                citations=[],
                rejected_because=[],
            ),
            GriStepResult(
                step=GriStep.GRI_4,
                applied=False,
                reasoning="Earlier step resolved classification.",
                citations=[],
                rejected_because=["GRI_3 applied"],
            ),
            GriStepResult(
                step=GriStep.GRI_5,
                applied=False,
                reasoning="Packaging rule not needed.",
                citations=[],
                rejected_because=["GRI_3 applied"],
            ),
            GriStepResult(
                step=GriStep.GRI_6,
                applied=False,
                reasoning="Subheading not needed.",
                citations=[],
                rejected_because=["GRI_3 applied"],
            ),
        ],
        final_step_used=GriStep.GRI_3,
        sequence_ok=True,
        violations=[],
        step_vector=[False, False, True, False, False, False],
    )


def test_gate_rejects_missing_questions_for_unknown_hts() -> None:
    dossier = _base_dossier([_base_mutation()])
    dossier = dossier.model_copy(update={"baseline": dossier.baseline.model_copy(update={"hts_code": None})})
    gate = _gate_dossier(dossier, min_mutations=1)
    assert "hts_or_questions_missing" in gate.rejected_because


def test_gate_rejects_origin_without_transformation() -> None:
    dossier = _base_dossier([_base_mutation(category="origin", change="Move assembly to partner")])
    gate = _gate_dossier(dossier, min_mutations=1)
    assert "origin_without_substantial_transformation" in gate.rejected_because


def test_gate_requires_citations_or_assumptions_for_precise_claims() -> None:
    dossier = _base_dossier([_base_mutation()])
    dossier = dossier.model_copy(update={"assumptions": [], "citations": []})
    gate = _gate_dossier(dossier, min_mutations=1)
    assert "missing_citations_or_assumptions" in gate.rejected_because
