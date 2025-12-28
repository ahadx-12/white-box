from __future__ import annotations

import pytest
from trustai_core.arbiter.evaluator import Evaluator
from trustai_core.core.encoder import AtomEncoder
from trustai_core.core.memory import ItemMemory
from trustai_core.orchestrator.loop import verify_and_fix
from trustai_core.packs.loader import load_pack
from trustai_core.schemas.atoms import AtomModel, ManifestModel
from trustai_core.utils.canonicalize import sort_atoms


class FastPerceiver:
    async def extract_evidence_atoms(self, text: str, pack) -> ManifestModel:
        atoms = [
            AtomModel(subject="door", predicate="state", obj="open", is_true=True, confidence=1.0)
        ]
        return ManifestModel(atoms=sort_atoms(atoms))

    async def extract_claim_atoms(self, answer: str, pack) -> ManifestModel:
        obj = "closed" if "closed" in answer.lower() else "open"
        atoms = [
            AtomModel(subject="door", predicate="state", obj=obj, is_true=True, confidence=1.0)
        ]
        return ManifestModel(atoms=sort_atoms(atoms))


class FastReasoner:
    def __init__(self) -> None:
        self.calls = 0

    async def generate_answer(self, user_text: str, pack, evidence=None, feedback=None) -> str:
        self.calls += 1
        if feedback and "MUST REMOVE" in feedback:
            return "FINAL_ANSWER: The door is open.\nThe evidence states the door is open."
        return "The door is closed."


@pytest.mark.asyncio
async def test_convergence_speed() -> None:
    memory = ItemMemory()
    pack = load_pack("general", memory)
    arbiter = Evaluator(AtomEncoder(memory))

    result = await verify_and_fix(
        user_text="Fact: The door is open. Answer whether the door is closed.",
        pack_name=pack.name,
        perceiver=FastPerceiver(),
        reasoner=FastReasoner(),
        arbiter=arbiter,
        max_iters=3,
    )

    assert result.status == "verified"
    assert len(result.iterations) <= 2
    assert result.iterations[-1].score >= 0.92
