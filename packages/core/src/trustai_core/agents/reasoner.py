from __future__ import annotations

from trustai_core.agents.prompts import build_reasoner_prompt
from trustai_core.llm.base import LLMClient
from trustai_core.packs.types import PackModel
from trustai_core.schemas.atoms import ManifestModel


class Reasoner:
    def __init__(self, client: LLMClient) -> None:
        self._client = client

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
        return await self._client.complete_text(prompt)
