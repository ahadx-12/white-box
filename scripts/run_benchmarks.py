#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import orjson

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "packages" / "core" / "src"))

from trustai_core.benchmarks.runner import run_benchmark_suite


def _format_markdown(report) -> str:
    summary = report.summary
    lines = [
        "# Benchmark Report",
        "",
        f"Suite: {report.suite}",
        f"Mode: {report.mode}",
        f"Started: {report.started_at}",
        f"Completed: {report.completed_at}",
        "",
        "## Summary",
        f"- Total cases: {summary.total_cases}",
        f"- Passed: {summary.passed_cases}",
        f"- Failed: {summary.failed_cases}",
        f"- Average score: {summary.average_score}",
        f"- Pass rate: {summary.pass_rate}",
        "",
        "## Case Results",
        "| Case | Type | Score | Passed | HTS | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for result in report.case_results:
        case = result.case
        score = result.score
        notes = ", ".join(score.penalties) if score.penalties else ""
        lines.append(
            f"| {case.id} | {case.case_type} | {score.score} | {score.passed} | "
            f"{score.final_hts or ''} | {notes} |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TrustAI benchmark suites.")
    parser.add_argument("--suite", required=True, help="Benchmark suite name (e.g., tariff)")
    parser.add_argument(
        "--path",
        default="storage/benchmarks/tariff/cases",
        help="Path to benchmark cases",
    )
    parser.add_argument(
        "--mode",
        default="fixture",
        choices=["fixture", "live"],
        help="Runner mode (fixture or live)",
    )
    args = parser.parse_args()

    case_path = Path(args.path)
    report = run_benchmark_suite(args.suite, case_path, mode=args.mode)

    reports_dir = Path("reports/benchmarks")
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = report.completed_at.replace(":", "").replace("-", "")
    json_path = reports_dir / f"{args.suite}_benchmark_{timestamp}.json"
    md_path = reports_dir / f"{args.suite}_benchmark_{timestamp}.md"

    json_path.write_bytes(
        orjson.dumps(report.model_dump(), option=orjson.OPT_SORT_KEYS)
    )
    markdown = _format_markdown(report)
    md_path.write_text(markdown, encoding="utf-8")

    summary = report.summary
    worst_failures = [
        result for result in report.case_results if not result.score.passed
    ]
    worst_failures.sort(key=lambda item: item.score.score)
    print(f"Suite {args.suite} ({args.mode})")
    print(
        f"Passed {summary.passed_cases}/{summary.total_cases} "
        f"avg score={summary.average_score}"
    )
    if worst_failures:
        print("Worst failures:")
        for result in worst_failures[:5]:
            print(
                f"- {result.case.id}: score={result.score.score} penalties={result.score.penalties}"
            )
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")


if __name__ == "__main__":
    main()
