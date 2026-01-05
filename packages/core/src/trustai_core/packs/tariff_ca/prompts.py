from __future__ import annotations

from textwrap import dedent

from trustai_core.packs.tariff.evidence.models import EvidenceSource
from trustai_core.packs.tariff.models import TariffDossier


def build_tariff_proposal_prompt(
    input_text: str,
    feedback: str | None,
    evidence_bundle: list[EvidenceSource] | None,
    schema: dict,
) -> str:
    feedback_block = f"\n\nVerifier feedback:\n{feedback}\n" if feedback else ""
    evidence_block = _build_evidence_block(evidence_bundle)
    return dedent(
        f"""
        You are a tariff engineering assistant. Your job is to legally reduce duties while staying compliant.

        Input:
        {input_text}
        {feedback_block}{evidence_block}
        Requirements:
        - Output STRICT JSON that matches the provided schema. No extra keys.
        - Provide baseline classification + duty estimate + assumptions.
        - Use Canada Customs Tariff line format for hts_code entries.
        - Include candidate_chapters: a short list of 2-digit chapters considered (e.g., ["84","85"]).
        - Provide a GRI trace with steps 1→6 in order, each with applied yes/no, reasoning,
          rejected_because, citations, and a 6-length step_vector. Do NOT skip steps.
        - GRI 3 (incl. 3(b) essential character) can only be applied after rejecting GRI 1 & 2.
        - Provide a composition_table (percent/cost/weight breakdown) and essential_character analysis
          with basis, weights, conclusion, justification, and citations.
        - Generate at least 8 legal tariff engineering mutations if any plausible options exist.
        - Consider material substitutions, surface coverage changes (e.g., felt-sole),
          manufacturing steps/essential character, origin shifts (substantial transformation),
          packaging/set classification, documentation strategies, and tariff shift rules.
        - Each mutation MUST include: id, category, required_evidence, risk_level, expected_effect, rationale.
        - Categories must be one of: materials, construction, component, process, origin, packaging, use,
          assembly, documentation, classification_argument.
        - expected_effect must be one of: hts_change, duty_rate_change, unknown.
        - If reducing duty is not plausible, say so explicitly and explain why.
        - Include compliance constraints and risk flags for each mutation.
        - Provide 1–3 lawful what-if candidates (max 5) with per-unit duty deltas and constraints.
          Use compliance phrasing: lawful redesign, tariff engineering, documentation required.
          Never suggest evasion. Include citations_required=true for each candidate.
        - Provide compliance_notes that emphasize lawful redesign, documentation, and auditability.
        - Use numeric duty_rate_pct where possible; if unknown, set null and ask questions.
        - If the input includes flow fields (importing/exporting/origin/preference), reflect them in assumptions.
        - Every HTS code claim must include at least one citation with source_id and a verbatim quote.
        - Every GRI step must include at least one citation with source_id starting with GRI.*.
        - Essential character must cite either a chapter/section note or GRI.3.
        - If no evidence supports a factual claim, mark it as an assumption instead.
        - Output citations as objects: {{"claim_type": "...", "claim": "...", "source_id": "...", "quote": "..."}}.

        Return JSON only.
        Schema:
        {schema}
        """
    ).strip()


def build_tariff_critic_prompt(
    input_text: str,
    dossier: TariffDossier,
    evidence_bundle: list[EvidenceSource] | None,
    schema: dict,
) -> str:
    evidence_block = _build_evidence_block(evidence_bundle)
    return dedent(
        f"""
        You are a compliance critic. Review the proposed tariff dossier for unsupported claims,
        missing key facts, internal contradictions, or illegal/implausible suggestions.
        Specifically check GRI step sequencing and essential character basis (GRI 3(b)).

        Input:
        {input_text}
        {evidence_block}

        Proposed JSON:
        {dossier.model_dump_json()}

        Return STRICT JSON matching the schema. Focus on unsupported, missing, conflicts, and fixes.
        Schema:
        {schema}
        """
    ).strip()


def build_tariff_revision_prompt(
    input_text: str,
    dossier: TariffDossier,
    critique_payload: dict,
    mismatch_report: str,
    evidence_bundle: list[EvidenceSource] | None,
    schema: dict,
) -> str:
    evidence_block = _build_evidence_block(evidence_bundle)
    return dedent(
        f"""
        Revise the tariff dossier to address the critique and mismatch report.
        Output STRICT JSON matching the schema.
        Ensure GRI steps are sequenced 1→6 with an accurate step_vector and citations.
        Fix essential character analysis and composition_table if flagged.
        Provide lawful what-if candidates with quantified deltas and constraints.

        Input:
        {input_text}
        {evidence_block}

        Previous dossier:
        {dossier.model_dump_json()}

        Critique:
        {critique_payload}

        Mismatch report:
        {mismatch_report}

        Return JSON only.
        Schema:
        {schema}
        """
    ).strip()


def _build_evidence_block(evidence_bundle: list[EvidenceSource] | None) -> str:
    if not evidence_bundle:
        return ""
    evidence_lines = "\n".join(
        f"{idx + 1}. [{source.source_id}] ({source.source_type}) {source.text}"
        for idx, source in enumerate(evidence_bundle)
    )
    return f"\n\nEvidence bundle (cite using source_id):\n{evidence_lines}\n"
