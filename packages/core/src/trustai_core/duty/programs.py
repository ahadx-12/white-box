from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Protocol

import orjson
from pydantic import BaseModel, ConfigDict, Field


class ProgramResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["eligible", "ineligible", "unknown"]
    program_id: str
    reason: str
    missing_inputs: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class ProgramRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_id: str
    program_id: str
    type: Literal["wholly_obtained", "tariff_shift"]
    requires: list[str]
    logic: dict[str, Any]
    reason: str
    source_id: str | None = None


class ProgramEvaluator(Protocol):
    def evaluate(
        self,
        program_id: str,
        context: dict[str, Any],
    ) -> ProgramResult | None:
        ...


def load_program_rules(path: Path) -> list[ProgramRule]:
    if not path.exists():
        return []
    payload = orjson.loads(path.read_bytes())
    if not isinstance(payload, list):
        return []
    return [ProgramRule.model_validate(entry) for entry in payload]


def evaluate_program_rules(
    program_id: str,
    rules: list[ProgramRule],
    context: dict[str, Any],
) -> ProgramResult:
    missing_inputs: set[str] = set()
    evaluated_any = False
    for rule in rules:
        if rule.program_id != program_id:
            continue
        missing = _missing_required(rule.requires, context)
        if missing:
            missing_inputs.update(missing)
            continue
        evaluated_any = True
        if _evaluate_rule(rule, context):
            return ProgramResult(
                status="eligible",
                program_id=program_id,
                reason=rule.reason,
                missing_inputs=[],
                evidence=[rule.rule_id],
            )
    if missing_inputs and not evaluated_any:
        return ProgramResult(
            status="unknown",
            program_id=program_id,
            reason="Missing inputs for preference program evaluation.",
            missing_inputs=sorted(missing_inputs),
            evidence=[],
        )
    if missing_inputs:
        return ProgramResult(
            status="unknown",
            program_id=program_id,
            reason="Missing inputs for preference program evaluation.",
            missing_inputs=sorted(missing_inputs),
            evidence=[],
        )
    return ProgramResult(
        status="ineligible",
        program_id=program_id,
        reason="No preference rules satisfied.",
        missing_inputs=[],
        evidence=[],
    )


def _missing_required(requires: list[str], context: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for requirement in requires:
        if requirement == "origin_country":
            if not context.get("origin_country") and not context.get("origin_method"):
                missing.append("origin_country")
        elif requirement == "bom.components[*].hs_chapter":
            components = _extract_components(context.get("bom"))
            if not components:
                missing.append(requirement)
            else:
                if any(not comp.get("hs_chapter") for comp in components):
                    missing.append(requirement)
        elif requirement == "manufacturing.steps":
            steps = _extract_steps(context.get("manufacturing"))
            if not steps:
                missing.append(requirement)
            else:
                if any(not step.get("country") for step in steps):
                    missing.append("manufacturing.steps[*].country")
        else:
            if context.get(requirement) is None:
                missing.append(requirement)
    return missing


def _evaluate_rule(rule: ProgramRule, context: dict[str, Any]) -> bool:
    if rule.type == "wholly_obtained":
        origin = context.get("origin_country")
        origin_in = set(rule.logic.get("origin_in") or [])
        return bool(origin and origin in origin_in)
    if rule.type == "tariff_shift":
        return _evaluate_tariff_shift(rule.logic, context)
    return False


def _evaluate_tariff_shift(logic: dict[str, Any], context: dict[str, Any]) -> bool:
    line_id = context.get("line_id")
    if not line_id:
        return False
    final_chapter = _normalize_chapter(line_id)
    if final_chapter not in set(logic.get("final_chapter_in") or []):
        return False
    components = _extract_components(context.get("bom"))
    if not components:
        return False
    manufacturing_steps = _extract_steps(context.get("manufacturing"))
    if not manufacturing_steps:
        return False
    if logic.get("non_originating_allowed_if") == "all_non_originating_chapters_not_equal_final":
        return all(_normalize_chapter(comp.get("hs_chapter", "")) != final_chapter for comp in components)
    return False


def _extract_components(bom: Any) -> list[dict[str, Any]]:
    if not isinstance(bom, dict):
        return []
    components = bom.get("components")
    if not isinstance(components, list):
        return []
    return [comp for comp in components if isinstance(comp, dict)]


def _extract_steps(manufacturing: Any) -> list[dict[str, Any]]:
    if not isinstance(manufacturing, dict):
        return []
    steps = manufacturing.get("steps")
    if not isinstance(steps, list):
        return []
    return [step for step in steps if isinstance(step, dict)]


def _normalize_chapter(value: str) -> str:
    normalized = value.replace(".", "")
    return normalized[:2]
