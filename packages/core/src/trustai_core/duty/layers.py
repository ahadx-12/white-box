from __future__ import annotations

from datetime import date
from pathlib import Path

import orjson
from pydantic import BaseModel, ConfigDict, Field

from trustai_core.duty.models import AppliedDutyLayer


class DutyLayerMatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    origin_countries: list[str] = Field(default_factory=list)
    line_prefixes: list[str] = Field(default_factory=list)


class DutyLayerRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    layer_id: str
    type: str
    pct: float
    match: DutyLayerMatch
    effective_from: str
    effective_to: str | None
    reason: str
    source_id: str | None = None


def load_layer_rules(path: Path) -> list[DutyLayerRule]:
    if not path.exists():
        return []
    payload = orjson.loads(path.read_bytes())
    if not isinstance(payload, list):
        return []
    return [DutyLayerRule.model_validate(entry) for entry in payload]


def evaluate_layer_rules(
    rules: list[DutyLayerRule],
    origin_country: str | None,
    line_id: str | None,
    effective_date: date,
) -> list[AppliedDutyLayer]:
    if not origin_country or not line_id:
        return []
    normalized_line = _normalize_code(line_id)
    applied: list[AppliedDutyLayer] = []
    for rule in rules:
        if origin_country not in rule.match.origin_countries:
            continue
        if not _matches_prefix(normalized_line, rule.match.line_prefixes):
            continue
        if not _date_in_range(effective_date, rule.effective_from, rule.effective_to):
            continue
        applied.append(
            AppliedDutyLayer(
                layer_id=rule.layer_id,
                pct=float(rule.pct),
                reason=rule.reason,
                effective_from=rule.effective_from,
                effective_to=rule.effective_to,
            )
        )
    return applied


def parse_effective_date(value: str | None, *, fallback: date) -> date:
    if not value:
        return fallback
    return date.fromisoformat(value)


def _matches_prefix(line_id: str, prefixes: list[str]) -> bool:
    for prefix in prefixes:
        if line_id.startswith(_normalize_code(prefix)):
            return True
    return False


def _normalize_code(value: str) -> str:
    return value.replace(".", "").strip()


def _date_in_range(effective: date, start: str, end: str | None) -> bool:
    start_date = date.fromisoformat(start)
    if effective < start_date:
        return False
    if end:
        end_date = date.fromisoformat(end)
        if effective > end_date:
            return False
    return True
