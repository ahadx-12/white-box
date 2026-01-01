from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import httpx

DEFAULT_TIMEOUT_S = 30.0


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def build_endpoints(base_url: str) -> dict[str, str]:
    normalized = normalize_base_url(base_url)
    return {
        "health": f"{normalized}/v1/health",
        "packs": f"{normalized}/v1/packs",
        "verify": f"{normalized}/v1/verify",
    }


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--pack", default="general")
    return parser


def _env_has_openai_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_KEY"))


def _env_has_anthropic_key() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUD_AI_KEY"))


def _require_live_keys() -> list[str]:
    missing: list[str] = []
    if not _env_has_openai_key():
        missing.append("OPENAI_API_KEY")
    if not _env_has_anthropic_key():
        missing.append("ANTHROPIC_API_KEY")
    return missing


def _parse_json_response(response: httpx.Response) -> dict[str, Any] | None:
    try:
        return response.json()
    except ValueError:
        return None


def _print_error_response(response: httpx.Response) -> None:
    payload = _parse_json_response(response)
    if payload:
        message = payload.get("message")
        status = payload.get("status")
        hint = payload.get("hint")
        details = [part for part in [status, message, hint] if part]
        if details:
            print("Upstream error:", " | ".join(details))
        if message and "Tried models" in message:
            print(message)
        return
    print(f"Request failed: status={response.status_code} body={response.text}")


def run_smoke(base_url: str, pack: str, llm_mode: str | None = None) -> int:
    mode = (llm_mode or os.getenv("TRUSTAI_LLM_MODE", "fixture")).lower()
    if mode == "mock":
        mode = "fixture"
    if mode == "live":
        missing = _require_live_keys()
        if missing:
            print(
                "TRUSTAI_LLM_MODE=live but required API keys are missing: "
                + ", ".join(missing)
            )
            return 2

    endpoints = build_endpoints(base_url)

    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT_S) as client:
            health_response = client.request("GET", endpoints["health"])
            if health_response.status_code != 200:
                _print_error_response(health_response)
                return 1

            packs_response = client.request("GET", endpoints["packs"])
            if packs_response.status_code != 200:
                _print_error_response(packs_response)
                return 1

            verify_response = client.request(
                "POST",
                endpoints["verify"],
                headers={"Content-Type": "application/json", "X-TrustAI-Pack": pack},
                json={"input": "The sky is blue."},
            )
            if verify_response.status_code != 200:
                _print_error_response(verify_response)
                return 1

            payload = _parse_json_response(verify_response)
            if payload is None:
                print("Verify response:", verify_response.text)
            else:
                print("Verify response:\n" + json.dumps(payload, indent=2, sort_keys=True))
    except httpx.RequestError as exc:
        print(f"Network error: {exc}")
        return 1

    return 0


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()
    sys.exit(run_smoke(args.base_url, args.pack))


if __name__ == "__main__":
    main()
