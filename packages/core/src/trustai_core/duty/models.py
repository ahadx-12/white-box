from __future__ import annotations

from typing import Literal

from trustai_core.duty.programs import ProgramResult

from pydantic import BaseModel, ConfigDict, Field


class DutyFlow(BaseModel):
    model_config = ConfigDict(frozen=True)

    importing_country: Literal["US", "CA"] | None = None
    exporting_country: str | None = None
    origin_country: str | None = None
    origin_method: str | None = None
    preference_program: str | None = None
    effective_date: str | None = None
    bom: dict | None = None
    manufacturing: dict | None = None


class DutyLineRate(BaseModel):
    model_config = ConfigDict(frozen=True)

    line_id: str
    base_rate_pct: float
    preferential_rate_pct: float | None = None


class AppliedDutyLayer(BaseModel):
    model_config = ConfigDict(frozen=True)

    layer_id: str
    pct: float
    reason: str
    effective_from: str
    effective_to: str | None = None


class DutyBreakdown(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_rate_pct: float
    preferential_rate_pct: float | None = None
    applied_additional_duties: list[AppliedDutyLayer] = Field(default_factory=list)
    applied_surtaxes: list[AppliedDutyLayer] = Field(default_factory=list)
    applied_layer_ids: list[str] = Field(default_factory=list)
    program_result: ProgramResult | None = None
    total_rate_pct: float
    assumptions: list[str] = Field(default_factory=list)
    effective_date: str | None = None
