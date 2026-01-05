from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from trustai_core.packs.tariff.evidence.models import EvidenceSource
from trustai_core.packs.tariff.gates.missing_evidence_gate import precheck_missing_evidence_gate
from trustai_core.packs.tariff.gates.plausibility_gate import run_plausibility_gate
from trustai_core.packs.tariff.models import TariffDossier
from trustai_core.packs.tariff.mutations.compose import can_compose
from trustai_core.packs.tariff.mutations.dedup import state_hash
from trustai_core.packs.tariff.mutations.models import (
    LeverVerificationSummary,
    MutationCandidate,
    MutationCandidateAudit,
    RejectedSequence,
    SearchSummary,
)
from trustai_core.packs.tariff.mutations.operators import MutationOperator
from trustai_core.packs.tariff.mutations.utils import apply_diff


@dataclass(frozen=True)
class SearchConfig:
    max_depth: int = 2
    beam_width: int = 4
    max_expansions: int = 40
    max_rejected_sequences: int = 8
    prune_no_gain: bool = True
    min_proxy_score: float = 0.05


@dataclass(frozen=True)
class SequenceCandidate:
    sequence: list[MutationCandidate]
    compliance_results: list[dict[str, Any]]
    dossier: Any
    state_hash: str
    parent_hashes: list[str]
    heuristic_score: float
    verification_summary: LeverVerificationSummary | None


@dataclass(frozen=True)
class SearchResult:
    sequences: list[SequenceCandidate]
    audits: list[MutationCandidateAudit]
    search_summary: SearchSummary
    rejected_sequences: list[RejectedSequence]


def run_beam_search(
    product_dossier: Any,
    tariff_dossier: TariffDossier,
    evidence_bundle: list[EvidenceSource],
    operators: list[MutationOperator],
    verifier: Callable[[TariffDossier, list[EvidenceSource]], LeverVerificationSummary],
    config: SearchConfig,
) -> SearchResult:
    max_depth = min(3, max(1, config.max_depth))
    beam_width = max(1, config.beam_width)
    max_expansions = max(1, config.max_expansions)

    audits: list[MutationCandidateAudit] = []
    rejected_sequences: list[RejectedSequence] = []
    sequences: list[SequenceCandidate] = []
    visited = 0
    expanded = 0
    pruned = 0
    dedup_hits = 0

    root_hash = state_hash(product_dossier)
    seen_states = {root_hash}
    unique = 1
    frontier = [
        SequenceCandidate(
            sequence=[],
            compliance_results=[],
            dossier=product_dossier,
            state_hash=root_hash,
            parent_hashes=[],
            heuristic_score=0.0,
            verification_summary=None,
        )
    ]

    for depth in range(1, max_depth + 1):
        next_candidates: list[SequenceCandidate] = []
        for node in frontier:
            if expanded >= max_expansions:
                break
            for candidate in _generate_candidates(node.dossier, operators):
                if expanded >= max_expansions:
                    break
                visited += 1
                ok, reason = can_compose(node.sequence, candidate)
                if not ok:
                    pruned += 1
                    _record_rejection(
                        rejected_sequences,
                        config.max_rejected_sequences,
                        node.sequence + [candidate],
                        reason or "conflict",
                        None,
                    )
                    continue

                compliance_result = run_plausibility_gate(candidate, node.dossier)
                if not compliance_result.ok:
                    pruned += 1
                    _record_rejection(
                        rejected_sequences,
                        config.max_rejected_sequences,
                        node.sequence + [candidate],
                        "plausibility_gate_failed",
                        None,
                    )
                    audits.append(
                        MutationCandidateAudit(
                            candidate=candidate,
                            compliance_gate_result=compliance_result.model_dump(),
                            verification_summary=None,
                            accepted=False,
                            rejection_reasons=list(compliance_result.violations),
                        )
                    )
                    continue

                missing_ok, missing_violations = precheck_missing_evidence_gate(
                    tariff_dossier,
                    evidence_bundle,
                )
                if not missing_ok:
                    pruned += 1
                    _record_rejection(
                        rejected_sequences,
                        config.max_rejected_sequences,
                        node.sequence + [candidate],
                        "missing_evidence_precheck",
                        None,
                    )
                    audits.append(
                        MutationCandidateAudit(
                            candidate=candidate,
                            compliance_gate_result=compliance_result.model_dump(),
                            verification_summary=None,
                            accepted=False,
                            rejection_reasons=missing_violations,
                        )
                    )
                    continue

                mutated = apply_diff(node.dossier, candidate)
                candidate_hash = state_hash(mutated)
                if candidate_hash in seen_states:
                    dedup_hits += 1
                    pruned += 1
                    _record_rejection(
                        rejected_sequences,
                        config.max_rejected_sequences,
                        node.sequence + [candidate],
                        "dedup_state",
                        candidate_hash,
                    )
                    continue

                heuristic_score = _heuristic_score(candidate, compliance_result.model_dump())
                if config.prune_no_gain and heuristic_score < config.min_proxy_score:
                    pruned += 1
                    _record_rejection(
                        rejected_sequences,
                        config.max_rejected_sequences,
                        node.sequence + [candidate],
                        "no_duty_proxy_gain",
                        candidate_hash,
                    )
                    continue

                seen_states.add(candidate_hash)
                unique += 1
                expanded += 1
                verification_summary = verifier(tariff_dossier, evidence_bundle)
                accepted = verification_summary.ok
                audits.append(
                    MutationCandidateAudit(
                        candidate=candidate,
                        compliance_gate_result=compliance_result.model_dump(),
                        verification_summary=verification_summary,
                        accepted=accepted,
                        rejection_reasons=list(verification_summary.rejected_because),
                    )
                )

                sequence = node.sequence + [candidate]
                compliance_results = node.compliance_results + [compliance_result.model_dump()]
                sequence_candidate = SequenceCandidate(
                    sequence=sequence,
                    compliance_results=compliance_results,
                    dossier=mutated,
                    state_hash=candidate_hash,
                    parent_hashes=node.parent_hashes + [node.state_hash],
                    heuristic_score=heuristic_score,
                    verification_summary=verification_summary,
                )
                if accepted:
                    sequences.append(sequence_candidate)
                next_candidates.append(sequence_candidate)

        frontier = _top_beam(next_candidates, beam_width)
        if not frontier:
            break

    search_summary = SearchSummary(
        max_depth=max_depth,
        beam_width=beam_width,
        max_expansions=max_expansions,
        visited=visited,
        expanded=expanded,
        pruned=pruned,
        unique=unique,
        dedup_hits=dedup_hits,
    )
    return SearchResult(
        sequences=sequences,
        audits=audits,
        search_summary=search_summary,
        rejected_sequences=rejected_sequences,
    )


def _generate_candidates(dossier: Any, operators: list[MutationOperator]) -> list[MutationCandidate]:
    candidates: list[MutationCandidate] = []
    for operator in sorted(operators, key=lambda item: item.operator_id):
        generated = operator.generate(dossier)
        candidates.extend(generated)
    return sorted(candidates, key=lambda item: item.operator_id)


def _heuristic_score(candidate: MutationCandidate, compliance_result: dict[str, Any]) -> float:
    score = 0.0
    for diff in candidate.diff:
        if "material_delta_pct" in diff.details:
            score += 0.1
        if "cost_delta_pct" in diff.details:
            score += 0.05
        if "components_split" in diff.details:
            score += 0.15
        if "chapter" in diff.path:
            score += 0.2
    if candidate.category in {"packaging", "assembly"}:
        score += 0.05
    risk_flags = compliance_result.get("risk_flags") or []
    score -= 0.05 * len(risk_flags)
    return round(max(0.0, score), 6)


def _top_beam(candidates: list[SequenceCandidate], beam_width: int) -> list[SequenceCandidate]:
    return sorted(
        candidates,
        key=lambda item: (-item.heuristic_score, _sequence_key(item.sequence)),
    )[:beam_width]


def _sequence_key(sequence: list[MutationCandidate]) -> str:
    return "|".join(candidate.operator_id for candidate in sequence)


def _record_rejection(
    rejected_sequences: list[RejectedSequence],
    limit: int,
    sequence: list[MutationCandidate],
    reason: str,
    state_hash: str | None,
) -> None:
    if len(rejected_sequences) >= limit:
        return
    rejected_sequences.append(
        RejectedSequence(
            sequence=[candidate.operator_id for candidate in sequence],
            reason=reason,
            state_hash=state_hash,
        )
    )
