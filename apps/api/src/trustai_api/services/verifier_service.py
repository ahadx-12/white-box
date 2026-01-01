from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from trustai_core.agents.perceiver import Perceiver
from trustai_core.agents.reasoner import Reasoner
from trustai_core.arbiter.evaluator import SCORE_THRESHOLD
from trustai_core.llm.anthropic_client import AnthropicClient
from trustai_core.llm.base import LLMClient
from trustai_core.llm.openai_client import OpenAIClient
from trustai_core.orchestrator.loop import VerificationFailure, verify_and_fix
from trustai_core.packs.registry import PackContext, get_pack_runner
from trustai_core.packs.tariff.models import TariffVerificationResult
from trustai_core.schemas.proof import VerificationResult

from trustai_api.services.mock_llm import MockLLMClient
from trustai_api.settings import Settings

VerifierFn = Callable[..., Awaitable[VerificationResult]]


@dataclass
class VerifyOptions:
    max_iters: int | None = None
    threshold: float | None = None
    min_mutations: int | None = None


class VerifierService:
    def __init__(
        self,
        settings: Settings,
        verifier_fn: VerifierFn | None = None,
        perceiver_client_factory: Callable[[], Any] | None = None,
        reasoner_client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._settings = settings
        self._verifier_fn = verifier_fn or verify_and_fix
        self._perceiver_client_factory = perceiver_client_factory or self._default_perceiver
        self._reasoner_client_factory = reasoner_client_factory or self._default_reasoner
        self._perceiver: Perceiver | None = None
        self._reasoner: Reasoner | None = None

    def _default_perceiver(self) -> LLMClient:
        if self._settings.llm_mode != "live":
            return MockLLMClient()
        return OpenAIClient(model=self._settings.openai_model)

    def _default_reasoner(self) -> LLMClient:
        if self._settings.llm_mode != "live":
            return MockLLMClient()
        return AnthropicClient(model=self._settings.claude_model)

    def _get_perceiver(self) -> Perceiver:
        if self._perceiver is None:
            self._perceiver = Perceiver(self._perceiver_client_factory())
        return self._perceiver

    def _get_reasoner(self) -> Reasoner:
        if self._reasoner is None:
            self._reasoner = Reasoner(self._reasoner_client_factory())
        return self._reasoner

    def debug_info(self) -> dict[str, object]:
        perceiver_calls = []
        reasoner_calls = []
        if self._perceiver and hasattr(self._perceiver, "get_debug_calls"):
            perceiver_calls = self._perceiver.get_debug_calls()
        if self._reasoner and hasattr(self._reasoner, "get_debug_calls"):
            reasoner_calls = self._reasoner.get_debug_calls()
        return {"perceiver": perceiver_calls, "reasoner": reasoner_calls}

    def reset_debug(self) -> None:
        if self._perceiver and hasattr(self._perceiver, "reset_debug"):
            self._perceiver.reset_debug()
        if self._reasoner and hasattr(self._reasoner, "reset_debug"):
            self._reasoner.reset_debug()

    async def verify_sync(
        self,
        input_text: str,
        pack: str,
        options: VerifyOptions | None = None,
        evidence: list[str] | None = None,
    ) -> VerificationResult | TariffVerificationResult:
        self.reset_debug()
        resolved_options = options or VerifyOptions()
        max_iters = resolved_options.max_iters or 5
        threshold = (
            resolved_options.threshold
            if resolved_options.threshold is not None
            else SCORE_THRESHOLD
        )
        pack_runner = get_pack_runner(
            pack,
            PackContext(
                llm_mode=self._settings.llm_mode,
                openai_model=self._settings.openai_model,
                claude_model=self._settings.claude_model,
                openai_client_factory=self._openai_client,
                anthropic_client_factory=self._anthropic_client,
            ),
        )
        if pack_runner:
            options_payload: dict[str, object] = {"max_iters": max_iters, "threshold": threshold}
            if resolved_options.min_mutations is not None:
                options_payload["min_mutations"] = resolved_options.min_mutations
            if evidence:
                options_payload["evidence"] = evidence
            return await pack_runner.run(input_text, options_payload)
        try:
            return await self._verifier_fn(
                user_text=input_text,
                pack_name=pack,
                perceiver=self._get_perceiver(),
                reasoner=self._get_reasoner(),
                arbiter=None,
                max_iters=max_iters,
                threshold=threshold,
            )
        except VerificationFailure as exc:
            return exc.result

    def _openai_client(self) -> LLMClient:
        if self._settings.llm_mode != "live":
            return MockLLMClient()
        return OpenAIClient(model=self._settings.openai_model)

    def _anthropic_client(self) -> LLMClient:
        if self._settings.llm_mode != "live":
            return MockLLMClient()
        return AnthropicClient(model=self._settings.claude_model)
