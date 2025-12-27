from __future__ import annotations

import asyncio
import time

import pytest
from trustai_core.arbiter.evaluator import Evaluator
from trustai_core.core.encoder import AtomEncoder
from trustai_core.core.memory import ItemMemory
from trustai_core.orchestrator.loop import verify_and_fix
from trustai_core.packs.loader import load_pack
from trustai_core.schemas.atoms import AtomModel, ManifestModel
from trustai_core.utils.canonicalize import sort_atoms


class SlowPerceiver:
    async def extract_evidence_atoms(self, text: str, pack) -> ManifestModel:
        await asyncio.sleep(0.25)
        atoms = [AtomModel(subject="bridge", predicate="status", obj="safe", is_true=True)]
        return ManifestModel(atoms=sort_atoms(atoms))

    async def extract_claim_atoms(self, answer: str, pack) -> ManifestModel:
        atoms = [AtomModel(subject="bridge", predicate="status", obj="safe", is_true=True)]
        return ManifestModel(atoms=sort_atoms(atoms))


class SlowReasoner:
    async def generate_answer(self, user_text: str, pack, evidence=None, feedback=None) -> str:
        await asyncio.sleep(0.25)
        return "The bridge is safe."


@pytest.mark.asyncio
async def test_async_gather_timing() -> None:
    memory = ItemMemory()
    pack = load_pack("general", memory)
    arbiter = Evaluator(AtomEncoder(memory))

    start = time.monotonic()
    result = await verify_and_fix(
        user_text="Is the bridge safe?",
        pack_name=pack.name,
        perceiver=SlowPerceiver(),
        reasoner=SlowReasoner(),
        arbiter=arbiter,
        max_iters=1,
        enable_parallel_prepass=True,
    )
    elapsed = time.monotonic() - start

    assert result.status == "verified"
    assert elapsed < 0.4
