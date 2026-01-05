from __future__ import annotations

import asyncio
import json
from pathlib import Path

from trustai_core.packs.registry import PackContext, get_pack_runner
class _NullClient:
    async def complete_text(self, prompt: str) -> str:
        raise RuntimeError("fixture only")

    async def complete_json(self, prompt: str, schema: dict) -> dict:
        raise RuntimeError("fixture only")


def _context(mode: str) -> PackContext:
    return PackContext(
        llm_mode=mode,
        openai_model="fixture",
        claude_model="fixture",
        openai_client_factory=_NullClient,
        anthropic_client_factory=_NullClient,
    )


def test_pack_routing_uses_jurisdiction_evidence(monkeypatch) -> None:
    monkeypatch.setenv("TRUSTAI_LLM_MODE", "fixture")
    input_payload = {
        "product_dossier": {"product_summary": "USB-C insulated charging cable."},
        "importing_country": "US",
        "exporting_country": "CN",
        "origin_country": "CN",
    }
    input_text = json.dumps(input_payload)

    us_runner = get_pack_runner("tariff_us", _context("fixture"))
    ca_runner = get_pack_runner("tariff_ca", _context("fixture"))
    assert us_runner is not None
    assert ca_runner is not None

    fixture_us = Path("storage/benchmarks/tariff_us/fixtures/fixture_positive.json")
    fixture_ca = Path("storage/benchmarks/tariff_ca/fixtures/fixture_positive.json")
    monkeypatch.setenv("TRUSTAI_TARIFF_FIXTURE", str(fixture_us))
    us_result = asyncio.run(us_runner.run(input_text, options=None))
    monkeypatch.setenv("TRUSTAI_TARIFF_FIXTURE", str(fixture_ca))
    ca_result = asyncio.run(ca_runner.run(input_text, options=None))

    us_sources = [source["source_id"] for source in us_result.evidence_bundle or []]
    ca_sources = [source["source_id"] for source in ca_result.evidence_bundle or []]
    assert all(source_id.startswith("US.") for source_id in us_sources)
    assert all(source_id.startswith("CA.") for source_id in ca_sources)
