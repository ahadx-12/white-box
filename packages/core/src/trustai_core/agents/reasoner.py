from __future__ import annotations

import time

from trustai_core.agents.prompts import build_reasoner_prompt
from trustai_core.llm.base import LLMClient
from trustai_core.packs.types import PackModel
from trustai_core.schemas.atoms import ManifestModel
from trustai_core.utils.hashing import sha256_canonical_json


class Reasoner:
    def __init__(self, client: LLMClient) -> None:
        self._client = client
        self._debug_calls: list[dict[str, object]] = []

    async def generate_answer(
        self,
        user_text: str,
        pack: PackModel,
        evidence: ManifestModel | None = None,
        feedback: str | None = None,
    ) -> str:
        evidence_block = None
        if evidence is not None:
            evidence_block = "\n".join(
                f"- ({atom.subject}, {atom.predicate}, {atom.obj}, {atom.is_true})"
                for atom in evidence.atoms
            )
        prompt = build_reasoner_prompt(user_text, evidence_block, feedback)
        start = time.monotonic()
        response = await self._client.complete_text(prompt)
        elapsed = time.monotonic() - start
        self._debug_calls.append(
            {
                "role": "reasoner",
                "prompt_hash": sha256_canonical_json(prompt),
                "prompt_tokens_estimate": len(prompt.split()),
                "latency_bucket": _latency_bucket(elapsed),
                "model_id": _model_id(self._client),
            }
        )
        return response

    def reset_debug(self) -> None:
        self._debug_calls = []

    def get_debug_calls(self) -> list[dict[str, object]]:
        return list(self._debug_calls)


def _latency_bucket(elapsed_s: float) -> str:
    if elapsed_s < 0.2:
        return "<200ms"
    if elapsed_s < 1.0:
        return "200ms-1s"
    if elapsed_s < 3.0:
        return "1s-3s"
    return ">3s"


def _model_id(client: LLMClient) -> str | None:
    return (
        getattr(client, "model_id", None)
        or getattr(client, "model", None)
        or getattr(client, "_model", None)
    )
