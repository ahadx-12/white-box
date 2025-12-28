from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass

import httpx


@dataclass
class SmokeResult:
    name: str
    ok: bool
    details: str


def _request(client: httpx.Client, method: str, url: str, **kwargs) -> httpx.Response:
    response = client.request(method, url, **kwargs)
    return response


def _check_health(client: httpx.Client, base_url: str) -> SmokeResult:
    response = _request(client, "GET", f"{base_url}/v1/health")
    if response.status_code != 200:
        return SmokeResult("health", False, f"status={response.status_code}")
    return SmokeResult("health", True, "ok")


def _check_packs(client: httpx.Client, base_url: str) -> SmokeResult:
    response = _request(client, "GET", f"{base_url}/v1/packs")
    if response.status_code != 200:
        return SmokeResult("packs", False, f"status={response.status_code}")
    payload = response.json()
    if "packs" not in payload:
        return SmokeResult("packs", False, "missing packs list")
    return SmokeResult("packs", True, f"packs={len(payload['packs'])}")


def _check_verify_sync(client: httpx.Client, base_url: str, pack: str) -> SmokeResult:
    response = _request(
        client,
        "POST",
        f"{base_url}/v1/verify",
        headers={"X-TrustAI-Pack": pack},
        json={"input": "The sky is blue."},
    )
    if response.status_code != 200:
        return SmokeResult("verify_sync", False, f"status={response.status_code}")
    payload = response.json()
    if payload.get("status") != "verified":
        return SmokeResult("verify_sync", False, f"status={payload.get('status')}")
    return SmokeResult("verify_sync", True, "ok")


def _check_verify_async(
    client: httpx.Client, base_url: str, pack: str, timeout_s: int = 30
) -> SmokeResult:
    response = _request(
        client,
        "POST",
        f"{base_url}/v1/verify",
        params={"mode": "async"},
        headers={"X-TrustAI-Pack": pack},
        json={"input": "The sky is blue."},
    )
    if response.status_code == 503 and "Redis unavailable" in response.text:
        return SmokeResult("verify_async", True, "SKIPPED (redis unavailable)")
    if response.status_code != 200:
        return SmokeResult("verify_async", False, f"status={response.status_code}")
    payload = response.json()
    job_id = payload.get("job_id")
    if not job_id:
        return SmokeResult("verify_async", False, "missing job_id")

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        job_response = _request(client, "GET", f"{base_url}/v1/jobs/{job_id}")
        if job_response.status_code != 200:
            return SmokeResult("verify_async", False, f"job_status={job_response.status_code}")
        job_payload = job_response.json()
        status = job_payload.get("status")
        if status == "done":
            return SmokeResult("verify_async", True, "ok")
        if status == "failed":
            return SmokeResult("verify_async", False, f"failed: {job_payload.get('error')}")
        time.sleep(2)
    return SmokeResult("verify_async", False, "timeout waiting for async job")


def run_smoke(base_url: str, pack: str) -> int:
    results: list[SmokeResult] = []
    with httpx.Client(timeout=30.0) as client:
        checks = [
            ("health", lambda: _check_health(client, base_url)),
            ("packs", lambda: _check_packs(client, base_url)),
            ("verify_sync", lambda: _check_verify_sync(client, base_url, pack)),
            ("verify_async", lambda: _check_verify_async(client, base_url, pack)),
        ]
        for name, check in checks:
            try:
                results.append(check())
            except httpx.RequestError as exc:
                results.append(SmokeResult(name, False, f"request error: {exc}"))

    ok = True
    print("Smoke report:")
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        if result.details.startswith("SKIPPED"):
            status = "SKIP"
        print(f"- {result.name}: {status} ({result.details})")
        if not result.ok and not result.details.startswith("SKIPPED"):
            ok = False
    return 0 if ok else 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--pack", default="general")
    args = parser.parse_args()
    sys.exit(run_smoke(args.base_url.rstrip("/"), args.pack))


if __name__ == "__main__":
    main()
