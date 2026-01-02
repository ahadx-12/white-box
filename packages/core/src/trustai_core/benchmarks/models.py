from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CaseType = Literal["positive", "negative", "adversarial", "no_savings"]
Difficulty = Literal["easy", "medium", "hard", "expert"]
RefusalCategory = Literal["insufficient_info", "ambiguous", "out_of_scope"]


class ExpectedSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    preferred_hts: list[str]
    allowed_hts: list[str] | None = None
    must_not_hts: list[str] | None = None
    expected_accept: bool
    expected_refusal_category: RefusalCategory | None = None
    no_savings_expected: bool = False
    duty_delta_range: tuple[float, float] | None = None


class NotesSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    tags: list[str] = Field(default_factory=list)


class BenchmarkCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    pack_id: str
    case_type: CaseType
    difficulty: Difficulty
    input: dict[str, Any]
    expected: ExpectedSpec
    notes: NotesSpec


class CaseScore(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str
    score: float
    passed: bool
    expected_accept: bool
    actual_accept: bool
    match_level: str | None = None
    final_hts: str | None = None
    refusal_category_expected: RefusalCategory | None = None
    refusal_category_actual: RefusalCategory | None = None
    duty_delta: float | None = None
    no_savings_ok: bool | None = None
    process_bonus: float = 0.0
    penalties: list[str] = Field(default_factory=list)
    citations_present: bool | None = None
    citations_valid: bool | None = None


class CaseResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    case: BenchmarkCase
    score: CaseScore
    output_summary: dict[str, Any] = Field(default_factory=dict)


class RunSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_cases: int
    passed_cases: int
    failed_cases: int
    average_score: float
    pass_rate: float


class BenchmarkRunResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "v1"
    suite: str
    pack_id: str
    mode: str
    started_at: str
    completed_at: str
    case_results: list[CaseResult]
    summary: RunSummary
