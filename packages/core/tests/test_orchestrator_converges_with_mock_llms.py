from __future__ import annotations

import pytest
from trustai_core.arbiter.evaluator import Evaluator
from trustai_core.core.encoder import AtomEncoder
from trustai_core.core.memory import ItemMemory
from trustai_core.orchestrator.loop import verify_and_fix
from trustai_core.packs.loader import load_pack
from trustai_core.schemas.atoms import AtomModel, ManifestModel
from trustai_core.utils.canonicalize import sort_atoms


class MockPerceiver:
    async def extract_evidence_atoms(self, text: str, pack) -> ManifestModel:
        atoms = [AtomModel(subject="bridge", predicate="status", obj="safe", is_true=True)]
        return ManifestModel(atoms=sort_atoms(atoms))

    async def extract_claim_atoms(self, answer: str, pack) -> ManifestModel:
        obj = "unsafe" if "unsafe" in answer.lower() else "safe"
        atoms = [AtomModel(subject="bridge", predicate="status", obj=obj, is_true=True)]
        return ManifestModel(atoms=sort_atoms(atoms))


class MockReasoner:
    def __init__(self) -> None:
        self.calls = 0

    async def generate_answer(self, user_text: str, pack, evidence=None, feedback=None) -> str:
        self.calls += 1
        if feedback and "Unsupported claims" in feedback:
            return "The bridge is safe."
        if self.calls == 1:
            return "The bridge is unsafe."
        return "The bridge is safe."


@pytest.mark.asyncio
async def test_orchestrator_converges_with_mock_llms() -> None:
    memory = ItemMemory()
    pack = load_pack("general", memory)
    arbiter = Evaluator(AtomEncoder(memory))

    result = await verify_and_fix(
        user_text="Is the bridge safe?",
        pack_name=pack.name,
        perceiver=MockPerceiver(),
        reasoner=MockReasoner(),
        arbiter=arbiter,
        max_iters=3,
    )

    assert result.status == "verified"
    assert len(result.iterations) <= 3
    scores = [trace.score for trace in result.iterations]
    assert scores[-1] >= 0.92
