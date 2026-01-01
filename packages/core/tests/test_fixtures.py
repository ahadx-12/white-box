from __future__ import annotations

from pathlib import Path

from trustai_core.fixtures.compare import compare_golden_invariants, extract_golden_invariants
from trustai_core.fixtures.models import FixtureMetadata, FixtureRecording
from trustai_core.fixtures.replay import replay_fixtures


def _payload(
    *,
    accepted: bool,
    hts_code: str = "0101.10",
    optimized_rate: float = 5.0,
    baseline_rate: float = 6.0,
    rejected_because: list[str] | None = None,
) -> dict:
    if rejected_because is None:
        rejected_because = [] if accepted else ["gri_sequence_violation"]
    return {
        "status": "verified" if accepted else "failed",
        "iterations": [
            {
                "i": 1,
                "accepted": accepted,
                "rejected_because": rejected_because,
            }
        ],
        "proof": {
            "tariff_dossier": {
                "baseline": {"hts_code": hts_code, "duty_rate_pct": baseline_rate},
                "optimized": {"hts_code": hts_code, "duty_rate_pct": optimized_rate},
            },
            "model_routing": {
                "proposer": {"provider": "fixture", "model": "fixture"},
                "critic": {"provider": "fixture", "model": "fixture"},
            },
        },
    }


def _recording(payload: dict) -> FixtureRecording:
    invariants, summary = extract_golden_invariants(payload)
    return FixtureRecording(
        metadata=FixtureMetadata(
            pack_id="tariff",
            pack_version="sha",
            ontology_hash="ontology",
            axioms_hash="axioms",
            model_provider="fixture",
            model_id="fixture",
            timestamp="2024-01-01T00:00:00Z",
            input_hash="input",
        ),
        request={"input": "sample", "pack": "tariff"},
        result=payload,
        proof=payload.get("proof"),
        final_iteration_summary=summary,
        golden_invariants=invariants,
    )


def test_fixture_roundtrip_serialization(tmp_path: Path) -> None:
    payload = _payload(accepted=True)
    recording = _recording(payload)
    path = tmp_path / "fixture.json"
    path.write_bytes(recording.to_json())
    loaded = FixtureRecording.from_json(path.read_bytes())
    assert loaded.model_dump() == recording.model_dump()


def test_golden_invariants_acceptance_mismatch() -> None:
    recorded = _recording(_payload(accepted=True))
    current = _payload(accepted=False)
    comparison = compare_golden_invariants(recorded, current)
    assert not comparison.ok
    assert any("acceptance mismatch" in reason for reason in comparison.reasons)


def test_golden_invariants_hts_mismatch_and_allowed_codes() -> None:
    recorded = _recording(_payload(accepted=True, hts_code="0101.10"))
    mismatch_payload = _payload(accepted=True, hts_code="0202.20")
    mismatch = compare_golden_invariants(recorded, mismatch_payload)
    assert not mismatch.ok
    assert any("hts code mismatch" in reason for reason in mismatch.reasons)

    allowed = recorded.model_copy(
        update={
            "golden_invariants": recorded.golden_invariants.model_copy(
                update={"allowed_codes": ["0202.20", "0303.30"]}
            )
        }
    )
    allowed_result = compare_golden_invariants(allowed, mismatch_payload)
    assert allowed_result.ok


def test_golden_invariants_critical_gate_mismatch() -> None:
    recorded = _recording(_payload(accepted=True))
    current = _payload(accepted=False, rejected_because=["gri_sequence_violation"])
    comparison = compare_golden_invariants(recorded, current)
    assert not comparison.ok
    assert any("critical gate mismatch" in reason for reason in comparison.reasons)


def test_replay_runner_offline(tmp_path: Path) -> None:
    payload = _payload(accepted=True)
    recording = _recording(payload)
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_bytes(recording.to_json())

    def verify_fn(_recording):
        return payload

    outcomes = replay_fixtures([fixture_path], verify_fn)
    assert len(outcomes) == 1
    assert outcomes[0].ok
