from __future__ import annotations

from typing import Protocol

from trustai_core.duty.models import DutyBreakdown, DutyFlow


class DutyCalculator(Protocol):
    def calculate(
        self,
        line_id: str,
        flow: DutyFlow,
        preference_program: str | None = None,
    ) -> DutyBreakdown:
        ...
