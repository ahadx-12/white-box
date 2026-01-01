from __future__ import annotations

from trustai_core.packs.tariff.models import (
    Mutation,
    TariffBaseline,
    TariffCitation,
    TariffDossier,
    TariffOptimized,
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
        questions_for_user=[],
        citations=[
            TariffCitation(
                evidence_index=0,
                quote="Test quote",
                claim="Test claim",
            )
        ],
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
