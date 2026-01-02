#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "packages" / "core" / "src"))

from trustai_core.benchmarks.compare import compare_reports, format_diff_markdown, load_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two TrustAI benchmark reports.")
    parser.add_argument("--baseline", required=True, help="Baseline benchmark JSON report")
    parser.add_argument("--current", required=True, help="Current benchmark JSON report")
    args = parser.parse_args()

    baseline = load_report(Path(args.baseline))
    current = load_report(Path(args.current))
    diff = compare_reports(baseline, current)
    markdown = format_diff_markdown(diff)

    reports_dir = Path("reports/benchmarks")
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = diff["generated_at"].replace(":", "").replace("-", "")
    md_path = reports_dir / f"benchmark_diff_{timestamp}.md"
    md_path.write_text(markdown, encoding="utf-8")

    print(f"Diff report: {md_path}")


if __name__ == "__main__":
    main()
