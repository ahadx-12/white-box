from __future__ import annotations

import os

import pytest
from trustai_api.services.job_store import JobStore


def _enable_tariff_fixture(monkeypatch) -> None:
    monkeypatch.setenv("TRUSTAI_LLM_MODE", "fixture")
    monkeypatch.setenv(
        "TRUSTAI_TARIFF_FIXTURE",
        os.path.abspath("apps/api/tests/fixtures/tariff_fixture.json"),
    )


def test_tariff_pack_sync_smoke(client, app, monkeypatch):
    _enable_tariff_fixture(monkeypatch)
    response = client.post(
        "/v1/verify",
        json={"input": "Classify a textile sneaker with rubber outsole."},
        headers={"X-TrustAI-Pack": "tariff"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "verified"
    assert payload["iterations"]
    assert "Baseline" in payload["final_answer"]
    assert "Optimized" in payload["final_answer"]
    assert payload["proof_id"]

    proof_response = client.get(f"/v1/proofs/{payload['proof_id']}")
    assert proof_response.status_code == 200
    proof_payload = proof_response.json()
    mutations = proof_payload["payload"]["proof"]["tariff_dossier"]["mutations"]
    assert len(mutations) >= 8


def test_tariff_pack_reduces_or_explains(client, monkeypatch):
    _enable_tariff_fixture(monkeypatch)
    response = client.post(
        "/v1/verify",
        json={"input": "Classify a textile sneaker with rubber outsole."},
        headers={"X-TrustAI-Pack": "tariff"},
    )
    payload = response.json()
    dossier = payload["proof"]["tariff_dossier"]
    baseline = dossier["baseline"]["duty_rate_pct"]
    optimized = dossier["optimized"]["duty_rate_pct"]
    if baseline is not None and optimized is not None:
        assert optimized <= baseline
    else:
        assert dossier["questions_for_user"]


def test_tariff_pack_evidence_citations(client, monkeypatch):
    _enable_tariff_fixture(monkeypatch)
    response = client.post(
        "/v1/verify",
        json={
            "input": "Classify a textile sneaker with rubber outsole.",
            "evidence": [
                "Lab report: textile upper dominates surface area; rubber outsole.",
                "Invoice: standard import, no preferential program.",
            ],
        },
        headers={"X-TrustAI-Pack": "tariff"},
    )
    payload = response.json()
    dossier = payload["proof"]["tariff_dossier"]
    assert dossier["citations"]
    assert all("evidence_index" in item for item in dossier["citations"])


def test_tariff_pack_async_job(client, app, monkeypatch):
    _enable_tariff_fixture(monkeypatch)
    async_response = client.post(
        "/v1/verify?mode=async",
        json={"input": "Classify a textile sneaker with rubber outsole."},
        headers={"X-TrustAI-Pack": "tariff"},
    )
    assert async_response.status_code == 200
    job_id = async_response.json()["job_id"]

    sync_response = client.post(
        "/v1/verify",
        json={"input": "Classify a textile sneaker with rubber outsole."},
        headers={"X-TrustAI-Pack": "tariff"},
    )
    proof_id = sync_response.json()["proof_id"]

    session = app.state.SessionLocal()
    try:
        job_store = JobStore()
        job = job_store.get(session, job_id)
        assert job is not None
        job_store.set_done(session, job, proof_id)
    finally:
        session.close()

    job_response = client.get(f"/v1/jobs/{job_id}")
    assert job_response.status_code == 200
    payload = job_response.json()
    assert payload["status"] == "done"
    proof_id = payload["proof_id"]
    assert proof_id

    proof_response = client.get(f"/v1/proofs/{proof_id}")
    assert proof_response.status_code == 200
    assert proof_response.json()["payload"]["proof"]["tariff_dossier"]


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("TRUSTAI_LLM_MODE") != "live"
    or not (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("OPEN_AI_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("CLAUD_AI_KEY")
    ),
    reason="Live tariff test requires TRUSTAI_LLM_MODE=live and API keys",
)
def test_tariff_pack_live_smoke(client):
    response = client.post(
        "/v1/verify",
        json={"input": "Classify a ceramic coffee mug."},
        headers={"X-TrustAI-Pack": "tariff"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"verified", "failed"}
