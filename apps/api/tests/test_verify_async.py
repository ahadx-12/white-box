from __future__ import annotations

import orjson
from trustai_api.db.models import Job


def test_verify_async_enqueues_job(client, app):
    response = client.post("/v1/verify?mode=async", json={"input": "Hello"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    job_id = payload["job_id"]

    session_local = app.state.SessionLocal
    session = session_local()
    try:
        job = session.get(Job, job_id)
        assert job is not None
        assert job.status == "queued"
        assert orjson.loads(job.payload_json)["input"] == "Hello"
    finally:
        session.close()
