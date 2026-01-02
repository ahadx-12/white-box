from __future__ import annotations

import math
import re
from typing import Any

from trustai_core.benchmarks.models import BenchmarkCase, CaseScore, RefusalCategory
from trustai_core.fixtures.compare import TARIFF_CRITICAL_GATES

CHAPTER_MATCH_SCORE = 0.3
ALLOWED_MATCH_SCORE = 0.7
PREFERRED_MATCH_SCORE = 1.0
REFUSAL_MATCH_SCORE = 1.0
REFUSAL_MISMATCH_SCORE = 0.8
PROCESS_BONUS = 0.05
GRI_PENALTY = 0.1
DUTY_DELTA_PENALTY = 0.1


def _normalize_result(result: Any) -> dict[str, Any]:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, dict):
        return result
    return {}


def _extract_final_iteration(payload: dict[str, Any]) -> dict[str, Any] | None:
    iterations = payload.get("iterations") or []
    if iterations:
        return iterations[-1]
    proof = payload.get("proof") or {}
    proof_iterations = proof.get("iterations") or []
    if proof_iterations:
        return proof_iterations[-1]
    return None


def _extract_tariff_dossier(payload: dict[str, Any]) -> dict[str, Any] | None:
    proof = payload.get("proof") or {}
    return payload.get("tariff_dossier") or proof.get("tariff_dossier")


def _extract_final_hts(dossier: dict[str, Any] | None) -> str | None:
    if not dossier:
        return None
    optimized = dossier.get("optimized") or {}
    baseline = dossier.get("baseline") or {}
    return optimized.get("hts_code") or baseline.get("hts_code")


def _extract_duty_delta(dossier: dict[str, Any] | None) -> float | None:
    if not dossier:
        return None
    baseline = dossier.get("baseline") or {}
    optimized = dossier.get("optimized") or {}
    if baseline.get("duty_rate_pct") is None or optimized.get("duty_rate_pct") is None:
        return None
    return float(optimized.get("duty_rate_pct")) - float(baseline.get("duty_rate_pct"))


def _extract_sequence_ok(payload: dict[str, Any], dossier: dict[str, Any] | None) -> bool:
    iteration = _extract_final_iteration(payload) or {}
    sequence_violations = iteration.get("sequence_violations") or []
    if sequence_violations:
        return False
    if dossier:
        gri_trace = dossier.get("gri_trace") or {}
        sequence_ok = gri_trace.get("sequence_ok")
        if sequence_ok is not None:
            return bool(sequence_ok)
    return True


def _critical_gates_passed(rejected_because: list[str]) -> bool:
    return all(gate not in rejected_because for gate in TARIFF_CRITICAL_GATES)


def _extract_refusal_category(rejected_because: list[str]) -> RefusalCategory | None:
    if not rejected_because:
        return None
    insufficient_markers = {
        "hts_or_questions_missing",
        "baseline_duty_missing",
        "insufficient_mutations",
        "missing_best_option",
        "mutation_missing_evidence",
        "missing",
    }
    ambiguous_markers = {
        "gri_sequence_violation",
        "conflicts",
        "unsupported",
    }
    out_of_scope_markers = {
        "illegal_evasion_suggestion",
        "llm_unavailable",
    }
    for reason in rejected_because:
        if reason in insufficient_markers:
            return "insufficient_info"
        if reason in ambiguous_markers:
            return "ambiguous"
        if reason in out_of_scope_markers:
            return "out_of_scope"
    return "insufficient_info"


def _extract_chapter(hts_code: str | None) -> str | None:
    if not hts_code:
        return None
    digits = re.sub(r"\D", "", hts_code)
    if len(digits) < 2:
        return None
    return digits[:2]


def _check_no_savings(dossier: dict[str, Any] | None) -> bool:
    if not dossier:
        return True
    what_if_candidates = dossier.get("what_if_candidates") or []
    if what_if_candidates:
        return False
    baseline = dossier.get("baseline") or {}
    optimized = dossier.get("optimized") or {}
    baseline_rate = baseline.get("duty_rate_pct")
    optimized_rate = optimized.get("duty_rate_pct")
    if optimized.get("estimated_savings_per_unit") not in (None, 0, 0.0):
        return False
    if baseline_rate is not None and optimized_rate is not None:
        if float(optimized_rate) < float(baseline_rate):
            return False
    rationale = (optimized.get("rationale") or "").lower()
    if "cannot reduce" not in rationale and "no savings" not in rationale:
        return False
    mutations = dossier.get("mutations") or []
    for mutation in mutations:
        expected_rate = mutation.get("expected_duty_rate_pct")
        if expected_rate is not None and baseline_rate is not None:
            if float(expected_rate) < float(baseline_rate):
                return False
        savings_note = (mutation.get("expected_savings_note") or "").lower()
        if "no savings" in savings_note or "cannot reduce" in savings_note:
            continue
        if any(token in savings_note for token in ("savings", "reduce", "lower")):
            return False
    return True


def _clamp(score: float) -> float:
    return max(0.0, min(1.0, score))


def score_case(case: BenchmarkCase, result: Any) -> CaseScore:
    payload = _normalize_result(result)
    dossier = _extract_tariff_dossier(payload)
    final_iteration = _extract_final_iteration(payload) or {}
    rejected_because = list(final_iteration.get("rejected_because") or [])
    accepted = bool(final_iteration.get("accepted")) if final_iteration else False
    if not final_iteration:
        accepted = payload.get("status") == "verified"
    final_hts = _extract_final_hts(dossier)
    refusal_category = _extract_refusal_category(rejected_because)
    duty_delta = _extract_duty_delta(dossier)
    sequence_ok = _extract_sequence_ok(payload, dossier)
    critical_gates_ok = _critical_gates_passed(rejected_because)
    no_savings_ok = _check_no_savings(dossier)

    penalties: list[str] = []
    match_level: str | None = None
    score = 0.0
    process_bonus = 0.0

    if case.expected.expected_accept:
        if not accepted:
            penalties.append("unexpected_refusal")
            score = 0.0
        else:
            preferred = case.expected.preferred_hts
            allowed = case.expected.allowed_hts or []
            must_not = case.expected.must_not_hts or []
            if final_hts and final_hts in must_not:
                penalties.append("must_not_hts")
                score = 0.0
            elif final_hts in preferred:
                score = PREFERRED_MATCH_SCORE
                match_level = "preferred"
            elif final_hts in allowed:
                score = ALLOWED_MATCH_SCORE
                match_level = "allowed"
            else:
                preferred_chapters = {_extract_chapter(code) for code in preferred}
                if final_hts and _extract_chapter(final_hts) in preferred_chapters:
                    score = CHAPTER_MATCH_SCORE
                    match_level = "chapter"
                else:
                    score = 0.0
                    match_level = "miss"
            if case.expected.no_savings_expected and not no_savings_ok:
                penalties.append("no_savings_violation")
                score = 0.0

        if accepted:
            if critical_gates_ok:
                process_bonus += PROCESS_BONUS
            if not sequence_ok:
                penalties.append("gri_sequence_violation")
                score -= GRI_PENALTY
            if case.expected.duty_delta_range and duty_delta is not None:
                low, high = case.expected.duty_delta_range
                if not (low <= duty_delta <= high):
                    penalties.append("duty_delta_out_of_range")
                    score -= DUTY_DELTA_PENALTY

        score = _clamp(score + process_bonus)
    else:
        if accepted:
            penalties.append("unexpected_acceptance")
            score = 0.0
        else:
            if case.expected.expected_refusal_category:
                if refusal_category == case.expected.expected_refusal_category:
                    score = REFUSAL_MATCH_SCORE
                else:
                    penalties.append("refusal_category_mismatch")
                    score = REFUSAL_MISMATCH_SCORE
            else:
                score = REFUSAL_MATCH_SCORE

    threshold = 0.9 if not case.expected.expected_accept else 0.8
    passed = score >= threshold
    return CaseScore(
        case_id=case.id,
        score=round(score, 4),
        passed=passed,
        expected_accept=case.expected.expected_accept,
        actual_accept=accepted,
        match_level=match_level,
        final_hts=final_hts,
        refusal_category_expected=case.expected.expected_refusal_category,
        refusal_category_actual=refusal_category,
        duty_delta=None if duty_delta is None else round(float(duty_delta), 4),
        no_savings_ok=no_savings_ok if case.expected.no_savings_expected else None,
        process_bonus=round(process_bonus, 4),
        penalties=penalties,
    )
