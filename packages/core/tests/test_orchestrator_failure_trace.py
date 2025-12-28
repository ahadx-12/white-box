from __future__ import annotations

import pytest
from trustai_core.arbiter.evaluator import Evaluator
from trustai_core.core.encoder import AtomEncoder
from trustai_core.core.memory import ItemMemory
from trustai_core.orchestrator.loop import VerificationFailure, verify_and_fix
from trustai_core.packs.loader import load_pack
from trustai_core.schemas.atoms import AtomModel, ManifestModel
from trustai_core.utils.canonicalize import sort_atoms


class StubbornPerceiver:
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
                obj="unsafe",
                is_true=True,
                confidence=1.0,
            )
        ]
        return ManifestModel(atoms=sort_atoms(atoms))


class StubbornReasoner:
    async def generate_answer(self, user_text: str, pack, evidence=None, feedback=None) -> str:
        return "The bridge is unsafe."


@pytest.mark.asyncio
async def test_orchestrator_failure_trace() -> None:
    memory = ItemMemory()
    pack = load_pack("general", memory)
    arbiter = Evaluator(AtomEncoder(memory))

    with pytest.raises(VerificationFailure) as exc:
        await verify_and_fix(
            user_text="Is the bridge safe?",
            pack_name=pack.name,
            perceiver=StubbornPerceiver(),
            reasoner=StubbornReasoner(),
            arbiter=arbiter,
            max_iters=2,
        )

    result = exc.value.result
    assert result.status == "failed"
    assert len(result.iterations) == 2
    assert result.iterations[-1].mismatch.unsupported_claims
