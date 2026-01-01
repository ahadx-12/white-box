from __future__ import annotations

import os

import pytest


def _enable_whatif_fixture(monkeypatch) -> None:
    monkeypatch.setenv("TRUSTAI_LLM_MODE", "fixture")
    monkeypatch.setenv(
        "TRUSTAI_TARIFF_FIXTURE",
        os.path.abspath("apps/api/tests/fixtures/tariff_whatif_threshold_flip.json"),
    )


def test_tariff_whatif_candidates(client, monkeypatch):
    _enable_whatif_fixture(monkeypatch)
    response = client.post(
        "/v1/verify",
        json={"input": "Classify a textile sneaker with rubber outsole."},
        headers={"X-TrustAI-Pack": "tariff"},
    )
    assert response.status_code == 200
    payload = response.json()
    dossier = payload["proof"]["tariff_dossier"]
    candidates = dossier["what_if_candidates"]
    assert 1 <= len(candidates) <= 5
    assert all(candidate["constraints"] for candidate in candidates)
    assert all("estimated_duty_delta" in candidate for candidate in candidates)
    assert dossier["savings_estimate"]["formula"]
    assert dossier["compliance_notes"]


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("TRUSTAI_LLM_MODE") != "live"
    or not (os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_KEY"))
    or not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_AI_KEY")),
    reason="Live tariff test requires TRUSTAI_LLM_MODE=live and both API keys",
)
def test_tariff_whatif_live_smoke(client):
    response = client.post(
        "/v1/verify",
        json={"input": "Classify a running shoe with textile upper and rubber outsole."},
        headers={"X-TrustAI-Pack": "tariff"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"verified", "failed"}
