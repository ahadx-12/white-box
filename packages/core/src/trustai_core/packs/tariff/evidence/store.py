from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import orjson

from trustai_core.packs.tariff.evidence.models import EvidenceSource


class TariffEvidenceStore:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or _default_evidence_root()

    def list_sources(self) -> list[EvidenceSource]:
        return list(_load_sources(self._root))

    def get_source(self, source_id: str) -> EvidenceSource | None:
        for source in _load_sources(self._root):
            if source.source_id == source_id:
                return source
        return None


def _default_evidence_root() -> Path:
    root = Path(os.getenv("TRUSTAI_PACKS_ROOT", "storage/packs"))
    return root / "tariff" / "evidence" / "sources"


@lru_cache(maxsize=4)
def _load_sources(root: Path) -> tuple[EvidenceSource, ...]:
    if not root.exists():
        return tuple()
    sources: list[EvidenceSource] = []
    for file_path in sorted(root.glob("*.json")):
        payload = orjson.loads(file_path.read_bytes())
        if isinstance(payload, dict):
            payload = [payload]
        for entry in payload:
            sources.append(EvidenceSource.model_validate(entry))
    sources.sort(key=lambda item: item.source_id)
    return tuple(sources)
