from __future__ import annotations

from typing import Protocol


class LLMError(Exception):
    """Base error for LLM client failures."""


class RateLimitError(LLMError):
    """Raised when the provider rate limits requests."""


class TimeoutError(LLMError):
    """Raised when the provider times out."""


class LLMClient(Protocol):
    async def complete_json(self, prompt: str, schema: dict) -> dict:
        ...

    async def complete_text(self, prompt: str) -> str:
        ...
