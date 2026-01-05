from __future__ import annotations

from pathlib import Path

import json

from trustai_core.benchmarks.models import BenchmarkCase, CaseResult
from trustai_core.benchmarks.runner import run_benchmark_suite
from trustai_core.benchmarks.scoring import score_case


def _sample_case_payload(case_id: str) -> dict:
    return {
        "id": case_id,
        "pack_id": "tariff",
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


def _fake_result(
    hts_code: str,
    accepted: bool = True,
    rejected_because: list[str] | None = None,
    lever_count: int = 0,
    lever_compliance_ok: bool = True,
    lever_steps: int = 1,
) -> dict:
    rejected = rejected_because or ([] if accepted else ["hts_or_questions_missing"])
    return {
        "status": "verified" if accepted else "failed",
        "iterations": [
            {
                "i": 1,
                "accepted": accepted,
                "rejected_because": [] if accepted else rejected,
                "sequence_violations": [],
                "citation_gate_result": {"ok": True, "violations": []},
            }
        ],
        "citation_gate_result": {"ok": True, "violations": []},
        "citations": [
            {
                "claim_type": "hts_classification",
                "claim": "HTS classification",
                "source_id": "HTS.6404",
                "quote": "Footwear with outer soles",
            }
        ],
        "tariff_dossier": {
            "baseline": {
                "hts_code": "6404.11.90",
                "duty_rate_pct": 20.0,
                "duty_breakdown": {"total_rate_pct": 20.0},
            },
            "optimized": {
                "hts_code": hts_code,
                "duty_rate_pct": 5.0,
                "duty_breakdown": {"total_rate_pct": 5.0},
                "rationale": "ok",
            },
            "mutations": [],
            "what_if_candidates": [],
            "gri_trace": {"sequence_ok": True, "steps": []},
        },
        "lever_proof": {
            "baseline_summary": {},
            "mutation_candidates": [],
            "selected_levers": [
                {
                    "sequence": [
                        {"operator_id": f"op_{idx}", "label": "test", "category": "material", "diff": []}
                        for _ in range(lever_steps)
                    ],
                    "gate_results": {"plausibility": [{"ok": lever_compliance_ok} for _ in range(lever_steps)]},
                }
                for idx in range(lever_count)
            ],
        },
    }


def test_case_schema_parsing() -> None:
    payload = _sample_case_payload("case_schema")
    case = BenchmarkCase.model_validate(payload)
    assert case.id == "case_schema"
    assert case.expected.preferred_hts == ["6402.99"]


def test_scoring_logic_partial_credit() -> None:
    payload = _sample_case_payload("case_scoring")
    case = BenchmarkCase.model_validate(payload)
    result = _fake_result("6402.99", accepted=True)
    score = score_case(case, result)
    assert score.passed
    assert score.match_level == "preferred"

    result_allowed = _fake_result("6404.11.90", accepted=True)
    score_allowed = score_case(case, result_allowed)
    assert score_allowed.score < score.score
    assert score_allowed.match_level == "allowed"


def test_runner_report_structure(tmp_path: Path) -> None:
    case_a = _sample_case_payload("case_a")
    case_b = _sample_case_payload("case_b")
    case_b["expected"]["expected_accept"] = False
    case_b["case_type"] = "negative"
    (tmp_path / "cases").mkdir()
    (tmp_path / "cases" / "case_a.json").write_text(json.dumps(case_a), encoding="utf-8")
    (tmp_path / "cases" / "case_b.json").write_text(json.dumps(case_b), encoding="utf-8")

    async def _executor(case, mode, fixture_resolver):
        accepted = case.expected.expected_accept
        result = _fake_result(case.expected.preferred_hts[0], accepted=accepted)
        return CaseResult(
            case=case,
            score=score_case(case, result),
            output_summary={"status": result["status"]},
        )

    report = run_benchmark_suite(
        "tariff",
        tmp_path / "cases",
        mode="fixture",
        executor=_executor,
    )
    payload = report.model_dump()
    assert payload["schema_version"] == "v1"
    assert payload["summary"]["total_cases"] == 2


def test_missing_evidence_refusal_scoring() -> None:
    payload = _sample_case_payload("case_missing_evidence")
    payload["expected"]["expected_accept"] = False
    payload["expected"]["expected_refusal_category"] = "missing_evidence"
    payload["case_type"] = "negative"
    case = BenchmarkCase.model_validate(payload)
    result = _fake_result("8504.10", accepted=False, rejected_because=["missing_evidence"])
    score = score_case(case, result)
    assert score.passed
    assert score.refusal_category_actual == "missing_evidence"


def test_lever_expectation_scoring() -> None:
    payload = _sample_case_payload("case_levers")
    payload["expected"]["lever_found_expected"] = True
    payload["expected"]["lever_count_min"] = 1
    payload["expected"]["lever_compliance_ok"] = True
    case = BenchmarkCase.model_validate(payload)
    result = _fake_result("6402.99", accepted=True, lever_count=1, lever_compliance_ok=True)
    score = score_case(case, result)
    assert score.passed
    assert score.lever_count == 1


def test_multi_step_expectation_scoring() -> None:
    payload = _sample_case_payload("case_multi_step")
    payload["expected"]["lever_found_expected"] = True
    payload["expected"]["expected_best_is_multi_step"] = True
    payload["expected"]["min_lever_steps"] = 2
    case = BenchmarkCase.model_validate(payload)
    result = _fake_result("6402.99", accepted=True, lever_count=1, lever_steps=2)
    score = score_case(case, result)
    assert score.passed
