from __future__ import annotations

import pytest
from trustai_core.arbiter.evaluator import Evaluator
from trustai_core.core.encoder import AtomEncoder
from trustai_core.core.memory import ItemMemory
from trustai_core.orchestrator.loop import verify_and_fix
from trustai_core.packs.loader import load_pack
from trustai_core.schemas.atoms import AtomModel, ManifestModel
from trustai_core.utils.canonicalize import sort_atoms


class StablePerceiver:
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


class StableReasoner:
    async def generate_answer(self, user_text: str, pack, evidence=None, feedback=None) -> str:
        return "The bridge is safe."


@pytest.mark.asyncio
async def test_proof_determinism() -> None:
    memory = ItemMemory()
    pack = load_pack("general", memory)
    arbiter = Evaluator(AtomEncoder(memory))

    result_a = await verify_and_fix(
        user_text="Is the bridge safe?",
        pack_name=pack.name,
        perceiver=StablePerceiver(),
        reasoner=StableReasoner(),
        arbiter=arbiter,
        max_iters=1,
    )

    result_b = await verify_and_fix(
        user_text="Is the bridge safe?",
        pack_name=pack.name,
        perceiver=StablePerceiver(),
        reasoner=StableReasoner(),
        arbiter=arbiter,
        max_iters=1,
    )

    assert result_a.proof_id == result_b.proof_id
    assert result_a.canonical_json() == result_b.canonical_json()
