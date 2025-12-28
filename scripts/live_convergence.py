from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

SCENARIOS_PATH = Path(__file__).with_name("live_scenarios.json")
DEFAULT_THRESHOLD = 0.92


@dataclass
class ScenarioResult:
    name: str
    iterations: int
    final_score: float
    corrected: bool
    proof_id: str


def _load_scenarios() -> list[dict[str, str]]:
    data = json.loads(SCENARIOS_PATH.read_text())
    if not isinstance(data, list):
        raise ValueError("Scenario file must contain a list")
    return data


def _build_prompt(scenario: dict[str, str]) -> str:
    input_text = scenario.get("input", "").strip()
    question = scenario.get("question", "").strip()
    if question:
        return f"{input_text}\n\nQuestion: {question}"
    return input_text


def _scores_improved(scores: list[float]) -> bool:
    return any(earlier < later for earlier, later in zip(scores, scores[1:]))


def _has_nontrivial_feedback(iterations: list[dict[str, Any]]) -> bool:
    for item in iterations:
        if item.get("feedback_text"):
            return True
        if item.get("top_conflicts"):
            return True
    return False


def _request_verify(
    client: httpx.Client,
    base_url: str,
    pack: str,
    input_text: str,
) -> dict[str, Any]:
    response = client.post(
        f"{base_url}/v1/verify",
        headers={"X-TrustAI-Pack": pack},
        json={"input": input_text},
    )
    response.raise_for_status()
    return response.json()


def _evaluate_payload(
    scenario_name: str,
    payload: dict[str, Any],
    threshold: float,
) -> ScenarioResult:
    iterations = payload.get("iterations", [])
    similarity_history = payload.get("similarity_history", [])
    final_score = similarity_history[-1] if similarity_history else 0.0
    status = payload.get("status")
    if status == "failed":
        if len(iterations) < 2 or not _has_nontrivial_feedback(iterations):
            raise AssertionError(
                f"Scenario {scenario_name} failed without sufficient iterations/feedback"
            )
    if not _scores_improved([item.get("score", 0.0) for item in iterations]):
        raise AssertionError(f"Scenario {scenario_name} did not improve similarity")

    corrected = final_score >= threshold
    return ScenarioResult(
        name=scenario_name,
        iterations=len(iterations),
        final_score=final_score,
        corrected=corrected,
        proof_id=payload.get("proof_id", ""),
    )


def run(base_url: str, pack: str, runs: int, timeout_s: int) -> int:
    scenarios = _load_scenarios()
    passed_threshold_counts: list[int] = []
    all_results: list[ScenarioResult] = []

    with httpx.Client(timeout=timeout_s) as client:
        for run_idx in range(1, runs + 1):
            run_passes = 0
            for scenario in scenarios:
                name = scenario.get("name", f"scenario_{run_idx}")
                prompt = _build_prompt(scenario)
                payload = _request_verify(client, base_url, pack, prompt)
                result = _evaluate_payload(name, payload, DEFAULT_THRESHOLD)
                all_results.append(result)
                if result.corrected:
                    run_passes += 1
            passed_threshold_counts.append(run_passes)

    print("Live convergence report:")
    print("scenario\titerations\tfinal_score\tcorrected\tproof_id")
    for result in all_results:
        print(
            f"{result.name}\t{result.iterations}\t{result.final_score:.4f}\t"
            f"{str(result.corrected).lower()}\t{result.proof_id}"
        )

    if not all(count >= 3 for count in passed_threshold_counts):
        print("\nFAIL: Fewer than 3 scenarios met the threshold in at least one run.")
        return 1
    print("\nPASS: Threshold met for at least 3 scenarios in every run.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--pack", default="general")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    sys.exit(run(args.base_url.rstrip("/"), args.pack, args.runs, args.timeout))


if __name__ == "__main__":
    main()
