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
    NotFoundError as AnthropicNotFoundError,
)
from anthropic import (
    RateLimitError as AnthropicRateLimitError,
)

from trustai_core.llm.base import LLMClient, LLMError, RateLimitError, TimeoutError
from trustai_core.llm.retry import RetryPolicy, build_idempotency_key, run_with_retry

DEFAULT_CLAUDE_MODELS = [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-3-sonnet-20240229",
]
DEFAULT_CLAUDE_MODEL = DEFAULT_CLAUDE_MODELS[0]
_CANON_MODEL_ALIASES = {
    "claude-3-5-sonnet": DEFAULT_CLAUDE_MODELS[0],
    "claude-3-5-haiku": DEFAULT_CLAUDE_MODELS[1],
}
_LEGACY_MODEL_PREFIX = "claude-3" + ".5-"
_LEGACY_MODEL_MAP = {
    "sonnet": DEFAULT_CLAUDE_MODELS[0],
    "haiku": DEFAULT_CLAUDE_MODELS[1],
}


class ModelNotFoundError(LLMError):
    """Raised when a requested model is not found."""


def _parse_model_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _normalize_model_id(model: str) -> str:
    cleaned = model.strip()
    if cleaned.startswith(_LEGACY_MODEL_PREFIX):
        suffix = cleaned[len(_LEGACY_MODEL_PREFIX) :]
        return _LEGACY_MODEL_MAP.get(suffix, cleaned)
    return _CANON_MODEL_ALIASES.get(cleaned, cleaned)


def _dedupe(models: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for model in models:
        if model in seen:
            continue
        seen.add(model)
        unique.append(model)
    return unique


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
        preferred_model = (
            os.getenv("TRUSTAI_ANTHROPIC_MODEL")
            or os.getenv("CLAUDE_MODEL")
            or os.getenv("ANTHROPIC_MODEL")
        )
        candidates: list[str] = []
        if preferred_model:
            candidates.append(_normalize_model_id(preferred_model))
        elif model:
            candidates.append(_normalize_model_id(model))
        fallback_models = [
            _normalize_model_id(m)
            for m in _parse_model_list(os.getenv("TRUSTAI_ANTHROPIC_MODEL_FALLBACKS"))
        ]
        candidates.extend(fallback_models)
        candidates.extend(DEFAULT_CLAUDE_MODELS)
        self._models = _dedupe(candidates)
        self._retry_policy = retry_policy or RetryPolicy()

    @property
    def model_id(self) -> str:
        if not self._models:
            return ""
        return self._models[0]

    async def complete_json(self, prompt: str, schema: dict) -> dict:
        raise LLMError("Anthropic client does not support structured JSON responses")

    async def _call_model(self, prompt: str, model: str) -> str:
        try:
            response = await self._client.messages.create(
                model=model,
                max_tokens=512,
                temperature=0.2,
                system="Return text only.",
                messages=[{"role": "user", "content": prompt}],
                extra_headers={"Idempotency-Key": build_idempotency_key("anthropic")},
            )
        except AnthropicNotFoundError as exc:
            raise ModelNotFoundError(str(exc)) from exc
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

    async def complete_text(self, prompt: str) -> str:
        attempted: list[str] = []
        last_error: LLMError | None = None
        for model in self._models:
            attempted.append(model)
            try:
                return await run_with_retry(
                    lambda: self._call_model(prompt, model),
                    policy=self._retry_policy,
                )
            except ModelNotFoundError as exc:
                last_error = exc
                continue
        raise LLMError(f"Anthropic model not found. Tried models: {attempted}") from last_error
