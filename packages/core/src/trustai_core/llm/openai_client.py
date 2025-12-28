from __future__ import annotations

import os

import orjson
from openai import (
    APIConnectionError as OpenAIConnectionError,
)
from openai import (
    APITimeoutError as OpenAITimeoutError,
)
from openai import (
    AsyncOpenAI,
)
from openai import (
    RateLimitError as OpenAIRateLimitError,
)

from trustai_core.llm.base import LLMClient, LLMError, RateLimitError, TimeoutError
from trustai_core.llm.retry import RetryPolicy, build_idempotency_key, run_with_retry

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


class OpenAIClient(LLMClient):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_OPENAI_MODEL,
        timeout_s: float = 30.0,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        resolved_key = api_key or os.getenv("OPEN_AI_KEY") or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            raise LLMError("OpenAI API key is missing")
        self._client = AsyncOpenAI(api_key=resolved_key, timeout=timeout_s)
        self._model = model
        self._retry_policy = retry_policy or RetryPolicy()

    @property
    def model_id(self) -> str:
        return self._model

    async def complete_json(self, prompt: str, schema: dict) -> dict:
        async def _call() -> dict:
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    temperature=0,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": "Return JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    extra_headers={"Idempotency-Key": build_idempotency_key("openai")},
                )
            except OpenAIRateLimitError as exc:
                raise RateLimitError(str(exc)) from exc
            except OpenAITimeoutError as exc:
                raise TimeoutError(str(exc)) from exc
            except OpenAIConnectionError as exc:
                raise LLMError(str(exc)) from exc
            except Exception as exc:  # pragma: no cover - safety net
                raise LLMError(str(exc)) from exc

            content = response.choices[0].message.content or "{}"
            try:
                payload = orjson.loads(content)
            except orjson.JSONDecodeError as exc:
                raise LLMError("OpenAI returned invalid JSON") from exc
            if not isinstance(payload, dict):
                raise LLMError("OpenAI returned non-object JSON")
            return payload

        return await run_with_retry(_call, policy=self._retry_policy)

    async def complete_text(self, prompt: str) -> str:
        async def _call() -> str:
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": "Return text only."},
                        {"role": "user", "content": prompt},
                    ],
                    extra_headers={"Idempotency-Key": build_idempotency_key("openai")},
                )
            except OpenAIRateLimitError as exc:
                raise RateLimitError(str(exc)) from exc
            except OpenAITimeoutError as exc:
                raise TimeoutError(str(exc)) from exc
            except OpenAIConnectionError as exc:
                raise LLMError(str(exc)) from exc
            except Exception as exc:  # pragma: no cover - safety net
                raise LLMError(str(exc)) from exc

            return response.choices[0].message.content or ""

        return await run_with_retry(_call, policy=self._retry_policy)
