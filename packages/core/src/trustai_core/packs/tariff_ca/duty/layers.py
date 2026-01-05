from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from trustai_core.duty.layers import evaluate_layer_rules, load_layer_rules, parse_effective_date
from trustai_core.duty.models import AppliedDutyLayer


class CADutyLayers:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or _default_rates_root()
        self._rules = load_layer_rules(self._root / "surtaxes.json")

    def evaluate(
        self,
        origin_country: str | None,
        line_id: str | None,
        effective_date: str | None,
    ) -> list[AppliedDutyLayer]:
        resolved = parse_effective_date(effective_date, fallback=date.today())
        return evaluate_layer_rules(self._rules, origin_country, line_id, resolved)


def _default_rates_root() -> Path:
    root = Path(os.getenv("TRUSTAI_PACKS_ROOT", "storage/packs"))
    return root / "tariff_ca" / "rates"
