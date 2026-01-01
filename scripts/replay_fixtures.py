from __future__ import annotations

import argparse
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.append(str(ROOT / "packages/core/src"))
sys.path.append(str(ROOT / "apps/api/src"))

from trustai_api.routes.utils import normalize_verification_result
from trustai_api.services.verifier_service import VerifierService, VerifyOptions
from trustai_api.settings import get_settings
from trustai_core.fixtures.replay import replay_fixtures

DEFAULT_FIXTURE_ROOT = Path("storage/fixtures/recordings")
DEFAULT_REPORT_ROOT = Path("reports/dev")


@contextmanager
def _temp_env(key: str, value: str | None):
    original = os.environ.get(key)
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value
    try:
        yield
    finally:
        if original is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original


def _list_fixtures(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.exists():
        return []
    return sorted([item for item in path.rglob("*.json") if item.is_file()])


def _write_report(outcomes, report_path: Path, mode: str) -> None:
    total = len(outcomes)
    passed = sum(1 for outcome in outcomes if outcome.ok)
    failed = total - passed
    timestamp = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Fixture Replay Report",
        "",
        f"- Timestamp: {timestamp}",
        f"- Mode: {mode}",
        f"- Total: {total}",
        f"- Passed: {passed}",
        f"- Failed: {failed}",
        "",
        "| Fixture | Status | Reasons |",
        "| --- | --- | --- |",
    ]
    for outcome in outcomes:
        status = "PASS" if outcome.ok else "FAIL"
        reasons = "; ".join(outcome.reasons) if outcome.reasons else "-"
        lines.append(f"| {outcome.fixture_path} | {status} | {reasons} |")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay fixture recordings and compare invariants.")
    parser.add_argument(
        "--path",
        default=str(DEFAULT_FIXTURE_ROOT),
        help="Fixture file or directory (default: storage/fixtures/recordings).",
    )
    parser.add_argument(
        "--mode",
        default="fixture",
        choices=("fixture", "live"),
        help="LLM mode to use for replay (default: fixture).",
    )
    parser.add_argument(
        "--report-dir",
        default=str(DEFAULT_REPORT_ROOT),
        help="Directory for markdown report output.",
    )
    args = parser.parse_args()

    fixture_root = Path(args.path)
    fixture_paths = _list_fixtures(fixture_root)
    if not fixture_paths:
        raise SystemExit(f"No fixture files found under {fixture_root}")

    report_dir = Path(args.report_dir)
    report_name = datetime.now(timezone.utc).strftime("fixture_replay_%Y%m%d_%H%M%S.md")
    report_path = report_dir / report_name

    outcomes = []
    with _temp_env("TRUSTAI_LLM_MODE", args.mode):
        for recording_path in fixture_paths:
            def verify_fn(recording, path=recording_path):
                request = recording.request
                options_payload = request.get("options") or {}
                options = None
                if isinstance(options_payload, dict) and options_payload:
                    options = VerifyOptions(
                        max_iters=options_payload.get("max_iters"),
                        threshold=options_payload.get("threshold"),
                        min_mutations=options_payload.get("min_mutations"),
                    )
                pack = str(request.get("pack") or "tariff")
                evidence = request.get("evidence")
                with _temp_env("TRUSTAI_TARIFF_FIXTURE", str(path) if pack == "tariff" else None):
                    settings = get_settings()
                    verifier = VerifierService(settings)
                    import asyncio

                    result = asyncio.run(
                        verifier.verify_sync(
                            input_text=str(request["input"]),
                            pack=pack,
                            options=options,
                            evidence=evidence,
                        )
                    )
                return normalize_verification_result(result)

            outcomes.extend(replay_fixtures([recording_path], verify_fn))

    for outcome in outcomes:
        status = "PASS" if outcome.ok else "FAIL"
        reason_text = f" ({'; '.join(outcome.reasons)})" if outcome.reasons else ""
        print(f"{status}: {outcome.fixture_path}{reason_text}")

    _write_report(outcomes, report_path, args.mode)
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
