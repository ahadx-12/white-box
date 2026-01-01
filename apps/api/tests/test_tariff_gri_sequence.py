from __future__ import annotations

import os


def _enable_gri_sequence_fixture(monkeypatch) -> None:
    monkeypatch.setenv("TRUSTAI_LLM_MODE", "fixture")
    monkeypatch.setenv(
        "TRUSTAI_TARIFF_FIXTURE",
        os.path.abspath("apps/api/tests/fixtures/tariff_gri_sequence_violation.json"),
    )


def test_tariff_gri_sequence_violation(client, monkeypatch):
    _enable_gri_sequence_fixture(monkeypatch)
    response = client.post(
        "/v1/verify",
        json={"input": "Classify a textile sneaker with rubber outsole."},
        headers={"X-TrustAI-Pack": "tariff"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["iterations"][0]["accepted"] is False
    assert "gri_sequence_violation" in payload["iterations"][0]["rejected_because"]
    assert any(
        "Sequence Violation" in item for item in payload["iterations"][0]["conflicts"]
    )
    assert payload["iterations"][-1]["gri_trace"]["sequence_ok"] is True
