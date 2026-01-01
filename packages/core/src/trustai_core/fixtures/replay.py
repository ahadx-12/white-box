from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from trustai_core.fixtures.compare import compare_golden_invariants
from trustai_core.fixtures.models import FixtureRecording


@dataclass(frozen=True)
class ReplayOutcome:
    fixture_path: Path
    ok: bool
    reasons: list[str]
    comparison_details: object | None = None


VerifyFn = Callable[[FixtureRecording], dict]


def replay_fixtures(
    fixture_paths: list[Path],
    verify_fn: VerifyFn,
) -> list[ReplayOutcome]:
    outcomes: list[ReplayOutcome] = []
    for path in fixture_paths:
        recording = FixtureRecording.from_json(path.read_bytes())
        current_payload = verify_fn(recording)
        comparison = compare_golden_invariants(recording, current_payload)
        outcomes.append(
            ReplayOutcome(
                fixture_path=path,
                ok=comparison.ok,
                reasons=comparison.reasons,
                comparison_details=comparison,
            )
        )
    return outcomes
