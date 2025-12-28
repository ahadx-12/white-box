from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import dataclass

from trustai_core.agents.perceiver import Perceiver
from trustai_core.agents.reasoner import Reasoner
from trustai_core.arbiter.evaluator import Evaluator
from trustai_core.core.encoder import AtomEncoder
from trustai_core.core.memory import ItemMemory
from trustai_core.llm.anthropic_client import AnthropicClient
from trustai_core.llm.openai_client import OpenAIClient
from trustai_core.orchestrator.loop import VerificationFailure, verify_and_fix
from trustai_core.packs.loader import load_pack
from trustai_core.schemas.atoms import AtomModel, ManifestModel
from trustai_core.utils.canonicalize import sort_atoms


@dataclass
class MockPerceiver:
    async def extract_evidence_atoms(self, text: str, pack) -> ManifestModel:
        atoms = [
            AtomModel(
                subject="bridge",
                predicate="status",
                obj="safe",
                is_true=True,
                confidence=1.0,
            )
        ]
        return ManifestModel(atoms=sort_atoms(atoms))

    async def extract_claim_atoms(self, answer: str, pack) -> ManifestModel:
        obj = "unsafe" if "unsafe" in answer.lower() else "safe"
        atoms = [
            AtomModel(
                subject="bridge",
                predicate="status",
                obj=obj,
                is_true=True,
                confidence=1.0,
            )
        ]
        return ManifestModel(atoms=sort_atoms(atoms))


@dataclass
class MockReasoner:
    call_count: int = 0

    async def generate_answer(self, user_text: str, pack, evidence=None, feedback=None) -> str:
        self.call_count += 1
        if feedback and "Unsupported claims" in feedback:
            return "The bridge is safe."
        if self.call_count == 1:
            return "The bridge is unsafe."
        return "The bridge is safe."


async def run_demo(live: bool) -> None:
    user_text = "Is the bridge safe?"
    pack_name = "general"

    if live:
        perceiver = Perceiver(OpenAIClient())
        reasoner = Reasoner(AnthropicClient())
        memory = ItemMemory()
        pack = load_pack(pack_name, memory)
        arbiter = Evaluator(AtomEncoder(memory))
    else:
        perceiver = MockPerceiver()
        reasoner = MockReasoner()
        memory = ItemMemory()
        pack = load_pack(pack_name, memory)
        arbiter = Evaluator(AtomEncoder(memory))

    try:
        result = await verify_and_fix(
            user_text=user_text,
            pack_name=pack.name,
            perceiver=perceiver,
            reasoner=reasoner,
            arbiter=arbiter,
        )
    except VerificationFailure as exc:
        result = exc.result

    print("Status:", result.status)
    print("Proof ID:", result.proof_id)
    print("Final Answer:", result.final_answer)
    print("Iteration Scores:", [trace.score for trace in result.iterations])
    print("Explain Summary:", result.explain.get("summary"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run TrustAI Week-2 demo")
    parser.add_argument("--live", action="store_true", help="Enable live LLM calls")
    args = parser.parse_args()

    live_enabled = args.live or os.getenv("TRUSTAI_LIVE") == "1"
    asyncio.run(run_demo(live_enabled))
