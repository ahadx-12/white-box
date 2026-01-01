from __future__ import annotations

from textwrap import dedent

from trustai_core.packs.tariff.models import TariffDossier


def build_tariff_proposal_prompt(
    input_text: str,
    feedback: str | None,
    schema: dict,
) -> str:
    feedback_block = f"\n\nVerifier feedback:\n{feedback}\n" if feedback else ""
    return dedent(
        f"""
        You are a tariff engineering assistant. Your job is to legally reduce duties while staying compliant.

        Input:
        {input_text}
        {feedback_block}
        Requirements:
        - Output STRICT JSON that matches the provided schema. No extra keys.
        - Provide baseline classification + duty estimate + assumptions.
        - Generate at least 5 legal tariff engineering mutations if any plausible options exist.
        - Consider material substitutions, surface coverage changes (e.g., felt-sole),
          manufacturing steps/essential character, origin shifts (substantial transformation),
          packaging/set classification, documentation strategies, and tariff shift rules.
        - If reducing duty is not plausible, say so explicitly and explain why.
        - Include compliance constraints and risk flags for each mutation.
        - Use numeric duty_rate_pct where possible; if unknown, set null and ask questions.

        Return JSON only.
        Schema:
        {schema}
        """
    ).strip()


def build_tariff_critic_prompt(
    input_text: str,
    dossier: TariffDossier,
    schema: dict,
) -> str:
    return dedent(
        f"""
        You are a compliance critic. Review the proposed tariff dossier for unsupported claims,
        missing key facts, internal contradictions, or illegal/implausible suggestions.

        Input:
        {input_text}

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
    schema: dict,
) -> str:
    return dedent(
        f"""
        Revise the tariff dossier to address the critique and mismatch report.
        Output STRICT JSON matching the schema.

        Input:
        {input_text}

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
