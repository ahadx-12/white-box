from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import orjson

from trustai_core.benchmarks.models import BenchmarkRunResult


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def compare_reports(
    baseline: BenchmarkRunResult,
    current: BenchmarkRunResult,
) -> dict[str, Any]:
    baseline_cases = {result.case.id: result for result in baseline.case_results}
    current_cases = {result.case.id: result for result in current.case_results}
    improved: list[dict[str, Any]] = []
    regressed: list[dict[str, Any]] = []
    new_failures: list[dict[str, Any]] = []
    score_changes: list[float] = []

    for case_id, current_result in current_cases.items():
        baseline_result = baseline_cases.get(case_id)
        if not baseline_result:
            continue
        delta = current_result.score.score - baseline_result.score.score
        score_changes.append(delta)
        entry = {
            "case_id": case_id,
            "baseline_score": baseline_result.score.score,
            "current_score": current_result.score.score,
            "delta": round(delta, 4),
            "baseline_passed": baseline_result.score.passed,
            "current_passed": current_result.score.passed,
        }
        if delta >= 0.05:
            improved.append(entry)
        if delta <= -0.05:
            regressed.append(entry)
        if baseline_result.score.passed and not current_result.score.passed:
            new_failures.append(entry)

    average_delta = sum(score_changes) / len(score_changes) if score_changes else 0.0
    return {
        "baseline_suite": baseline.suite,
        "current_suite": current.suite,
        "baseline_mode": baseline.mode,
        "current_mode": current.mode,
        "baseline_avg_score": baseline.summary.average_score,
        "current_avg_score": current.summary.average_score,
        "average_delta": round(average_delta, 4),
        "improved": improved,
        "regressed": regressed,
        "new_failures": new_failures,
        "generated_at": _timestamp(),
    }


def format_diff_markdown(diff: dict[str, Any]) -> str:
    lines = [
        "# Benchmark Regression Report",
        "",
        f"Generated: {diff['generated_at']}",
        "",
        "## Summary",
        f"- Baseline suite: {diff['baseline_suite']} ({diff['baseline_mode']})",
        f"- Current suite: {diff['current_suite']} ({diff['current_mode']})",
        f"- Baseline average score: {diff['baseline_avg_score']}",
        f"- Current average score: {diff['current_avg_score']}",
        f"- Average score delta: {diff['average_delta']}",
        "",
    ]

    def _section(title: str, items: list[dict[str, Any]]) -> None:
        lines.append(f"## {title}")
        if not items:
            lines.append("No changes.")
            lines.append("")
            return
        lines.append("| Case | Baseline | Current | Delta | Pass → Pass? |")
        lines.append("| --- | --- | --- | --- | --- |")
        for item in items:
            status = f"{item['baseline_passed']} → {item['current_passed']}"
            lines.append(
                f"| {item['case_id']} | {item['baseline_score']} | "
                f"{item['current_score']} | {item['delta']} | {status} |"
            )
        lines.append("")

    _section("Improved Cases", diff["improved"])
    _section("Regressed Cases", diff["regressed"])
    _section("New Failures", diff["new_failures"])
    return "\n".join(lines)


def load_report(path: Path) -> BenchmarkRunResult:
    payload = orjson.loads(path.read_bytes())
    return BenchmarkRunResult.model_validate(payload)


def write_markdown_report(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
