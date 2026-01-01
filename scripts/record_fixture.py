from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "packages/core/src"))
sys.path.append(str(ROOT / "apps/api/src"))

from trustai_api.routes.utils import normalize_verification_result
from trustai_api.services.verifier_service import VerifierService, VerifyOptions
from trustai_api.settings import get_settings
from trustai_core.fixtures.compare import extract_golden_invariants
from trustai_core.fixtures.models import FixtureMetadata, FixtureRecording
from trustai_core.utils.hashing import sha256_canonical_json

FIXTURE_ROOT = Path("storage/fixtures/recordings")


def _require_live_keys() -> None:
    if (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("OPEN_AI_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("CLAUDE_AI_KEY")
    ):
        return
    raise SystemExit(
        "Missing live API keys. Set OPENAI_API_KEY/OPEN_AI_KEY or "
        "ANTHROPIC_API_KEY/CLAUDE_AI_KEY before recording."
    )


@contextmanager
def _force_live_mode() -> Any:
    original = os.environ.get("TRUSTAI_LLM_MODE")
    os.environ["TRUSTAI_LLM_MODE"] = "live"
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("TRUSTAI_LLM_MODE", None)
        else:
            os.environ["TRUSTAI_LLM_MODE"] = original


def _load_request(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise SystemExit("Input payload must be a JSON object.")
    if "input" not in payload:
        raise SystemExit("Input payload must include an 'input' field.")
    if "pack" not in payload:
        payload["pack"] = "tariff"
    return payload


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def _hash_file(path: Path) -> str:
    import hashlib

    hasher = hashlib.sha256()
    hasher.update(path.read_bytes())
    return hasher.hexdigest()


def _resolve_pack_hashes(pack: str) -> tuple[str, str]:
    pack_root = Path("storage/packs") / pack
    ontology_path = pack_root / "ontology.json"
    axioms_path = pack_root / "axioms.json"
    if not ontology_path.exists() or not axioms_path.exists():
        raise SystemExit(f"Missing ontology/axioms for pack '{pack}'.")
    return _hash_file(ontology_path), _hash_file(axioms_path)


def _extract_model_info(result_payload: dict[str, Any]) -> tuple[str, str]:
    model_routing = {}
    proof = result_payload.get("proof")
    if isinstance(proof, dict):
        model_routing = proof.get("model_routing") or {}
    proposer = model_routing.get("proposer") or {}
    critic = model_routing.get("critic") or {}
    provider = proposer.get("provider")
    model = proposer.get("model")
    if provider and model and provider == critic.get("provider") and model == critic.get("model"):
        return str(provider), str(model)
    if provider and model:
        return f"{provider}+{critic.get('provider')}", f"{model}+{critic.get('model')}"
    return "unknown", "unknown"


def _resolve_output_path(pack: str, case_id: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return FIXTURE_ROOT / pack / f"{case_id}_{timestamp}.json"


async def _run_verify(request_payload: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    verifier = VerifierService(settings)
    options_payload = request_payload.get("options") or {}
    options = None
    if isinstance(options_payload, dict) and options_payload:
        options = VerifyOptions(
            max_iters=options_payload.get("max_iters"),
            threshold=options_payload.get("threshold"),
            min_mutations=options_payload.get("min_mutations"),
        )
    result = await verifier.verify_sync(
        input_text=str(request_payload["input"]),
        pack=str(request_payload.get("pack") or "tariff"),
        options=options,
        evidence=request_payload.get("evidence"),
    )
    return normalize_verification_result(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="Record a live fixture for /v1/verify.")
    parser.add_argument("--input", required=True, help="Path to input JSON payload.")
    parser.add_argument("--case-id", help="Optional case identifier for the fixture name.")
    args = parser.parse_args()

    request_path = Path(args.input)
    if not request_path.exists():
        raise SystemExit(f"Input file not found: {request_path}")

    request_payload = _load_request(request_path)
    case_id = args.case_id or request_path.stem
    pack = str(request_payload.get("pack") or "tariff")

    _require_live_keys()
    with _force_live_mode():
        import asyncio

        result_payload = asyncio.run(_run_verify(request_payload))

    input_hash = sha256_canonical_json(request_payload)
    ontology_hash, axioms_hash = _resolve_pack_hashes(pack)
    model_provider, model_id = _extract_model_info(result_payload)
    metadata = FixtureMetadata(
        pack_id=pack,
        pack_version=_git_sha(),
        ontology_hash=ontology_hash,
        axioms_hash=axioms_hash,
        model_provider=model_provider,
        model_id=model_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        input_hash=input_hash,
    )
    golden_invariants, summary = extract_golden_invariants(result_payload)

    proposals = None
    critics = None
    proof = result_payload.get("proof")
    if isinstance(proof, dict):
        proposal_history = proof.get("proposal_history") or []
        if proposal_history:
            proposals = proposal_history
        elif proof.get("tariff_dossier"):
            proposals = [proof["tariff_dossier"]]
        critics = proof.get("critic_outputs")

    recording = FixtureRecording(
        metadata=metadata,
        request=request_payload,
        result=result_payload,
        proof=proof if isinstance(proof, dict) else None,
        final_iteration_summary=summary,
        golden_invariants=golden_invariants,
        proposals=proposals,
        critics=critics,
    )

    output_path = _resolve_output_path(pack, case_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(recording.to_json())

    print(f"Fixture recorded: {output_path}")
    print(f"Accepted: {golden_invariants.accepted}")
    if golden_invariants.final_hts_code:
        print(f"HTS: {golden_invariants.final_hts_code}")


if __name__ == "__main__":
    main()
