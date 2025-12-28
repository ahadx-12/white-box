from __future__ import annotations

import os

import pytest

env_enabled = os.getenv("TRUSTAI_LIVE") == "1" or os.getenv("TRUSTAI_LLM_MODE") == "live"
keys_present = bool(os.getenv("OPEN_AI_KEY") or os.getenv("OPENAI_API_KEY")) and bool(
    os.getenv("CLAUD_AI_KEY") or os.getenv("ANTHROPIC_API_KEY")
)


@pytest.mark.skipif(not (env_enabled and keys_present), reason="Live test disabled")
def test_verify_live(client):
    response = client.post("/v1/verify", json={"input": "What is 2+2?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"verified", "failed"}
