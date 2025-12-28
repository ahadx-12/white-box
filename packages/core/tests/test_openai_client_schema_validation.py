from __future__ import annotations

import pytest
from pydantic import ValidationError
from trustai_core.agents.perceiver import Perceiver
from trustai_core.core.memory import ItemMemory
from trustai_core.packs.loader import load_pack
from trustai_core.schemas.atoms import ManifestModel


class BadClient:
    async def complete_json(self, prompt: str, schema: dict) -> dict:
        return {"bad": "shape"}

    async def complete_text(self, prompt: str) -> str:
        return ""


class GoodClient:
    async def complete_json(self, prompt: str, schema: dict) -> dict:
        return {
            "atoms": [
                {
                    "subject": "Bridge",
                    "predicate": "Status",
                    "obj": "secured",
                    "is_true": True,
                    "confidence": 0.9,
                },
                {
                    "subject": "Bridge",
                    "predicate": "Status",
                    "obj": "unsafe",
                    "is_true": True,
                    "confidence": 0.8,
                },
            ]
        }

    async def complete_text(self, prompt: str) -> str:
        return ""


@pytest.mark.asyncio
async def test_openai_client_schema_validation() -> None:
    pack = load_pack("general", ItemMemory())
    perceiver = Perceiver(BadClient())
    with pytest.raises(ValidationError):
        await perceiver.extract_evidence_atoms("text", pack)

    good_perceiver = Perceiver(GoodClient())
    manifest = await good_perceiver.extract_evidence_atoms("text", pack)
    assert isinstance(manifest, ManifestModel)
    assert [atom.obj for atom in manifest.atoms] == ["safe", "unsafe"]
