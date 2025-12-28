from __future__ import annotations

import os

from anthropic import (
    APIConnectionError as AnthropicConnectionError,
)
from anthropic import (
    APITimeoutError as AnthropicTimeoutError,
)
from anthropic import (
    AsyncAnthropic,
)
from anthropic import (
    RateLimitError as AnthropicRateLimitError,
)

from trustai_core.llm.base import LLMClient, LLMError, RateLimitError, TimeoutError
from trustai_core.llm.retry import RetryPolicy, build_idempotency_key, run_with_retry

DEFAULT_CLAUDE_MODEL = "claude-3.5-sonnet"


class AnthropicClient(LLMClient):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_CLAUDE_MODEL,
        timeout_s: float = 30.0,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        resolved_key = api_key or os.getenv("CLAUD_AI_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise LLMError("Anthropic API key is missing")
        self._client = AsyncAnthropic(api_key=resolved_key, timeout=timeout_s)
        self._model = model
        self._retry_policy = retry_policy or RetryPolicy()

    @property
    def model_id(self) -> str:
        return self._model

    async def complete_json(self, prompt: str, schema: dict) -> dict:
        raise LLMError("Anthropic client does not support structured JSON responses")

    async def complete_text(self, prompt: str) -> str:
        async def _call() -> str:
            try:
                response = await self._client.messages.create(
                    model=self._model,
                    max_tokens=512,
                    temperature=0.2,
                    system="Return text only.",
                    messages=[{"role": "user", "content": prompt}],
                    extra_headers={"Idempotency-Key": build_idempotency_key("anthropic")},
                )
            except AnthropicRateLimitError as exc:
                raise RateLimitError(str(exc)) from exc
            except AnthropicTimeoutError as exc:
                raise TimeoutError(str(exc)) from exc
            except AnthropicConnectionError as exc:
                raise LLMError(str(exc)) from exc
            except Exception as exc:  # pragma: no cover - safety net
                raise LLMError(str(exc)) from exc

            content_blocks = response.content or []
            if not content_blocks:
                return ""
            return "".join(block.text for block in content_blocks if hasattr(block, "text"))

        return await run_with_retry(_call, policy=self._retry_policy)
