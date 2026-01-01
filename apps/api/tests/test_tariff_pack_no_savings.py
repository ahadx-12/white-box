from __future__ import annotations

import os


def _enable_tariff_no_savings_fixture(monkeypatch) -> None:
    monkeypatch.setenv("TRUSTAI_LLM_MODE", "fixture")
    monkeypatch.setenv(
        "TRUSTAI_TARIFF_FIXTURE",
        os.path.abspath("apps/api/tests/fixtures/tariff_fixture_no_savings.json"),
    )


def test_tariff_pack_no_savings_fixture(client, monkeypatch):
    _enable_tariff_no_savings_fixture(monkeypatch)
    response = client.post(
        "/v1/verify",
        json={"input": "Classify a duty-free stainless steel bottle."},
        headers={"X-TrustAI-Pack": "tariff"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    dossier = payload["proof"]["tariff_dossier"]
    baseline = dossier["baseline"]["duty_rate_pct"]
    optimized = dossier["optimized"]["duty_rate_pct"]
    assert baseline == 0.0
    assert optimized == 0.0
    assert payload["iterations"]
    assert payload["iterations"][0]["feedback_text"]
    assert payload["iterations"][0]["conflicts"] is not None
    assert payload["iterations"][0]["missing"] is not None
    assert payload["iterations"][0]["unsupported"] is not None
    assert payload["iterations"][0]["top_conflicts"] is not None
    assert payload["iterations"][0]["accepted"] is False
