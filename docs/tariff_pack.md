# Tariff Pack (tariff)

## Overview
The tariff pack turns TrustAI into a tariff engineering assistant. It produces:
- Baseline classification + duty estimate + assumptions.
- Legal tariff engineering mutations with duty impact.
- A proof-driven GRI trace (steps 1–6) with step-vector sequencing.
- Essential character analysis (GRI 3(b)) with weighted composition vectors.
- Lawful what-if prototyping with quantified per-unit savings and constraints.
- A recommended optimized plan (“golden scenario”).
- A verification trace covering checks, missing inputs, and corrections.

## Calling the API
Use the existing `/v1/verify` endpoint and select the pack via header or body.

**Header example**:
```bash
curl -sSf https://<api>/v1/verify \
  -H "Content-Type: application/json" \
  -H "X-TrustAI-Pack: tariff" \
  -d '{"input":"Textile sneaker with rubber outsole"}'
```

**Body example**:
```json
{
  "input": "Textile sneaker with rubber outsole",
  "pack": "tariff",
  "options": {
    "max_iters": 4,
    "threshold": 0.92,
    "min_mutations": 8
  }
}
```

## Live mode
Fixture mode is the default. To run live LLM calls, set:
```bash
export TRUSTAI_LLM_MODE=live
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
```

## Recording a new fixture
Run the API locally and record a live response:
```bash
TRUSTAI_LLM_MODE=live \\
python scripts/record_tariff_fixture.py \\
  --prompt "Classify a textile sneaker with rubber outsole." \\
  --out apps/api/tests/fixtures/tariff_fixture.json
```
The recording script normalizes payloads, caps arrays (mutations, what-if candidates, GRI steps),
and strips timestamps for deterministic fixtures.

## Response highlights
The response stays backward compatible, with additional tariff details in the `proof` payload:
- `proof.tariff_dossier`: structured tariff dossier (baseline, mutations, optimized plan).
- `iterations[].hdc_score` / `iterations[].mismatch_report`: deterministic verifier signals.
- `proof.tariff_dossier.gri_trace`: ordered GRI trace with step vector + violations.
- `proof.tariff_dossier.essential_character`: weighted essential character assessment.
- `proof.tariff_dossier.what_if_candidates`: ranked, lawful engineering levers with per-unit deltas.
- `proof.critic_outputs`: critic findings per iteration.
- `proof.model_routing`: provider/model routing.
 - `proof.tariff_dossier.citations`: evidence citations for factual claims.

## Loop behavior
The tariff pack runs a propose → critique → verify → revise loop until the verifier accepts or `max_iters` is reached.
The deterministic verifier checks:
- Schema completeness and required fields.
- Minimum mutation coverage (>=5 or explicit “cannot reduce” rationale).
- Baseline vs optimized duty consistency.
- GRI step sequencing and step-vector alignment.
- Essential character mismatch against composition vectors.
- HDC drift across iterations.
- What-if candidate caps (<=5) and compliance phrasing.

## Known limitations
- No tariff RAG or external corpus yet; outputs rely on LLMs + heuristics.
- Origin/tariff-shift suggestions require documentary evidence; risk flags highlight uncertainty.
- If LLM providers are unavailable, the pack returns a structured failure with feedback.

## Improving results
Provide:
- Full BOM/material breakdown.
- Manufacturing steps and origin details.
- Value breakdown and HTS guess.
- Any certification or compliance constraints.
