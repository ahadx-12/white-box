from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

DEFAULT_OUT = Path("apps/api/tests/fixtures/tariff_fixture.json")


def _read_prompt(arg_prompt: str | None) -> str:
    if arg_prompt:
        return arg_prompt
    return "\n".join(line.rstrip("\n") for line in sys.stdin) or ""


def _sanitize_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        cleaned = {}
        for key, value in payload.items():
            if key in {"run_id", "request_id", "created_at", "updated_at", "timestamp"}:
                continue
            cleaned[key] = _sanitize_payload(value)
        return cleaned
    if isinstance(payload, list):
        return [_sanitize_payload(item) for item in payload]
    return payload


def _cap_list(items: list[Any], limit: int) -> list[Any]:
    return items[:limit]


def _normalize_tariff_dossier(dossier: dict[str, Any] | None) -> dict[str, Any] | None:
    if dossier is None:
        return None
    normalized = _sanitize_payload(dossier)
    if not isinstance(normalized, dict):
        return None
    if isinstance(normalized.get("mutations"), list):
        normalized["mutations"] = _cap_list(normalized["mutations"], 10)
    if isinstance(normalized.get("what_if_candidates"), list):
        normalized["what_if_candidates"] = _cap_list(normalized["what_if_candidates"], 5)
    if isinstance(normalized.get("gri_trace"), dict):
        trace = normalized["gri_trace"]
        if isinstance(trace.get("steps"), list):
            trace["steps"] = _cap_list(trace["steps"], 6)
        if isinstance(trace.get("violations"), list):
            trace["violations"] = _cap_list(trace["violations"], 10)
    return normalized


def _resolve_output_path(out_arg: str | None) -> Path:
    if not out_arg:
        return DEFAULT_OUT
    base = Path(out_arg)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    if base.is_dir() or str(base).endswith(os.sep):
        return base / f"tariff_fixture_{timestamp}.json"
    if base.suffix:
        return base.with_name(f"{base.stem}_{timestamp}{base.suffix}")
    return base.with_name(f"{base.name}_{timestamp}.json")


def _extract_fixture(response_payload: dict[str, Any]) -> dict[str, Any]:
    proof = response_payload.get("proof") or {}
    dossier = _normalize_tariff_dossier(proof.get("tariff_dossier"))
    critics = proof.get("critic_outputs") or []
    proposals = [dossier] if dossier else []
    return {"proposals": proposals, "critics": critics}


def main() -> None:
    parser = argparse.ArgumentParser(description="Record tariff fixtures from live API runs.")
    parser.add_argument("--prompt", help="Input prompt for /v1/verify")
    parser.add_argument("--out", help="Output path (timestamped when provided)")
    parser.add_argument(
        "--evidence",
        action="append",
        default=None,
        help="Evidence text (repeatable)",
    )
    args = parser.parse_args()

    prompt = _read_prompt(args.prompt)
    if not prompt.strip():
        raise SystemExit("Prompt is required via --prompt or stdin.")

    base_url = os.getenv("TRUSTAI_API_BASE_URL", "http://localhost:8000")
    request_payload: dict[str, Any] = {
        "input": prompt,
        "pack": "tariff",
    }
    if args.evidence:
        request_payload["evidence"] = args.evidence

    response = httpx.post(f"{base_url}/v1/verify", json=request_payload, timeout=60.0)
    response.raise_for_status()
    response_payload = response.json()

    fixture_payload = {
        "_request": request_payload,
        "_response": _sanitize_payload(response_payload),
        **_extract_fixture(response_payload),
    }

    out_path = _resolve_output_path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(fixture_payload, indent=2, sort_keys=True))
    print(f"Wrote fixture to {out_path}")


if __name__ == "__main__":
    main()
