from __future__ import annotations

from textwrap import dedent

from trustai_core.packs.tariff.models import TariffDossier


def build_tariff_proposal_prompt(
    input_text: str,
    feedback: str | None,
    evidence: list[str] | None,
    schema: dict,
) -> str:
    feedback_block = f"\n\nVerifier feedback:\n{feedback}\n" if feedback else ""
    evidence_block = ""
    if evidence:
        evidence_lines = "\n".join(
            f"- evidence[{idx}]: {item}" for idx, item in enumerate(evidence)
        )
        evidence_block = f"\n\nEvidence (cite by index):\n{evidence_lines}\n"
    return dedent(
        f"""
        You are a tariff engineering assistant. Your job is to legally reduce duties while staying compliant.

        Input:
        {input_text}
        {feedback_block}{evidence_block}
        Requirements:
        - Output STRICT JSON that matches the provided schema. No extra keys.
        - Provide baseline classification + duty estimate + assumptions.
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
        - Use numeric duty_rate_pct where possible; if unknown, set null and ask questions.
        - If you make specific factual claims (exact HTS/duty), include citations with short quotes
          (<=25 words) and reference evidence index. If no evidence supports the claim, mark it
          as an assumption.
        - Output citations as objects: {{"evidence_index": 0, "quote": "...", "claim": "..."}}.

        Return JSON only.
        Schema:
        {schema}
        """
    ).strip()


def build_tariff_critic_prompt(
    input_text: str,
    dossier: TariffDossier,
    evidence: list[str] | None,
    schema: dict,
) -> str:
    evidence_block = ""
    if evidence:
        evidence_lines = "\n".join(
            f"- evidence[{idx}]: {item}" for idx, item in enumerate(evidence)
        )
        evidence_block = f"\n\nEvidence (cite by index):\n{evidence_lines}\n"
    return dedent(
        f"""
        You are a compliance critic. Review the proposed tariff dossier for unsupported claims,
        missing key facts, internal contradictions, or illegal/implausible suggestions.

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
    evidence: list[str] | None,
    schema: dict,
) -> str:
    evidence_block = ""
    if evidence:
        evidence_lines = "\n".join(
            f"- evidence[{idx}]: {item}" for idx, item in enumerate(evidence)
        )
        evidence_block = f"\n\nEvidence (cite by index):\n{evidence_lines}\n"
    return dedent(
        f"""
        Revise the tariff dossier to address the critique and mismatch report.
        Output STRICT JSON matching the schema.

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
