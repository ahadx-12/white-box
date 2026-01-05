from __future__ import annotations

from trustai_core.packs.tariff_ca.duty.layers import CADutyLayers
from trustai_core.packs.tariff_us.duty.layers import USDutyLayers


def test_us_additional_duty_layer_applies_for_cn_ch73() -> None:
    layers = USDutyLayers()
    applied = layers.evaluate("CN", "7318.15", "2024-06-01")
    assert [layer.layer_id for layer in applied] == ["US.301.CN.V1"]


def test_us_additional_duty_layer_outside_date_range() -> None:
    layers = USDutyLayers()
    applied = layers.evaluate("FR", "8413.70", "2024-06-01")
    assert applied == []


def test_ca_surtax_layer_applies_for_cn_ch73() -> None:
    layers = CADutyLayers()
    applied = layers.evaluate("CN", "7318.15", "2024-06-01")
    assert [layer.layer_id for layer in applied] == ["CA.SURTAX.CN.V1"]


def test_ca_surtax_layer_outside_date_range() -> None:
    layers = CADutyLayers()
    applied = layers.evaluate("US", "8413.70", "2024-06-01")
    assert applied == []
