from __future__ import annotations

from dataclasses import dataclass

from trustai_core.packs.tariff.evidence.models import EvidenceSource
from trustai_core.packs.tariff.mutations.engine import _verify_mutation
from trustai_core.packs.tariff.mutations.models import MutationBounds, MutationCandidate, ProductDiff, ProductDossier
from trustai_core.packs.tariff.mutations.operators import MutationOperator
from trustai_core.packs.tariff.mutations.search import SearchConfig, run_beam_search
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


@dataclass(frozen=True)
class _TestOperator(MutationOperator):
    def generate(self, dossier: ProductDossier) -> list[MutationCandidate]:
        if not self._has_required_inputs(dossier):
            return []
        path = next(iter(self.touch_paths)) if self.touch_paths else "housing.material"
        return [
            self._candidate(
                [
                    ProductDiff(
                        path=path,
                        from_value="steel",
                        to_value="plastic",
                        details={"material_delta_pct": 0.1},
                    )
                ]
            )
        ]


def _tariff_dossier() -> TariffDossier:
    return TariffDossier(
        product_summary="Pump",
        candidate_chapters=["84"],
        assumptions=["Assumption"],
        gri_trace=GriTrace(
            steps=[
                GriStepResult(
                    step=GriStep.GRI_1,
                    applied=True,
                    reasoning="Rule applied.",
                    citations=[],
                    rejected_because=[],
                )
            ],
            final_step_used=GriStep.GRI_1,
            sequence_ok=True,
            violations=[],
            step_vector=[True, False, False, False, False, False],
        ),
        composition_table=[CompositionComponent(name="housing", pct=100.0)],
        essential_character=EssentialCharacter(
            basis="value",
            weights={"housing": 1.0},
            conclusion="Housing dominates.",
            justification="Housing dominates value.",
            citations=[],
        ),
        baseline=TariffBaseline(
            hts_code="8413.91",
            duty_rate_pct=5.0,
            duty_basis="ad valorem",
            rationale="Baseline",
            confidence=0.5,
        ),
        mutations=[],
        best_option_id=None,
        optimized=TariffOptimized(
            hts_code="8413.91",
            duty_rate_pct=2.0,
            estimated_savings_per_unit=0.0,
            rationale="Optimized",
            risk_flags=[],
        ),
        compliance_notes=[],
        what_if_candidates=[],
        chosen_mutation=None,
        savings_estimate=None,
        questions_for_user=[],
        citations=[
            TariffCitation(
                claim_type="hts_classification",
                claim="Classification",
                source_id="HTS.84",
                quote="Pumps.",
            )
        ],
    )


def _evidence_bundle() -> list[EvidenceSource]:
    return [
        EvidenceSource(
            source_id="HTS.84",
            source_type="heading",
            title="HTS 84 heading",
            effective_date="2024",
            url=None,
            text="Pumps.",
        ),
        EvidenceSource(
            source_id="CH84.1",
            source_type="chapter_note",
            title="Chapter 84 note",
            effective_date="2024",
            url=None,
            text="Chapter note for machinery.",
        ),
    ]


def test_beam_search_respects_depth_and_expansions() -> None:
    dossier = ProductDossier(
        product_summary="Pump",
        housing_material="steel",
    )
    operators = [
        _TestOperator(
            operator_id="op_a",
            label="A",
            category="material",
            required_inputs=["housing_material"],
            assumptions=[],
            bounds=MutationBounds(),
            compliance_framing="Design change",
            touch_paths=frozenset({"housing.material"}),
        ),
        _TestOperator(
            operator_id="op_b",
            label="B",
            category="material",
            required_inputs=["housing_material"],
            assumptions=[],
            bounds=MutationBounds(),
            compliance_framing="Design change",
            touch_paths=frozenset({"housing.material"}),
        ),
    ]
    result = run_beam_search(
        product_dossier=dossier,
        tariff_dossier=_tariff_dossier(),
        evidence_bundle=_evidence_bundle(),
        operators=operators,
        verifier=_verify_mutation,
        config=SearchConfig(max_depth=2, beam_width=1, max_expansions=1),
    )
    assert result.search_summary.max_depth == 2
    assert result.search_summary.expanded <= 1


def test_dedup_prunes_equivalent_states() -> None:
    dossier = ProductDossier(
        product_summary="Pump",
        housing_material="steel",
    )
    operators = [
        _TestOperator(
            operator_id="op_a",
            label="A",
            category="material",
            required_inputs=["housing_material"],
            assumptions=[],
            bounds=MutationBounds(),
            compliance_framing="Design change",
            touch_paths=frozenset({"housing.material"}),
        ),
        _TestOperator(
            operator_id="op_b",
            label="B",
            category="material",
            required_inputs=["housing_material"],
            assumptions=[],
            bounds=MutationBounds(),
            compliance_framing="Design change",
            touch_paths=frozenset({"housing.material"}),
        ),
    ]
    result = run_beam_search(
        product_dossier=dossier,
        tariff_dossier=_tariff_dossier(),
        evidence_bundle=_evidence_bundle(),
        operators=operators,
        verifier=_verify_mutation,
        config=SearchConfig(max_depth=1, beam_width=2, max_expansions=5),
    )
    assert result.search_summary.dedup_hits >= 1
