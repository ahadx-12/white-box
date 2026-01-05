from __future__ import annotations

from trustai_core.packs.tariff.evidence.models import EvidenceSource
from trustai_core.packs.tariff.mutations.engine import build_lever_proof
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
    WhatIfCandidate,
)
from trustai_core.packs.tariff.mutations.models import ProductDossier


def _evidence_bundle() -> list[EvidenceSource]:
    sources = [
        EvidenceSource(
            source_id="HTS.64",
            source_type="heading",
            title="HTS 64 heading",
            effective_date="2024",
            url=None,
            text="Footwear with outer soles of rubber or plastics.",
        ),
        EvidenceSource(
            source_id="CH64.1",
            source_type="chapter_note",
            title="Chapter 64 note",
            effective_date="2024",
            url=None,
            text="Chapter note for footwear.",
        ),
    ]
    for step in range(1, 7):
        sources.append(
            EvidenceSource(
                source_id=f"GRI.{step}",
                source_type="gri",
                title=f"GRI {step}",
                effective_date="2024",
                url=None,
                text=f"GRI {step} rule text.",
            )
        )
    return sources


def _tariff_dossier() -> TariffDossier:
    gri_steps = []
    for step in GriStep:
        applied = step == GriStep.GRI_3
        gri_steps.append(
            GriStepResult(
                step=step,
                applied=applied,
                reasoning="Rule applied." if applied else "Rule not applied.",
                citations=[
                    TariffCitation(
                        claim_type="gri_application",
                        claim="Applied GRI",
                        source_id=f"GRI.{step.value.split('_')[-1]}",
                        quote=f"GRI {step.value.split('_')[-1]} rule text.",
                    )
                ],
                rejected_because=[] if applied else ["Not applicable"],
            )
        )
    return TariffDossier(
        product_summary="Footwear",
        candidate_chapters=["64"],
        assumptions=["Assumption"],
        gri_trace=GriTrace(
            steps=gri_steps,
            final_step_used=GriStep.GRI_3,
            sequence_ok=True,
            violations=[],
            step_vector=[False, False, True, False, False, False],
        ),
        composition_table=[
            CompositionComponent(name="rubber outsole", pct=60.0),
            CompositionComponent(name="textile upper", pct=40.0),
        ],
        essential_character=EssentialCharacter(
            basis="value",
            weights={"rubber": 60.0, "textile": 40.0},
            conclusion="Rubber outsole dominates.",
            justification="Outsole dominates value.",
            citations=[
                TariffCitation(
                    claim_type="essential_character",
                    claim="Essential character",
                    source_id="GRI.3",
                    quote="GRI 3 rule text.",
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
        mutations=[],
        best_option_id=None,
        optimized=TariffOptimized(
            hts_code="6404.11.90",
            duty_rate_pct=10.0,
            estimated_savings_per_unit=0.0,
            rationale="Optimization",
            risk_flags=[],
        ),
        what_if_candidates=[
            WhatIfCandidate(
                mutation_id="whatif",
                change="Change",
                rationale="Rationale",
                expected_heading_shift="Shift",
                estimated_duty_delta=-0.1,
                legal_risks=[],
                citations_required=True,
                constraints=[],
            )
        ],
        chosen_mutation=None,
        savings_estimate=None,
        compliance_notes=["Lawful"],
        questions_for_user=[],
        citations=[
            TariffCitation(
                claim_type="hts_classification",
                claim="Classification",
                source_id="HTS.64",
                quote="Footwear with outer soles of rubber or plastics.",
            )
        ],
    )


def test_tariff_levers_only_include_verified_candidates() -> None:
    product = ProductDossier(
        product_summary="Athletic footwear",
        upper_materials=[
            {"material": "textile", "pct": 60.0},
            {"material": "leather", "pct": 40.0},
        ],
        outsole_materials=[
            {"material": "rubber", "pct": 70.0},
            {"material": "textile", "pct": 30.0},
        ],
    )
    dossier = _tariff_dossier()
    evidence = _evidence_bundle()
    evidence_payload = [source.model_dump() for source in evidence]

    proof = build_lever_proof(product, dossier, evidence, evidence_payload, top_k=3)

    assert proof.mutation_candidates
    assert proof.selected_levers
    for lever in proof.selected_levers:
        assert lever.gate_results["verification"]["ok"]
        assert lever.sequence
        for step in lever.sequence:
            assert step.compliance_result["ok"]


def test_no_product_dossier_returns_no_levers() -> None:
    dossier = _tariff_dossier()
    evidence = _evidence_bundle()
    evidence_payload = [source.model_dump() for source in evidence]
    proof = build_lever_proof(None, dossier, evidence, evidence_payload, top_k=3)
    assert proof.selected_levers == []
