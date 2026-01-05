from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DutyFlow(BaseModel):
    model_config = ConfigDict(frozen=True)

    importing_country: Literal["US", "CA"] | None = None
    exporting_country: str | None = None
    origin_country: str | None = None
    origin_method: str | None = None
    preference_program: str | None = None


class DutyLineRate(BaseModel):
    model_config = ConfigDict(frozen=True)

    line_id: str
    base_rate_pct: float
    preferential_rate_pct: float | None = None


class AdditionalDuty(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    description: str | None = None
    rate_pct: float


class DutyBreakdown(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_rate_pct: float
    preferential_rate_pct: float | None = None
    additional_duties: list[AdditionalDuty] = Field(default_factory=list)
    surtaxes: list[AdditionalDuty] = Field(default_factory=list)
    total_rate_pct: float
    assumptions: list[str] = Field(default_factory=list)
