from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import orjson

from trustai_core.duty.models import AdditionalDuty, DutyBreakdown, DutyFlow


class CADutyCalculator:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or _default_rates_root()
        self._base_rates = _load_rates(self._root / "base_rates.json")
        self._surtaxes = _load_rates(self._root / "surtaxes.json")

    def calculate(
        self,
        line_id: str,
        flow: DutyFlow,
        preference_program: str | None = None,
    ) -> DutyBreakdown:
        entry = self._base_rates.get(line_id)
        assumptions: list[str] = []
        if not entry:
            return DutyBreakdown(
                base_rate_pct=0.0,
                preferential_rate_pct=None,
                additional_duties=[],
                surtaxes=[],
                total_rate_pct=0.0,
                assumptions=["Rate not found in CA base rate table."],
            )
        base_rate = float(entry.get("mfn_rate_pct", entry.get("base_rate_pct", 0.0)))
        preferential_rate = None
        if preference_program:
            preferential_rate = _resolve_preference_rate(entry, preference_program)
            if preferential_rate is None:
                assumptions.append("Preference program not applied.")
        surtaxes = _build_surtaxes(self._surtaxes.get(line_id))
        total = base_rate + sum(item.rate_pct for item in surtaxes)
        return DutyBreakdown(
            base_rate_pct=base_rate,
            preferential_rate_pct=preferential_rate,
            additional_duties=[],
            surtaxes=surtaxes,
            total_rate_pct=round(total, 4),
            assumptions=assumptions,
        )


def _default_rates_root() -> Path:
    root = Path(os.getenv("TRUSTAI_PACKS_ROOT", "storage/packs"))
    return root / "tariff_ca" / "rates"


def _load_rates(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = orjson.loads(path.read_bytes())
    if not isinstance(payload, dict):
        return {}
    return payload


def _resolve_preference_rate(entry: dict[str, Any], preference_program: str) -> float | None:
    rates = entry.get("treatment_rates") or entry.get("preference_rates") or {}
    value = rates.get(preference_program)
    if value is None:
        return None
    return float(value)


def _build_surtaxes(payload: Any) -> list[AdditionalDuty]:
    if not payload:
        return []
    surtaxes: list[AdditionalDuty] = []
    for entry in payload:
        surtaxes.append(
            AdditionalDuty(
                code=entry.get("code", "SUR"),
                description=entry.get("description"),
                rate_pct=float(entry.get("rate_pct", 0.0)),
            )
        )
    return surtaxes
