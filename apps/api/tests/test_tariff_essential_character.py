from __future__ import annotations

import os


def _enable_essential_character_fixture(monkeypatch) -> None:
    monkeypatch.setenv("TRUSTAI_LLM_MODE", "fixture")
    monkeypatch.setenv(
        "TRUSTAI_TARIFF_FIXTURE",
        os.path.abspath("apps/api/tests/fixtures/tariff_essential_character_mismatch.json"),
    )


def test_tariff_essential_character_mismatch(client, monkeypatch):
    _enable_essential_character_fixture(monkeypatch)
    response = client.post(
        "/v1/verify",
        json={"input": "Classify a mixed-material wearable device."},
        headers={"X-TrustAI-Pack": "tariff"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["iterations"][0]["accepted"] is False
    assert "essential_character_mismatch" in payload["iterations"][0]["rejected_because"]
    assert payload["iterations"][0]["essential_character_score"] < 0.58
    assert payload["iterations"][-1]["accepted"] is True
