from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import orjson
from pydantic import ValidationError

from trustai_core.llm.base import LLMClient, LLMError
from trustai_core.packs.registry import PackContext, register_pack
from trustai_core.packs.tariff.hdc import HDCScore, bundle_tokens, compare_bundles
from trustai_core.packs.tariff.models import (
    TariffCritique,
    TariffDossier,
    TariffVerificationResult,
    TariffVerifyIteration,
)
from trustai_core.packs.tariff.prompts import (
    build_tariff_critic_prompt,
    build_tariff_proposal_prompt,
    build_tariff_revision_prompt,
)
from trustai_core.utils.hashing import sha256_canonical_json

TARIFF_PACK_VERSION = "0.1"
TARIFF_THRESHOLD_DEFAULT = 0.92


@dataclass
class TariffOptions:
    max_iters: int = 4
    threshold: float = TARIFF_THRESHOLD_DEFAULT


class TariffPack:
    name = "tariff"

    def __init__(self, context: PackContext) -> None:
        self._context = context
        self.fingerprint = sha256_canonical_json(
            {"pack": self.name, "version": TARIFF_PACK_VERSION}
        )

    async def run(self, input_text: str, options: dict[str, object] | None) -> TariffVerificationResult:
        resolved_options = _resolve_options(options)
        fixture = _load_fixture()
        if fixture:
            return await self._run_with_fixture(input_text, resolved_options, fixture)
        if self._context.llm_mode == "mock":
            return _build_llm_error_result(
                input_text,
                self.name,
                self.fingerprint,
                "Mock mode requires FAKE_LLM=1 for the tariff pack.",
            )
        router = _select_router(self._context)
        if router.error:
            return _build_llm_error_result(
                input_text,
                self.name,
                self.fingerprint,
                router.error,
            )
        iterations: list[TariffVerifyIteration] = []
        critic_outputs: list[TariffCritique] = []
        dossier: TariffDossier | None = None
        previous_bundle: list[int] | None = None
        mismatch_report: str = ""
        feedback: str | None = None
        previous_dossier: TariffDossier | None = None

        try:
            for i in range(1, resolved_options.max_iters + 1):
                if dossier and feedback:
                    prompt = build_tariff_revision_prompt(
                        input_text,
                        dossier,
                        critic_outputs[-1].model_dump(),
                        mismatch_report,
                        _tariff_dossier_schema(),
                    )
                else:
                    prompt = build_tariff_proposal_prompt(
                        input_text,
                        feedback,
                        _tariff_dossier_schema(),
                    )
                dossier = await router.proposer.complete_tariff(prompt)
                critique = await router.critic.complete_critique(
                    build_tariff_critic_prompt(
                        input_text,
                        dossier,
                        _tariff_critique_schema(),
                    )
                )
                iteration, previous_bundle, mismatch_report = _evaluate_iteration(
                    i=i,
                    dossier=dossier,
                    critique=critique,
                    previous_bundle=previous_bundle,
                    previous_dossier=previous_dossier,
                    threshold=resolved_options.threshold,
                )
                iterations.append(iteration)
                critic_outputs.append(critique)
                feedback = iteration.feedback_text
                previous_dossier = dossier
                if iteration.accepted:
                    break
        except LLMError as exc:
            return _build_llm_error_result(
                input_text,
                self.name,
                self.fingerprint,
                f"LLM error: {exc}",
            )

        final_answer = _format_tariff_report(dossier) if dossier else None
        explain = _build_explain(iterations)
        proof_payload = _build_proof_payload(
            input_text,
            self.name,
            self.fingerprint,
            final_answer,
            iterations,
            explain,
            dossier,
            critic_outputs,
            router.model_routing,
        )
        proof_id = sha256_canonical_json(proof_payload)
        return TariffVerificationResult(
            status=proof_payload["status"],
            proof_id=proof_id,
            pack=self.name,
            pack_fingerprint=self.fingerprint,
            evidence_manifest_hash=proof_payload["evidence_manifest_hash"],
            final_answer=final_answer,
            iterations=iterations,
            explain=explain,
            tariff_dossier=dossier,
            critic_outputs=critic_outputs,
            model_routing=router.model_routing,
        )

    async def _run_with_fixture(
        self,
        input_text: str,
        options: TariffOptions,
        fixture: dict[str, Any],
    ) -> TariffVerificationResult:
        proposals = fixture.get("proposals") or []
        critiques = fixture.get("critics") or []
        if not proposals or not critiques:
            return _build_llm_error_result(
                input_text,
                self.name,
                self.fingerprint,
                "Fixture missing proposals or critiques.",
            )
        iterations: list[TariffVerifyIteration] = []
        critic_outputs: list[TariffCritique] = []
        dossier: TariffDossier | None = None
        previous_bundle: list[int] | None = None
        mismatch_report = ""
        previous_dossier: TariffDossier | None = None

        for i in range(1, options.max_iters + 1):
            proposal_payload = proposals[min(i - 1, len(proposals) - 1)]
            critique_payload = critiques[min(i - 1, len(critiques) - 1)]
            dossier = TariffDossier.model_validate(proposal_payload)
            critique = TariffCritique.model_validate(critique_payload)
            iteration, previous_bundle, mismatch_report = _evaluate_iteration(
                i=i,
                dossier=dossier,
                critique=critique,
                previous_bundle=previous_bundle,
                previous_dossier=previous_dossier,
                threshold=options.threshold,
            )
            iterations.append(iteration)
            critic_outputs.append(critique)
            previous_dossier = dossier
            if iteration.accepted:
                break

        final_answer = _format_tariff_report(dossier) if dossier else None
        explain = _build_explain(iterations)
        model_routing = {
            "proposer": {"provider": "fixture", "model": "fixture"},
            "critic": {"provider": "fixture", "model": "fixture"},
        }
        proof_payload = _build_proof_payload(
            input_text,
            self.name,
            self.fingerprint,
            final_answer,
            iterations,
            explain,
            dossier,
            critic_outputs,
            model_routing,
        )
        proof_id = sha256_canonical_json(proof_payload)
        return TariffVerificationResult(
            status=proof_payload["status"],
            proof_id=proof_id,
            pack=self.name,
            pack_fingerprint=self.fingerprint,
            evidence_manifest_hash=proof_payload["evidence_manifest_hash"],
            final_answer=final_answer,
            iterations=iterations,
            explain=explain,
            tariff_dossier=dossier,
            critic_outputs=critic_outputs,
            model_routing=model_routing,
        )


@dataclass
class RouterSelection:
    proposer: "TariffLLM"
    critic: "TariffLLM"
    model_routing: dict[str, Any]
    error: str | None = None


class TariffLLM:
    def __init__(self, provider: str, client: LLMClient) -> None:
        self.provider = provider
        self.client = client

    async def complete_tariff(self, prompt: str) -> TariffDossier:
        payload = await _complete_json(self.client, prompt)
        try:
            return TariffDossier.model_validate(payload)
        except ValidationError as exc:
            raise LLMError(f"Tariff proposer returned invalid JSON: {exc}") from exc

    async def complete_critique(self, prompt: str) -> TariffCritique:
        payload = await _complete_json(self.client, prompt)
        try:
            return TariffCritique.model_validate(payload)
        except ValidationError as exc:
            raise LLMError(f"Tariff critic returned invalid JSON: {exc}") from exc


async def _complete_json(client: LLMClient, prompt: str) -> dict[str, Any]:
    try:
        payload = await client.complete_json(prompt, {})
        if isinstance(payload, dict):
            return payload
    except LLMError:
        pass
    content = await client.complete_text(prompt)
    return _parse_json(content)


def _parse_json(content: str) -> dict[str, Any]:
    try:
        payload = orjson.loads(content)
    except orjson.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise LLMError("LLM response did not contain JSON")
        payload = orjson.loads(content[start : end + 1])
    if not isinstance(payload, dict):
        raise LLMError("LLM response JSON was not an object")
    return payload


def _resolve_options(options: dict[str, object] | None) -> TariffOptions:
    if not options:
        return TariffOptions()
    max_iters = int(options.get("max_iters") or 4)
    threshold = float(options.get("threshold") or TARIFF_THRESHOLD_DEFAULT)
    return TariffOptions(max_iters=max_iters, threshold=threshold)


def _select_router(context: PackContext) -> RouterSelection:
    openai_client = _safe_client(context.openai_client_factory)
    anthropic_client = _safe_client(context.anthropic_client_factory)

    if not openai_client and not anthropic_client:
        return RouterSelection(
            proposer=_null_llm(),
            critic=_null_llm(),
            model_routing={},
            error="No LLM providers available. Configure OPENAI_API_KEY or ANTHROPIC_API_KEY.",
        )

    if openai_client and anthropic_client:
        proposer = TariffLLM("anthropic", anthropic_client)
        critic = TariffLLM("openai", openai_client)
    elif anthropic_client:
        proposer = TariffLLM("anthropic", anthropic_client)
        critic = TariffLLM("anthropic", anthropic_client)
    else:
        proposer = TariffLLM("openai", openai_client)
        critic = TariffLLM("openai", openai_client)

    return RouterSelection(
        proposer=proposer,
        critic=critic,
        model_routing={
            "proposer": {
                "provider": proposer.provider,
                "model": getattr(proposer.client, "model_id", None),
            },
            "critic": {
                "provider": critic.provider,
                "model": getattr(critic.client, "model_id", None),
            },
        },
    )


def _safe_client(factory) -> LLMClient | None:
    try:
        return factory()
    except LLMError:
        return None


def _null_llm() -> TariffLLM:
    return TariffLLM("none", _NullLLM())


class _NullLLM:
    async def complete_json(self, prompt: str, schema: dict) -> dict:
        raise LLMError("No LLM configured")

    async def complete_text(self, prompt: str) -> str:
        raise LLMError("No LLM configured")


def _build_llm_error_result(
    input_text: str,
    pack: str,
    fingerprint: str,
    error: str,
) -> TariffVerificationResult:
    iteration = TariffVerifyIteration(
        i=1,
        score=0.0,
        accepted=False,
        rejected_because=["llm_unavailable"],
        conflicts=[],
        top_conflicts=[error],
        unsupported=[],
        missing=[],
        feedback_text=f"LLM unavailable: {error}",
        answer_delta_summary="initial_answer",
        hdc_score=None,
        mismatch_report=error,
    )
    explain = {
        "summary": error,
        "missing_required": [],
        "unsupported_claims": [],
        "key_conflicts": [],
    }
    payload = _build_proof_payload(
        input_text,
        pack,
        fingerprint,
        None,
        [iteration],
        explain,
        None,
        [],
        {},
    )
    proof_id = sha256_canonical_json(payload)
    return TariffVerificationResult(
        status="failed",
        proof_id=proof_id,
        pack=pack,
        pack_fingerprint=fingerprint,
        evidence_manifest_hash=payload["evidence_manifest_hash"],
        final_answer=None,
        iterations=[iteration],
        explain=explain,
        tariff_dossier=None,
        critic_outputs=[],
        model_routing={},
    )


def _tariff_dossier_schema() -> dict[str, Any]:
    return TariffDossier.model_json_schema()


def _tariff_critique_schema() -> dict[str, Any]:
    return TariffCritique.model_json_schema()


def _evaluate_iteration(
    i: int,
    dossier: TariffDossier,
    critique: TariffCritique,
    previous_bundle: list[int] | None,
    previous_dossier: TariffDossier | None,
    threshold: float,
) -> tuple[TariffVerifyIteration, list[int], str]:
    rejected_because: list[str] = []
    conflicts = sorted(set(critique.conflicts))
    unsupported = sorted(set(critique.unsupported))
    missing = sorted(set(critique.missing))

    baseline_duty = dossier.baseline.duty_rate_pct
    optimized_duty = dossier.optimized.duty_rate_pct

    if baseline_duty is None and not dossier.questions_for_user:
        rejected_because.append("baseline_duty_missing")

    if len(dossier.mutations) < 5:
        if "cannot reduce" not in dossier.optimized.rationale.lower():
            rejected_because.append("insufficient_mutations")

    if baseline_duty is not None and optimized_duty is not None:
        if dossier.best_option_id and optimized_duty > baseline_duty:
            rejected_because.append("optimized_duty_higher_than_baseline")

    has_lowering_option = _has_lowering_option(dossier)
    if not has_lowering_option and "cannot reduce" not in dossier.optimized.rationale.lower():
        rejected_because.append("no_lowering_option")

    if not dossier.best_option_id and dossier.optimized.duty_rate_pct is not None:
        rejected_because.append("missing_best_option")

    hdc_bundle = bundle_tokens(_hdc_tokens(dossier))
    hdc = compare_bundles(previous_bundle, hdc_bundle)
    hdc_score = hdc.similarity
    if previous_bundle is not None and hdc_score < threshold:
        rejected_because.append("hdc_drift")

    if conflicts:
        rejected_because.append("conflicts")
    if unsupported:
        rejected_because.append("unsupported")
    if missing:
        rejected_because.append("missing")

    score = _score_iteration(rejected_because, hdc_score)
    accepted = score >= threshold and not rejected_because

    mismatch_report = _build_mismatch_report(rejected_because, hdc)
    feedback_text = _build_feedback_text(rejected_because, critique, mismatch_report)
    answer_delta_summary = _summarize_dossier_delta(previous_dossier, dossier)
    top_conflicts = _build_top_conflicts(rejected_because, conflicts, unsupported, missing)

    iteration = TariffVerifyIteration(
        i=i,
        score=round(score, 6),
        accepted=accepted,
        rejected_because=rejected_because,
        conflicts=conflicts,
        top_conflicts=top_conflicts,
        unsupported=unsupported,
        missing=missing,
        feedback_text=feedback_text,
        answer_delta_summary=answer_delta_summary,
        hdc_score=round(hdc_score, 6),
        mismatch_report=mismatch_report,
    )
    return iteration, hdc_bundle, mismatch_report


def _has_lowering_option(dossier: TariffDossier) -> bool:
    baseline = dossier.baseline.duty_rate_pct
    if baseline is None:
        return False
    for mutation in dossier.mutations:
        if mutation.expected_duty_rate_pct is not None and mutation.expected_duty_rate_pct < baseline:
            return True
    optimized = dossier.optimized.duty_rate_pct
    if optimized is not None and optimized < baseline:
        return True
    return False


def _hdc_tokens(dossier: TariffDossier) -> list[str]:
    tokens = [
        f"baseline.hts={dossier.baseline.hts_code}",
        f"baseline.duty={dossier.baseline.duty_rate_pct}",
        f"optimized.hts={dossier.optimized.hts_code}",
        f"optimized.duty={dossier.optimized.duty_rate_pct}",
        f"best_option={dossier.best_option_id}",
    ]
    for assumption in dossier.assumptions:
        tokens.append(f"assumption={assumption}")
    for mutation in dossier.mutations:
        tokens.append(f"mutation={mutation.id}:{mutation.category}")
    return sorted(tokens)


def _score_iteration(rejected_because: list[str], hdc_score: float) -> float:
    penalty = 0.0
    if rejected_because:
        penalty = 0.1 * len(set(rejected_because))
    score = max(0.0, 1.0 - penalty)
    return min(score, hdc_score)


def _build_mismatch_report(rejected_because: list[str], hdc: HDCScore) -> str:
    reasons = ", ".join(rejected_because) if rejected_because else "none"
    return (
        f"Rejected because: {reasons}. "
        f"HDC similarity={hdc.similarity:.4f}, drift={hdc.drift:.4f}."
    )


def _build_feedback_text(
    rejected_because: list[str],
    critique: TariffCritique,
    mismatch_report: str,
) -> str:
    parts = [mismatch_report]
    if critique.missing:
        parts.append("Missing: " + "; ".join(critique.missing))
    if critique.unsupported:
        parts.append("Unsupported: " + "; ".join(critique.unsupported))
    if critique.conflicts:
        parts.append("Conflicts: " + "; ".join(critique.conflicts))
    if critique.suggested_fixes:
        parts.append("Suggested fixes: " + "; ".join(critique.suggested_fixes))
    if rejected_because:
        parts.append("Rejected: " + ", ".join(rejected_because))
    return "\n".join(parts)


def _summarize_dossier_delta(
    previous: TariffDossier | None,
    current: TariffDossier,
) -> str:
    if previous is None:
        return "initial_answer"
    changes = []
    if previous.baseline.hts_code != current.baseline.hts_code:
        changes.append("baseline_hts_changed")
    if previous.baseline.duty_rate_pct != current.baseline.duty_rate_pct:
        changes.append("baseline_duty_changed")
    if previous.optimized.duty_rate_pct != current.optimized.duty_rate_pct:
        changes.append("optimized_duty_changed")
    if previous.best_option_id != current.best_option_id:
        changes.append("best_option_changed")
    if not changes:
        return "no_change"
    return "changes: " + ", ".join(changes)


def _build_top_conflicts(
    rejected_because: list[str],
    conflicts: list[str],
    unsupported: list[str],
    missing: list[str],
) -> list[str]:
    items: list[str] = []
    items.extend(conflicts)
    items.extend(unsupported)
    items.extend(missing)
    items.extend(rejected_because)
    return items[:6]


def _build_explain(iterations: list[TariffVerifyIteration]) -> dict[str, Any]:
    if not iterations:
        return {
            "summary": "No iterations",
            "missing_required": [],
            "unsupported_claims": [],
            "key_conflicts": [],
        }
    last = iterations[-1]
    summary = (
        f"Score {last.score:.4f}; accepted={str(last.accepted).lower()}; "
        f"rejected={len(last.rejected_because)}"
    )
    return {
        "summary": summary,
        "missing_required": last.missing,
        "unsupported_claims": last.unsupported,
        "key_conflicts": last.conflicts,
    }


def _build_proof_payload(
    input_text: str,
    pack: str,
    fingerprint: str,
    final_answer: str | None,
    iterations: list[TariffVerifyIteration],
    explain: dict[str, Any],
    dossier: TariffDossier | None,
    critics: list[TariffCritique],
    model_routing: dict[str, Any],
) -> dict[str, Any]:
    status = "verified" if iterations and iterations[-1].accepted else "failed"
    return {
        "status": status,
        "pack": pack,
        "pack_fingerprint": fingerprint,
        "evidence_manifest_hash": sha256_canonical_json({"input": input_text}),
        "final_answer": final_answer,
        "iterations": [item.model_dump() for item in iterations],
        "explain": explain,
        "tariff_dossier": dossier.model_dump() if dossier else None,
        "critic_outputs": [item.model_dump() for item in critics],
        "model_routing": model_routing,
    }


def _format_tariff_report(dossier: TariffDossier | None) -> str:
    if dossier is None:
        return ""
    baseline_rate = (
        f"{dossier.baseline.duty_rate_pct:.2f}%"
        if dossier.baseline.duty_rate_pct is not None
        else "unknown"
    )
    optimized_rate = (
        f"{dossier.optimized.duty_rate_pct:.2f}%"
        if dossier.optimized.duty_rate_pct is not None
        else "unknown"
    )
    lines = [
        "Baseline:",
        f"- HTS: {dossier.baseline.hts_code or 'unknown'}",
        f"- Duty rate: {baseline_rate} ({dossier.baseline.duty_basis})",
        f"- Rationale: {dossier.baseline.rationale}",
        "",
        "Optimized (golden scenario):",
        f"- Best option id: {dossier.best_option_id or 'none'}",
        f"- HTS: {dossier.optimized.hts_code or 'unknown'}",
        f"- Duty rate: {optimized_rate}",
        f"- Savings per unit: {dossier.optimized.estimated_savings_per_unit}",
        f"- Rationale: {dossier.optimized.rationale}",
        "",
        "Top mutations:",
    ]
    for mutation in dossier.mutations[:5]:
        lines.append(f"- {mutation.title}: {mutation.expected_effect}")
    if dossier.questions_for_user:
        lines.append("")
        lines.append("Questions for user:")
        for question in dossier.questions_for_user:
            lines.append(f"- {question}")
    return "\n".join(lines)


def _load_fixture() -> dict[str, Any] | None:
    if os.getenv("FAKE_LLM") != "1":
        return None
    fixture_path = os.getenv("TRUSTAI_TARIFF_FIXTURE")
    if fixture_path:
        path = Path(fixture_path)
    else:
        path = Path(__file__).resolve().parent / "fixtures" / "tariff_fixture.json"
    if not path.exists():
        return None
    return orjson.loads(path.read_bytes())


register_pack("tariff", lambda context: TariffPack(context))
