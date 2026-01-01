from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import orjson
from pydantic import ValidationError

from trustai_core.llm.base import LLMClient, LLMError
from trustai_core.packs.registry import PackContext, register_pack
from trustai_core.packs.tariff.hdc import (
    HDCScore,
    build_composition_vector,
    bundle_tokens,
    compare_bundles,
    essential_character_score,
    normalize_component_name,
    tariff_mutex_sets,
)
from trustai_core.packs.tariff.models import (
    GriStep,
    GriTrace,
    WhatIfCandidate,
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
TARIFF_MIN_MUTATIONS_DEFAULT = 8
TARIFF_MAX_ITERS_CAP = 6
MAX_WHAT_IF_CANDIDATES = 5
ESSENTIAL_CHARACTER_MIN_SCORE = 0.58


@dataclass
class TariffOptions:
    max_iters: int = 4
    threshold: float = TARIFF_THRESHOLD_DEFAULT
    min_mutations: int = TARIFF_MIN_MUTATIONS_DEFAULT
    evidence: list[str] | None = None


class TariffPack:
    name = "tariff"

    def __init__(self, context: PackContext) -> None:
        self._context = context
        self.fingerprint = sha256_canonical_json(
            {"pack": self.name, "version": TARIFF_PACK_VERSION}
        )

    async def run(self, input_text: str, options: dict[str, object] | None) -> TariffVerificationResult:
        resolved_options = _resolve_options(options)
        evidence = resolved_options.evidence
        if self._context.llm_mode != "live":
            fixture = _load_fixture()
            if fixture:
                return await self._run_with_fixture(input_text, resolved_options, fixture)
            return _build_llm_error_result(
                input_text,
                self.name,
                self.fingerprint,
                "Fixture mode enabled but no tariff fixture was found.",
                evidence=evidence,
            )
        router = _select_router(self._context)
        if router.error:
            return _build_llm_error_result(
                input_text,
                self.name,
                self.fingerprint,
                router.error,
                evidence=evidence,
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
                        evidence,
                        _tariff_dossier_schema(),
                    )
                else:
                    prompt = build_tariff_proposal_prompt(
                        input_text,
                        feedback,
                        evidence,
                        _tariff_dossier_schema(),
                    )
                dossier = await router.proposer.complete_tariff(prompt)
                critique = await router.critic.complete_critique(
                    build_tariff_critic_prompt(
                        input_text,
                        dossier,
                        evidence,
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
                    min_mutations=resolved_options.min_mutations,
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
                evidence=evidence,
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
            evidence,
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
                evidence=options.evidence,
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
                min_mutations=options.min_mutations,
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
            options.evidence,
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
    max_iters = min(max_iters, TARIFF_MAX_ITERS_CAP)
    threshold = float(options.get("threshold") or TARIFF_THRESHOLD_DEFAULT)
    min_mutations = int(options.get("min_mutations") or TARIFF_MIN_MUTATIONS_DEFAULT)
    evidence_value = options.get("evidence")
    evidence: list[str] | None = None
    if isinstance(evidence_value, list):
        evidence = [str(item) for item in evidence_value]
    elif isinstance(evidence_value, str):
        evidence = [evidence_value]
    return TariffOptions(
        max_iters=max_iters,
        threshold=threshold,
        min_mutations=min_mutations,
        evidence=evidence,
    )


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
    evidence: list[str] | None = None,
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
        evidence,
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


@dataclass
class GateResult:
    rejected_because: list[str]
    missing: list[str]
    unsupported: list[str]
    conflicts: list[str]
    essential_character_score: float | None = None


ALLOWED_CATEGORIES = {
    "materials",
    "construction",
    "component",
    "process",
    "origin",
    "packaging",
    "use",
    "assembly",
    "documentation",
    "classification_argument",
}
ALLOWED_EXPECTED_EFFECTS = {"hts_change", "duty_rate_change", "unknown"}
ALLOWED_RISK_LEVELS = {"low", "med", "high"}
ILLEGAL_EVASION_TERMS = {
    "misdeclare",
    "fake",
    "falsify",
    "lie",
    "false invoice",
    "fraud",
    "evade",
    "evasion",
    "smuggle",
    "bribe",
}

GRI_ORDER = [
    GriStep.GRI_1,
    GriStep.GRI_2,
    GriStep.GRI_3,
    GriStep.GRI_4,
    GriStep.GRI_5,
    GriStep.GRI_6,
]


def validate_gri_sequence(gri_trace: GriTrace | None) -> tuple[bool, list[str]]:
    if gri_trace is None:
        return False, ["missing_gri_trace"]
    violations: list[str] = []
    if [step.step for step in gri_trace.steps] != GRI_ORDER:
        violations.append("GRI steps must be ordered GRI_1 through GRI_6")
    if gri_trace.step_vector and len(gri_trace.step_vector) != len(GRI_ORDER):
        violations.append("Step vector must include 6 entries")
    applied_indices = [i for i, step in enumerate(gri_trace.steps) if step.applied]
    if applied_indices:
        first_applied = applied_indices[0]
        for idx in range(first_applied):
            if gri_trace.steps[idx].applied:
                violations.append(
                    f"Sequence Violation: {gri_trace.steps[idx].step} applied before "
                    f"{gri_trace.steps[first_applied].step}"
                )
            if not gri_trace.steps[idx].rejected_because:
                violations.append(
                    f"Sequence Violation: {gri_trace.steps[first_applied].step} used before "
                    f"rejecting {gri_trace.steps[idx].step}"
                )
        for idx in range(first_applied + 1, len(gri_trace.steps)):
            if gri_trace.steps[idx].applied:
                violations.append(
                    f"Sequence Violation: {gri_trace.steps[idx].step} applied after "
                    f"{gri_trace.steps[first_applied].step}"
                )
    if gri_trace.step_vector:
        applied_vector = [step.applied for step in gri_trace.steps]
        if applied_vector != gri_trace.step_vector:
            violations.append("Step vector does not match applied steps")
    return (not violations), _cap_list(violations, 10)


def generate_perturbations(
    product_facts: dict[str, Any],
    constraints: list[str] | None,
) -> list[WhatIfCandidate]:
    candidates: list[WhatIfCandidate] = []
    composition = product_facts.get("composition_table") or []
    baseline_duty = product_facts.get("baseline_duty_rate_pct")
    constraints_list = constraints or []
    if composition:
        sorted_components = sorted(
            composition,
            key=lambda item: float(item.get("pct") or 0.0),
            reverse=True,
        )
        if len(sorted_components) >= 2:
            primary = sorted_components[0]
            secondary = sorted_components[1]
            primary_name = primary.get("name", "primary material")
            secondary_name = secondary.get("name", "secondary material")
            candidates.append(
                WhatIfCandidate(
                    mutation_id="whatif_material_flip",
                    change=(
                        f"Adjust composition so {secondary_name} reaches 51% "
                        f"and {primary_name} drops below 49%."
                    ),
                    rationale="Threshold flip may shift essential character and heading notes.",
                    expected_heading_shift="Potential shift to heading aligned with dominant material.",
                    estimated_duty_delta=-0.02 if baseline_duty else None,
                    legal_risks=[
                        "Requires lawful redesign and documented BOM changes.",
                        "May affect performance/compliance testing.",
                    ],
                    citations_required=True,
                    constraints=constraints_list,
                )
            )
    candidates.append(
        WhatIfCandidate(
            mutation_id="whatif_documentation_upgrade",
            change="Add detailed production records and product testing to support lawful reclassification.",
            rationale="Documentation can support a defensible classification argument.",
            expected_heading_shift="No direct shift; strengthens classification support.",
            estimated_duty_delta=None,
            legal_risks=["Must remain truthful and auditable."],
            citations_required=True,
            constraints=constraints_list,
        )
    )
    return candidates[:MAX_WHAT_IF_CANDIDATES]


def _detect_mutex_conflicts(labels: list[str]) -> list[str]:
    normalized = {normalize_component_name(label) for label in labels if label}
    conflicts: list[str] = []
    for group in tariff_mutex_sets():
        group_set = {normalize_component_name(item) for item in group}
        hits = sorted(group_set.intersection(normalized))
        if len(hits) > 1:
            conflicts.append(f"Mutually exclusive categories present: {', '.join(hits)}")
    return conflicts


def _evaluate_iteration(
    i: int,
    dossier: TariffDossier,
    critique: TariffCritique,
    previous_bundle: list[int] | None,
    previous_dossier: TariffDossier | None,
    threshold: float,
    min_mutations: int,
) -> tuple[TariffVerifyIteration, list[int], str]:
    rejected_because: list[str] = []
    gate = _gate_dossier(dossier, min_mutations)
    sequence_ok, sequence_violations = validate_gri_sequence(dossier.gri_trace)
    conflicts = sorted(set(critique.conflicts + gate.conflicts))
    unsupported = sorted(set(critique.unsupported + gate.unsupported))
    missing = sorted(set(critique.missing + gate.missing))
    rejected_because.extend(gate.rejected_because)
    if not sequence_ok:
        rejected_because.append("gri_sequence_violation")
        conflicts.extend(sequence_violations)

    baseline_duty = dossier.baseline.duty_rate_pct
    optimized_duty = dossier.optimized.duty_rate_pct

    if baseline_duty is None and not dossier.questions_for_user:
        rejected_because.append("baseline_duty_missing")

    if baseline_duty is not None and optimized_duty is not None:
        if dossier.best_option_id and optimized_duty > baseline_duty:
            rejected_because.append("optimized_duty_higher_than_baseline")

    has_lowering_option = _has_lowering_option(dossier)
    if not has_lowering_option and "cannot reduce" not in dossier.optimized.rationale.lower():
        rejected_because.append("no_lowering_option")

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

    mismatch_report = _build_mismatch_report(
        rejected_because,
        hdc,
        sequence_violations,
        gate.essential_character_score,
    )
    feedback_text = _build_feedback_text(
        rejected_because,
        critique,
        mismatch_report,
        _build_what_if_feedback(dossier, rejected_because),
    )
    answer_delta_summary = _summarize_dossier_delta(previous_dossier, dossier)
    conflicts = _cap_list(conflicts, 50)
    unsupported = _cap_list(unsupported, 50)
    missing = _cap_list(missing, 50)
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
        gri_trace=dossier.gri_trace,
        sequence_violations=sequence_violations,
        essential_character_score=(
            round(gate.essential_character_score, 6)
            if gate.essential_character_score is not None
            else None
        ),
    )
    return iteration, hdc_bundle, mismatch_report


def _gate_dossier(dossier: TariffDossier, min_mutations: int) -> GateResult:
    rejected_because: list[str] = []
    missing: list[str] = []
    unsupported: list[str] = []
    conflicts: list[str] = []
    essential_score: float | None = None

    hts_code = (dossier.baseline.hts_code or "").strip()
    if not hts_code or hts_code.lower() == "unknown":
        if len(dossier.questions_for_user) < 3:
            missing.append("questions_for_user (>=3 required when HTS unknown)")
            rejected_because.append("hts_or_questions_missing")

    if len(dossier.mutations) < min_mutations:
        if "cannot reduce" not in dossier.optimized.rationale.lower():
            missing.append(f"mutations (min {min_mutations})")
            rejected_because.append("insufficient_mutations")

    mutation_ids = {mutation.id for mutation in dossier.mutations if mutation.id}
    if not dossier.best_option_id or dossier.best_option_id not in mutation_ids:
        missing.append("best_option_id (must reference mutation id)")
        rejected_because.append("missing_best_option")

    for mutation in dossier.mutations:
        if not mutation.id:
            missing.append("mutation id")
            rejected_because.append("mutation_fields_incomplete")
        if mutation.category not in ALLOWED_CATEGORIES:
            unsupported.append(f"mutation {mutation.id} category '{mutation.category}' invalid")
            rejected_because.append("invalid_mutation_category")
        if mutation.expected_effect not in ALLOWED_EXPECTED_EFFECTS:
            unsupported.append(
                f"mutation {mutation.id} expected_effect '{mutation.expected_effect}' invalid"
            )
            rejected_because.append("invalid_mutation_expected_effect")
        if mutation.risk_level not in ALLOWED_RISK_LEVELS:
            unsupported.append(f"mutation {mutation.id} risk_level '{mutation.risk_level}' invalid")
            rejected_because.append("invalid_mutation_risk_level")
        if not mutation.required_evidence:
            missing.append(f"mutation {mutation.id} required_evidence")
            rejected_because.append("mutation_missing_evidence")
        if not mutation.rationale.strip():
            missing.append(f"mutation {mutation.id} rationale")
            rejected_because.append("mutation_missing_rationale")
        if not mutation.legal_rationale.strip():
            missing.append(f"mutation {mutation.id} legal_rationale")
            rejected_because.append("mutation_missing_legal_rationale")
        if _contains_illegal_terms(_mutation_text(mutation)):
            conflicts.append(f"mutation {mutation.id} contains illegal evasion suggestion")
            rejected_because.append("illegal_evasion_suggestion")
        if _is_origin_mutation(mutation):
            if not _contains_substantial_transformation(mutation):
                conflicts.append(
                    f"mutation {mutation.id} origin change without substantial transformation"
                )
                rejected_because.append("origin_without_substantial_transformation")

    has_precise_claim = any(
        [
            dossier.baseline.hts_code,
            dossier.baseline.duty_rate_pct is not None,
            dossier.optimized.hts_code,
            dossier.optimized.duty_rate_pct is not None,
        ]
    )
    if has_precise_claim and not dossier.citations and not dossier.assumptions:
        missing.append("citations or assumptions for precise claims")
        rejected_because.append("missing_citations_or_assumptions")

    if dossier.baseline.duty_rate_pct is not None and dossier.baseline.confidence >= 0.8:
        if not dossier.assumptions:
            missing.append("assumptions for high-confidence duty rate")
            rejected_because.append("high_confidence_without_assumptions")
        if not dossier.baseline.rationale.strip():
            missing.append("baseline rationale for high-confidence duty rate")
            rejected_because.append("high_confidence_missing_rationale")

    composition_payload = [item.model_dump() for item in dossier.composition_table]
    composition_vector = build_composition_vector(composition_payload)
    claim_components = [
        {"name": name, "pct": weight} for name, weight in dossier.essential_character.weights.items()
    ]
    claim_vector = build_composition_vector(claim_components)
    essential_score = essential_character_score(claim_vector, composition_vector)
    if essential_score < ESSENTIAL_CHARACTER_MIN_SCORE:
        conflicts.append(
            f"Essential Character Mismatch (score {essential_score:.2f} below threshold)"
        )
        rejected_because.append("essential_character_mismatch")

    mutex_conflicts = _detect_mutex_conflicts(
        [component.name for component in dossier.composition_table]
        + list(dossier.essential_character.weights.keys())
    )
    if mutex_conflicts:
        conflicts.extend(mutex_conflicts)
        rejected_because.append("ontology_mutex_conflict")

    if not dossier.compliance_notes:
        missing.append("compliance_notes")
        rejected_because.append("compliance_notes_missing")

    if dossier.what_if_candidates:
        if len(dossier.what_if_candidates) > MAX_WHAT_IF_CANDIDATES:
            missing.append(f"what_if_candidates (max {MAX_WHAT_IF_CANDIDATES})")
            rejected_because.append("too_many_what_if_candidates")
        for candidate in dossier.what_if_candidates:
            if not candidate.citations_required:
                missing.append(f"what_if {candidate.mutation_id} citations_required")
                rejected_because.append("what_if_citations_required")
            if _contains_illegal_terms(
                " ".join([candidate.change, candidate.rationale, " ".join(candidate.legal_risks)])
            ):
                conflicts.append(
                    f"what_if {candidate.mutation_id} contains illegal evasion suggestion"
                )
                rejected_because.append("illegal_evasion_suggestion")
    else:
        if dossier.baseline.duty_rate_pct and dossier.baseline.duty_rate_pct > 0:
            missing.append("what_if_candidates")
            rejected_because.append("missing_what_if_candidates")

    return GateResult(
        rejected_because=sorted(set(rejected_because)),
        missing=sorted(set(missing)),
        unsupported=sorted(set(unsupported)),
        conflicts=sorted(set(conflicts)),
        essential_character_score=essential_score,
    )


def _mutation_text(mutation: Any) -> str:
    parts = [
        mutation.title,
        mutation.category,
        mutation.change,
        mutation.expected_effect,
        mutation.expected_savings_note,
        mutation.rationale,
        mutation.legal_rationale,
        " ".join(mutation.constraints),
    ]
    return " ".join(part for part in parts if part)


def _contains_illegal_terms(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in ILLEGAL_EVASION_TERMS)


def _is_origin_mutation(mutation: Any) -> bool:
    if mutation.category == "origin":
        return True
    return "origin" in mutation.title.lower() or "origin" in mutation.change.lower()


def _contains_substantial_transformation(mutation: Any) -> bool:
    text = _mutation_text(mutation).lower()
    return "substantial transformation" in text


def _cap_list(items: list[str], limit: int) -> list[str]:
    return items[:limit]


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
        f"gri.final={dossier.gri_trace.final_step_used}",
    ]
    for assumption in dossier.assumptions:
        tokens.append(f"assumption={assumption}")
    for mutation in dossier.mutations:
        tokens.append(f"mutation={mutation.id}:{mutation.category}")
    for component in dossier.composition_table:
        tokens.append(f"component={component.name}:{component.pct or component.cost_pct or 0.0}")
    for candidate in dossier.what_if_candidates:
        tokens.append(f"whatif={candidate.mutation_id}")
    return sorted(tokens)


def _score_iteration(rejected_because: list[str], hdc_score: float) -> float:
    penalty = 0.0
    if rejected_because:
        penalty = 0.1 * len(set(rejected_because))
    score = max(0.0, 1.0 - penalty)
    return min(score, hdc_score)


def _build_mismatch_report(
    rejected_because: list[str],
    hdc: HDCScore,
    sequence_violations: list[str] | None = None,
    essential_score: float | None = None,
) -> str:
    reasons = ", ".join(rejected_because) if rejected_because else "none"
    sequence_note = ""
    if sequence_violations:
        sequence_note = f" GRI violations: {'; '.join(sequence_violations)}."
    essential_note = ""
    if essential_score is not None:
        essential_note = f" Essential character score={essential_score:.4f}."
    return (
        f"Rejected because: {reasons}. "
        f"HDC similarity={hdc.similarity:.4f}, drift={hdc.drift:.4f}."
        f"{essential_note}{sequence_note}"
    )


def _build_feedback_text(
    rejected_because: list[str],
    critique: TariffCritique,
    mismatch_report: str,
    what_if_feedback: str | None = None,
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
    if what_if_feedback:
        parts.append(what_if_feedback)
    if rejected_because:
        parts.append("Rejected: " + ", ".join(rejected_because))
    return "\n".join(parts)


def _build_what_if_feedback(dossier: TariffDossier, rejected_because: list[str]) -> str | None:
    if "missing_what_if_candidates" not in rejected_because:
        return None
    suggestions = generate_perturbations(
        {
            "composition_table": [item.model_dump() for item in dossier.composition_table],
            "baseline_duty_rate_pct": dossier.baseline.duty_rate_pct,
        },
        dossier.compliance_notes,
    )
    if not suggestions:
        return None
    lines = ["Provide what-if candidates; example levers:"]
    for candidate in suggestions:
        lines.append(f"- {candidate.mutation_id}: {candidate.change}")
    return "\n".join(lines)


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
    return items[:5]


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
    evidence: list[str] | None,
) -> dict[str, Any]:
    status = "verified" if iterations and iterations[-1].accepted else "failed"
    return {
        "status": status,
        "pack": pack,
        "pack_fingerprint": fingerprint,
        "evidence_manifest_hash": sha256_canonical_json(
            {"input": input_text, "evidence": evidence or []}
        ),
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
    llm_mode = os.getenv("TRUSTAI_LLM_MODE", "fixture").lower()
    if llm_mode == "mock":
        llm_mode = "fixture"
    if llm_mode != "fixture" and os.getenv("FAKE_LLM") != "1":
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
