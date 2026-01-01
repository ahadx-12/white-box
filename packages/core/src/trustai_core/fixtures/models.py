from __future__ import annotations

from typing import Any

import orjson
from pydantic import BaseModel, ConfigDict, Field


class FixtureMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    pack_id: str
    pack_version: str
    ontology_hash: str
    axioms_hash: str
    model_provider: str
    model_id: str
    timestamp: str
    input_hash: str


class FinalIterationSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    iteration_index: int
    accepted: bool
    rejected_because: list[str] = Field(default_factory=list)
    critical_gates: dict[str, bool] = Field(default_factory=dict)


class GoldenInvariantsSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    accepted: bool
    final_hts_code: str | None = None
    allowed_codes: list[str] | None = None
    duty_rate_pct: float | None = None
    duty_rate_delta_pct: float | None = None
    critical_gates: dict[str, bool] = Field(default_factory=dict)
    refusal_category: str | None = None


class FixtureRecording(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    schema_version: str = "v1"
    metadata: FixtureMetadata
    request: dict[str, Any]
    result: dict[str, Any]
    proof: dict[str, Any] | None = None
    final_iteration_summary: FinalIterationSummary | None = None
    golden_invariants: GoldenInvariantsSpec
    proposals: list[dict[str, Any]] | None = None
    critics: list[dict[str, Any]] | None = None

    def to_json(self) -> bytes:
        return orjson.dumps(self.model_dump(), option=orjson.OPT_SORT_KEYS)

    @classmethod
    def from_json(cls, payload: bytes) -> "FixtureRecording":
        return cls.model_validate(orjson.loads(payload))
