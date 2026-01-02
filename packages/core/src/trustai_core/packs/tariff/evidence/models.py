from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class EvidenceSource(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    source_type: str
    title: str
    effective_date: str
    url: str | None = None
    text: str
