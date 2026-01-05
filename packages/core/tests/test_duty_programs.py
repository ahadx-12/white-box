from __future__ import annotations

from trustai_core.packs.tariff_ca.duty.programs import CAPreferencePrograms
from trustai_core.packs.tariff_us.duty.programs import USPreferencePrograms


def test_usmca_wholly_obtained_eligible() -> None:
    programs = USPreferencePrograms()
    result = programs.evaluate(
        "USMCA",
        {
            "origin_country": "CA",
            "line_id": "8544.11",
        },
    )
    assert result is not None
    assert result.status == "eligible"
    assert "USMCA.WHOLLY_OBTAINED.V1" in result.evidence


def test_usmca_tariff_shift_eligible() -> None:
    programs = USPreferencePrograms()
    result = programs.evaluate(
        "USMCA",
        {
            "origin_country": "CN",
            "line_id": "8544.11",
            "bom": {
                "components": [
                    {"hs_chapter": "73"},
                    {"hs_chapter": "84"},
                ]
            },
            "manufacturing": {"steps": [{"country": "MX"}]},
        },
    )
    assert result is not None
    assert result.status == "eligible"
    assert "USMCA.TARIFF_SHIFT.CH85.V1" in result.evidence


def test_usmca_missing_inputs_returns_unknown() -> None:
    programs = USPreferencePrograms()
    result = programs.evaluate(
        "USMCA",
        {
            "origin_country": "CN",
            "line_id": "8544.11",
        },
    )
    assert result is not None
    assert result.status == "unknown"
    assert "bom.components[*].hs_chapter" in result.missing_inputs


def test_cusma_wholly_obtained_eligible() -> None:
    programs = CAPreferencePrograms()
    result = programs.evaluate(
        "CUSMA",
        {
            "origin_country": "US",
            "line_id": "7318.15",
        },
    )
    assert result is not None
    assert result.status == "eligible"
    assert "CUSMA.WHOLLY_OBTAINED.V1" in result.evidence
