from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any

import orjson

from trustai_core.duty.layers import parse_effective_date
from trustai_core.duty.models import DutyBreakdown, DutyFlow
from trustai_core.packs.tariff_us.duty.layers import USDutyLayers
from trustai_core.packs.tariff_us.duty.programs import USPreferencePrograms


class USDutyCalculator:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or _default_rates_root()
        self._base_rates = _load_rates(self._root / "base_rates.json")
        self._layers = USDutyLayers(self._root)
        self._programs = USPreferencePrograms(self._root)

    def calculate(
        self,
        line_id: str,
        flow: DutyFlow,
        preference_program: str | None = None,
    ) -> DutyBreakdown:
        effective_date = parse_effective_date(flow.effective_date, fallback=date.today())
        effective_date_str = effective_date.isoformat()
        entry = self._base_rates.get(line_id)
        assumptions: list[str] = []
        if not entry:
            return DutyBreakdown(
                base_rate_pct=0.0,
                preferential_rate_pct=None,
                applied_additional_duties=[],
                applied_surtaxes=[],
                applied_layer_ids=[],
                program_result=None,
                total_rate_pct=0.0,
                assumptions=["Rate not found in US base rate table."],
                effective_date=effective_date_str,
            )
        base_rate = float(entry.get("base_rate_pct", 0.0))
        preference_program = preference_program or flow.preference_program
        preferential_rate = None
        program_result = None
        if preference_program:
            program_result = self._programs.evaluate(
                preference_program,
                _build_program_context(flow, line_id),
            )
            if program_result and program_result.status == "eligible":
                preferential_rate = self._programs.resolve_preferential_rate(
                    program_result.program_id,
                    line_id,
                )
                if preferential_rate is None:
                    assumptions.append(
                        "Preference program eligible but no preferential rate found."
                    )
            elif program_result:
                assumptions.append(f"Preference not applied: {program_result.reason}")
        applied_additional = self._layers.evaluate(
            flow.origin_country,
            line_id,
            effective_date_str,
        )
        base_for_total = preferential_rate if preferential_rate is not None else base_rate
        total = base_for_total + sum(item.pct for item in applied_additional)
        applied_layer_ids = [item.layer_id for item in applied_additional]
        return DutyBreakdown(
            base_rate_pct=base_rate,
            preferential_rate_pct=preferential_rate,
            applied_additional_duties=applied_additional,
            applied_surtaxes=[],
            applied_layer_ids=applied_layer_ids,
            program_result=program_result,
            total_rate_pct=round(total, 4),
            assumptions=assumptions,
            effective_date=effective_date_str,
        )


def _default_rates_root() -> Path:
    root = Path(os.getenv("TRUSTAI_PACKS_ROOT", "storage/packs"))
    return root / "tariff_us" / "rates"


def _load_rates(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = orjson.loads(path.read_bytes())
    if not isinstance(payload, dict):
        return {}
    return payload


def _build_program_context(flow: DutyFlow, line_id: str) -> dict[str, Any]:
    return {
        "origin_country": flow.origin_country,
        "origin_method": flow.origin_method,
        "line_id": line_id,
        "bom": flow.bom,
        "manufacturing": flow.manufacturing,
    }
