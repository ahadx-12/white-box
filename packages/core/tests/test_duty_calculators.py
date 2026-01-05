from __future__ import annotations

from trustai_core.duty.models import DutyFlow
from trustai_core.packs.tariff_ca.duty.calculator import CADutyCalculator
from trustai_core.packs.tariff_us.duty.calculator import USDutyCalculator


def test_us_duty_calculator_base_rate_lookup() -> None:
    calculator = USDutyCalculator()
    flow = DutyFlow(importing_country="US", exporting_country="CN", origin_country="CN")
    breakdown = calculator.calculate("8544.11", flow)
    assert breakdown.base_rate_pct == 2.6
    assert breakdown.total_rate_pct == 2.6
    assert isinstance(breakdown.additional_duties, list)


def test_ca_duty_calculator_base_rate_lookup() -> None:
    calculator = CADutyCalculator()
    flow = DutyFlow(importing_country="CA", exporting_country="CN", origin_country="CN")
    breakdown = calculator.calculate("8544.11", flow)
    assert breakdown.base_rate_pct == 0.0
    assert breakdown.total_rate_pct == 0.0
    assert isinstance(breakdown.surtaxes, list)


def test_duty_calculators_deterministic() -> None:
    us_calc = USDutyCalculator()
    ca_calc = CADutyCalculator()
    flow_us = DutyFlow(importing_country="US")
    flow_ca = DutyFlow(importing_country="CA")
    first = us_calc.calculate("6402.99", flow_us)
    second = us_calc.calculate("6402.99", flow_us)
    assert first.model_dump() == second.model_dump()
    first_ca = ca_calc.calculate("6402.99", flow_ca)
    second_ca = ca_calc.calculate("6402.99", flow_ca)
    assert first_ca.model_dump() == second_ca.model_dump()
