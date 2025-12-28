from __future__ import annotations

import time

from pydantic import ValidationError

from trustai_core.agents.prompts import (
    ATOM_MANIFEST_SCHEMA,
    build_claim_prompt,
    build_evidence_prompt,
)
from trustai_core.llm.base import LLMClient
from trustai_core.packs.types import PackModel
from trustai_core.schemas.atoms import AtomModel, ManifestModel
from trustai_core.utils.canonicalize import canonicalize_atom, sort_atoms
from trustai_core.utils.hashing import sha256_canonical_json


class Perceiver:
    def __init__(self, client: LLMClient) -> None:
        self._client = client
        self._debug_calls: list[dict[str, object]] = []

    async def extract_evidence_atoms(self, text: str, pack: PackModel) -> ManifestModel:
        prompt = build_evidence_prompt(text)
        payload = await self._call_with_debug(prompt, ATOM_MANIFEST_SCHEMA, "perceiver_evidence")
        return self._validate_manifest(payload, pack)

    async def extract_claim_atoms(self, answer: str, pack: PackModel) -> ManifestModel:
        prompt = build_claim_prompt(answer)
        payload = await self._call_with_debug(prompt, ATOM_MANIFEST_SCHEMA, "perceiver_claim")
        return self._validate_manifest(payload, pack)

    def reset_debug(self) -> None:
        self._debug_calls = []

    def get_debug_calls(self) -> list[dict[str, object]]:
        return list(self._debug_calls)

    def _validate_manifest(self, payload: dict, pack: PackModel) -> ManifestModel:
        try:
            manifest = ManifestModel.model_validate(payload)
        except ValidationError as exc:
            raise exc
        aliases = pack.ontology.aliases
        canonical_atoms = [canonicalize_atom(atom, aliases) for atom in manifest.atoms]
        deduped = self._dedupe_atoms(canonical_atoms)
        return ManifestModel(atoms=sort_atoms(deduped))

    async def _call_with_debug(self, prompt: str, schema: dict, role: str) -> dict:
        start = time.monotonic()
        payload = await self._client.complete_json(prompt, schema)
        elapsed = time.monotonic() - start
        self._debug_calls.append(
            {
                "role": role,
                "prompt_hash": sha256_canonical_json(prompt),
                "prompt_tokens_estimate": len(prompt.split()),
                "latency_bucket": self._latency_bucket(elapsed),
                "model_id": _model_id(self._client),
            }
        )
        return payload

    def _dedupe_atoms(self, atoms: list[AtomModel]) -> list[AtomModel]:
        best_by_key: dict[tuple[str, str, str, bool], AtomModel] = {}
        for atom in atoms:
            key = atom.sort_key()
            existing = best_by_key.get(key)
            if existing is None or atom.confidence > existing.confidence:
                best_by_key[key] = atom
        return list(best_by_key.values())

    @staticmethod
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
