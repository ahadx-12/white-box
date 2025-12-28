from __future__ import annotations

from trustai_core.llm.base import LLMClient


class MockLLMClient(LLMClient):
    async def complete_json(self, prompt: str, schema: dict) -> dict:
        return {"atoms": []}

    async def complete_text(self, prompt: str) -> str:
        return ""
