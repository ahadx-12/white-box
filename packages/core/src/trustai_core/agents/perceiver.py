from __future__ import annotations

from pydantic import ValidationError

from trustai_core.agents.prompts import (
    ATOM_MANIFEST_SCHEMA,
    build_claim_prompt,
    build_evidence_prompt,
)
from trustai_core.llm.base import LLMClient
from trustai_core.packs.types import PackModel
from trustai_core.schemas.atoms import ManifestModel
from trustai_core.utils.canonicalize import canonicalize_atom, sort_atoms


class Perceiver:
    def __init__(self, client: LLMClient) -> None:
        self._client = client

    async def extract_evidence_atoms(self, text: str, pack: PackModel) -> ManifestModel:
        prompt = build_evidence_prompt(text)
        payload = await self._client.complete_json(prompt, ATOM_MANIFEST_SCHEMA)
        return self._validate_manifest(payload, pack)

    async def extract_claim_atoms(self, answer: str, pack: PackModel) -> ManifestModel:
        prompt = build_claim_prompt(answer)
        payload = await self._client.complete_json(prompt, ATOM_MANIFEST_SCHEMA)
        return self._validate_manifest(payload, pack)

    def _validate_manifest(self, payload: dict, pack: PackModel) -> ManifestModel:
        try:
            manifest = ManifestModel.model_validate(payload)
        except ValidationError as exc:
            raise exc
        aliases = pack.ontology.aliases
        canonical_atoms = [canonicalize_atom(atom, aliases) for atom in manifest.atoms]
        return ManifestModel(atoms=sort_atoms(canonical_atoms))
