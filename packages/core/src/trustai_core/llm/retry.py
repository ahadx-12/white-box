from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from trustai_core.llm.base import LLMError, RateLimitError, TimeoutError


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    min_wait: float = 0.5
    max_wait: float = 4.0

    def build(self) -> AsyncRetrying:
        return AsyncRetrying(
            stop=stop_after_attempt(self.max_attempts),
            wait=wait_exponential(min=self.min_wait, max=self.max_wait),
            retry=retry_if_exception_type((RateLimitError, TimeoutError, LLMError)),
            reraise=True,
        )


def build_idempotency_key(prefix: str = "trustai") -> str:
    return f"{prefix}-{uuid4()}"


async def run_with_retry(fn, *args, policy: RetryPolicy | None = None, **kwargs):
    retrying = (policy or RetryPolicy()).build()
    async for attempt in retrying:
        with attempt:
            return await fn(*args, **kwargs)
    raise LLMError("Retry attempts exhausted")  # pragma: no cover
