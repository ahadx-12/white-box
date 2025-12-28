from __future__ import annotations

import json

ATOM_MANIFEST_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "atoms": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "predicate": {"type": "string"},
                    "obj": {"type": "string"},
                    "is_true": {"type": "boolean"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "type": {"type": "string", "enum": ["fact", "norm", "assumption"]},
                    "source_span": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "integer", "minimum": 0},
                            "end": {"type": "integer", "minimum": 0},
                        },
                        "required": ["start", "end"],
                    },
                },
                "required": ["subject", "predicate", "obj", "is_true", "confidence"],
            },
        }
    },
    "required": ["atoms"],
}


def _schema_block() -> str:
    return json.dumps(ATOM_MANIFEST_SCHEMA, indent=2, sort_keys=True)


def build_evidence_prompt(text: str) -> str:
    instruction = (
        "You are an extraction agent. Extract evidence atoms from the user text. "
        "Return JSON only that matches the schema. Normalize tokens to lowercase and underscores. "
        "Include confidence between 0 and 1 and optional source_span indices."
    )
    return (
        f"{instruction}\n\n"
        f"User text:\n{text}\n\n"
        f"Schema:\n{_schema_block()}"
    )


def build_claim_prompt(answer: str) -> str:
    instruction = (
        "You are an extraction agent. Extract claim atoms from the answer text. "
        "Return JSON only that matches the schema. Normalize tokens to lowercase and underscores. "
        "Include confidence between 0 and 1 and optional source_span indices."
    )
    return (
        f"{instruction}\n\n"
        f"Answer text:\n{answer}\n\n"
        f"Schema:\n{_schema_block()}"
    )


def build_reasoner_prompt(
    user_text: str,
    evidence_block: str | None = None,
    feedback_block: str | None = None,
) -> str:
    parts = [
        "You are a careful reasoning assistant.",
        "Answer the user query directly and concisely.",
        "Use the evidence atoms if provided.",
        "Do not include JSON.",
        "",
        "User query:",
        user_text,
    ]
    if evidence_block:
        parts.extend(["", "Evidence atoms:", evidence_block])
    if feedback_block:
        parts.extend(["", "Verifier feedback:", feedback_block])
    return "\n".join(parts)
