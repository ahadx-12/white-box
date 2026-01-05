from __future__ import annotations

import asyncio
import os
from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import orjson

from trustai_core.benchmarks.models import BenchmarkCase, BenchmarkRunResult, CaseResult, RunSummary
from trustai_core.benchmarks.scoring import score_case
from trustai_core.llm.anthropic_client import AnthropicClient
from trustai_core.llm.openai_client import OpenAIClient
from trustai_core.packs.registry import PackContext, get_pack_runner

FixtureResolver = Callable[[BenchmarkCase], Path | None]


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_cases_from_path(path: Path) -> list[BenchmarkCase]:
    cases: list[BenchmarkCase] = []
    for file_path in sorted(path.rglob("*.json")):
        payload = orjson.loads(file_path.read_bytes())
        cases.append(BenchmarkCase.model_validate(payload))
    return sorted(cases, key=lambda item: item.id)


def _default_fixture_resolver(case: BenchmarkCase) -> Path | None:
    root = Path("storage/benchmarks")
    suite = case.pack_id
    if case.expected.expected_refusal_category == "missing_evidence":
        fixture_path = root / suite / "fixtures" / "fixture_missing_evidence.json"
        if fixture_path.exists():
            return fixture_path
    if case.case_type == "no_savings":
        fixture_path = root / suite / "fixtures" / "fixture_no_savings.json"
        if fixture_path.exists():
            return fixture_path
    fixture_map = {
        "positive": "fixture_positive.json",
        "negative": "fixture_negative.json",
        "adversarial": "fixture_positive.json",
        "no_savings": "fixture_no_savings.json",
        "savings_possible": "fixture_positive.json",
    }
    tag_map = {
        "chapter_64": "fixture_positive.json",
        "chapter_73": "fixture_ch73.json",
        "chapter_84": "fixture_ch84.json",
        "chapter_85": "fixture_ch85.json",
    }
    for tag in case.notes.tags:
        fixture_name = tag_map.get(tag)
        if fixture_name:
            fixture_path = root / suite / "fixtures" / fixture_name
            if fixture_path.exists():
                return fixture_path
    fixture_name = fixture_map.get(case.case_type)
    if not fixture_name:
        return None
    fixture_path = root / suite / "fixtures" / fixture_name
    if fixture_path.exists():
        return fixture_path
    return None


async def _run_case(
    case: BenchmarkCase,
    mode: str,
    fixture_resolver: FixtureResolver,
) -> CaseResult:
    if mode == "fixture":
        os.environ["TRUSTAI_LLM_MODE"] = "fixture"
        fixture_path = fixture_resolver(case)
        if fixture_path:
            os.environ["TRUSTAI_TARIFF_FIXTURE"] = str(fixture_path)
    else:
        os.environ["TRUSTAI_LLM_MODE"] = "live"
        os.environ.pop("TRUSTAI_TARIFF_FIXTURE", None)

    pack_runner = get_pack_runner(
        case.pack_id,
        PackContext(
            llm_mode=mode,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            claude_model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
            openai_client_factory=lambda: OpenAIClient(
                model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
            ),
            anthropic_client_factory=lambda: AnthropicClient(
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
            ),
        ),
    )
    if not pack_runner:
        raise RuntimeError(f"Pack not found: {case.pack_id}")

    input_payload = case.input
    input_text = input_payload.get("input", "")
    options = input_payload.get("options")
    evidence = input_payload.get("evidence")
    if evidence:
        options = dict(options or {})
        options["evidence"] = evidence
    result = await pack_runner.run(input_text, options)
    case_score = score_case(case, result)
    summary = {
        "status": getattr(result, "status", None),
        "final_hts": case_score.final_hts,
        "accepted": case_score.actual_accept,
    }
    return CaseResult(case=case, score=case_score, output_summary=summary)


def _summarize_results(results: Iterable[CaseResult]) -> RunSummary:
    results_list = list(results)
    total = len(results_list)
    passed = sum(1 for item in results_list if item.score.passed)
    failed = total - passed
    average = sum(item.score.score for item in results_list) / total if total else 0.0
    pass_rate = passed / total if total else 0.0
    return RunSummary(
        total_cases=total,
        passed_cases=passed,
        failed_cases=failed,
        average_score=round(average, 4),
        pass_rate=round(pass_rate, 4),
    )


def run_benchmark_suite(
    suite: str,
    path: Path,
    mode: str = "fixture",
    fixture_resolver: FixtureResolver | None = None,
    executor: Callable[[BenchmarkCase, str, FixtureResolver], Any] | None = None,
) -> BenchmarkRunResult:
    if mode not in {"fixture", "live"}:
        raise ValueError("Mode must be fixture or live.")
    cases = _load_cases_from_path(path)
    fixture_resolver = fixture_resolver or _default_fixture_resolver
    executor = executor or _run_case
    started_at = _timestamp()
    results: list[CaseResult] = []
    for case in cases:
        result = asyncio.run(executor(case, mode, fixture_resolver))
        results.append(result)
    completed_at = _timestamp()
    summary = _summarize_results(results)
    return BenchmarkRunResult(
        suite=suite,
        pack_id=suite,
        mode=mode,
        started_at=started_at,
        completed_at=completed_at,
        case_results=results,
        summary=summary,
    )
