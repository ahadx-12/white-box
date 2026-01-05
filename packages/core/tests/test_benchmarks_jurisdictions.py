from __future__ import annotations

import json
from pathlib import Path

from trustai_core.benchmarks.models import BenchmarkCase
from trustai_core.benchmarks.runner import run_benchmark_suite


def _case_payload(case_id: str, pack_id: str) -> dict:
    return {
        "id": case_id,
        "pack_id": pack_id,
        "case_type": "positive",
        "difficulty": "easy",
        "input": {"input": "Sample input", "options": {"max_iters": 2}},
        "expected": {
            "preferred_hts": ["6402.99"],
            "allowed_hts": ["6404.11.90"],
            "must_not_hts": [],
            "expected_accept": True,
            "expected_refusal_category": None,
            "no_savings_expected": False,
            "duty_delta_range": None,
            "expected_duty_total_rate_pct": None,
            "expected_duty_delta_direction": None,
            "lever_found_expected": None,
            "lever_count_min": None,
            "lever_compliance_ok": None,
            "expected_best_is_multi_step": None,
            "min_lever_steps": None,
        },
        "notes": {"source": "synthetic", "tags": ["chapter_64"]},
    }


def test_benchmark_runner_jurisdictions(tmp_path: Path) -> None:
    case_us = _case_payload("case_us", "tariff_us")
    case_ca = _case_payload("case_ca", "tariff_ca")
    for case in (case_us, case_ca):
        BenchmarkCase.model_validate(case)

    suite_path_us = tmp_path / "cases_us"
    suite_path_ca = tmp_path / "cases_ca"
    suite_path_us.mkdir()
    suite_path_ca.mkdir()
    (suite_path_us / "case_us.json").write_text(json.dumps(case_us), encoding="utf-8")
    (suite_path_ca / "case_ca.json").write_text(json.dumps(case_ca), encoding="utf-8")

    fixture_us = Path("storage/benchmarks/tariff_us/fixtures/fixture_positive.json")
    fixture_ca = Path("storage/benchmarks/tariff_ca/fixtures/fixture_positive.json")

    def fixture_resolver(case):
        return fixture_us if case.pack_id == "tariff_us" else fixture_ca

    report_us = run_benchmark_suite(
        "tariff_us",
        suite_path_us,
        mode="fixture",
        fixture_resolver=fixture_resolver,
    )
    report_ca = run_benchmark_suite(
        "tariff_ca",
        suite_path_ca,
        mode="fixture",
        fixture_resolver=fixture_resolver,
    )
    assert report_us.summary.total_cases == 1
    assert report_ca.summary.total_cases == 1
