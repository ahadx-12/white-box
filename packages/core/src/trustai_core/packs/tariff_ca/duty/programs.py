from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import orjson

from trustai_core.duty.programs import ProgramResult, evaluate_program_rules, load_program_rules


class CAPreferencePrograms:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or _default_rates_root()
        self._rules = load_program_rules(self._root / "program_rules_cusma.json")
        self._preference_rates = _load_preference_rates(
            self._root / "preferential_rates.json"
        )

    def evaluate(self, program_id: str, context: dict[str, Any]) -> ProgramResult | None:
        if program_id not in {"CUSMA"}:
            return None
        return evaluate_program_rules(program_id, self._rules, context)

    def resolve_preferential_rate(self, program_id: str, line_id: str) -> float | None:
        rates = self._preference_rates.get(program_id)
        if not rates:
            return None
        chapter = _normalize_chapter(line_id)
        value = rates.get(chapter)
        if value is None:
            return None
        return float(value)


def _default_rates_root() -> Path:
    root = Path(os.getenv("TRUSTAI_PACKS_ROOT", "storage/packs"))
    return root / "tariff_ca" / "rates"


def _normalize_chapter(line_id: str) -> str:
    return line_id.replace(".", "")[:2]


def _load_preference_rates(path: Path) -> dict[str, dict[str, float]]:
    if not path.exists():
        return {}
    payload = orjson.loads(path.read_bytes())
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return {}
    rates: dict[str, dict[str, float]] = {}
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        program_id = entry.get("program_id")
        program_rates = entry.get("rates")
        if not program_id or not isinstance(program_rates, dict):
            continue
        rates[program_id] = {
            chapter: float(rate) for chapter, rate in program_rates.items()
        }
    return rates
