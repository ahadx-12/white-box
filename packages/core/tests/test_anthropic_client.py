from __future__ import annotations

import pytest

from trustai_core.llm.anthropic_client import AnthropicClient


class DummyAnthropic:
    def __init__(self, api_key: str, timeout: float) -> None:
        self.api_key = api_key
        self.timeout = timeout


def _setup_dummy_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "trustai_core.llm.anthropic_client.AsyncAnthropic",
        DummyAnthropic,
    )


def test_anthropic_client_normalizes_preferred_and_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_dummy_client(monkeypatch)
    monkeypatch.setenv("CLAUD_AI_KEY", "test-key")
    legacy_sonnet = "claude-3" + ".5-sonnet"
    legacy_haiku = "claude-3" + ".5-haiku"
    monkeypatch.setenv("TRUSTAI_ANTHROPIC_MODEL", legacy_sonnet)
    monkeypatch.setenv(
        "TRUSTAI_ANTHROPIC_MODEL_FALLBACKS",
        f"{legacy_haiku},claude-3-5-haiku-20241022",
    )

    client = AnthropicClient()

    assert client.model_id == "claude-3-5-sonnet-20241022"
    assert client._models[1] == "claude-3-5-haiku-20241022"
    assert client._models.count("claude-3-5-haiku-20241022") == 1


def test_anthropic_client_prefers_claude_model_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_dummy_client(monkeypatch)
    monkeypatch.setenv("CLAUD_AI_KEY", "test-key")
    monkeypatch.delenv("TRUSTAI_ANTHROPIC_MODEL", raising=False)
    monkeypatch.setenv("CLAUDE_MODEL", "claude-3" + ".5-haiku")

    client = AnthropicClient()

    assert client.model_id == "claude-3-5-haiku-20241022"
