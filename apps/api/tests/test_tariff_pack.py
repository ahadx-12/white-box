from __future__ import annotations

import os

from trustai_api.services.job_store import JobStore


def _enable_tariff_fixture(monkeypatch) -> None:
    monkeypatch.setenv("FAKE_LLM", "1")
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
    assert len(mutations) >= 5


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
    assert payload["result"]["proof_id"] == proof_id
