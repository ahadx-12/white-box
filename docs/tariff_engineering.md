# Tariff Engineering v1

This document describes the Week 5 Tariff Engineering v1 implementation: deterministic mutation operators, a plausibility/compliance gate, and verified top‑K levers.

## Mutation Operator Framework

Mutation operators are deterministic transforms over a structured **Product Dossier** input JSON. Each operator only activates when its required inputs are present. Operators emit `MutationCandidate` objects with explicit, auditable metadata:

- `operator_id`, `label`, `category`
- `required_inputs`
- `diff` (structured product changes)
- `assumptions` and `bounds` (plausibility metadata)
- `compliance_framing` (explicit design/manufacturing framing)

Example candidate:

```json
{
  "operator_id": "op85_split_set_components",
  "category": "packaging",
  "label": "Separate set components into distinct retail items",
  "required_inputs": ["sold_as_set", "components"],
  "diff": [
    {"path": "packaging.sold_as_set", "from": true, "to": false},
    {"path": "components", "op": "split", "details": {"split_count": 2}}
  ],
  "assumptions": ["Items can be sold separately without changing consumer use."],
  "bounds": {"max_cost_delta": 0.20, "max_material_delta": 0.30},
  "compliance_framing": "Design/packaging change; not a declaration change."
}
```

Operators live in `packages/core/src/trustai_core/packs/tariff/mutations/operators.py` and cover chapters 64/73/84/85.

## Plausibility & Compliance Gate

The `PlausibilityComplianceGate` is deterministic and rejects candidates that:

- Only modify documentation/description fields.
- Contain evasion language (e.g., “misdeclare”, “evade”, “falsify”).
- Exceed configured bounds for material/cost delta or component removal.
- Contradict known product facts (e.g., claiming “no electronics” when electronics are present).
- Remove safety features when the product is marked safety footwear.

Gate output includes:

- `ok: bool`
- `violations: list[str]`
- `risk_flags: list[str]`
- `guidance: str`

Gate implementation: `packages/core/src/trustai_core/packs/tariff/gates/plausibility_gate.py`.

## Verified Lever Pipeline

The tariff pack now produces a **lever proof** payload:

1. Generate operator candidates from the Product Dossier.
2. Run the compliance gate.
3. Apply the diff to produce a mutated dossier.
4. Verify the mutated classification using the existing gates:
   - citation gate
   - missing evidence gate
   - GRI sequence validation
5. Rank accepted levers deterministically and return top‑K.

Ranking v1:

- Prefer `duty_savings` if duty rates are available.
- Otherwise use a proxy score based on plausibility deltas.
- Apply plausibility penalties and add gate confidence.

## Lever Proof Format

The tariff proof payload includes:

- `baseline_summary`
- `mutation_candidates` (accepted + rejected, with rejection reasons)
- `selected_levers` (top‑K)

Selected levers include:

- `candidate`
- `baseline_summary` vs `mutated_summary`
- `savings_estimate` + score
- `evidence_bundle` + `citations`
- `gate_results` (plausibility + verification)

This ensures levers are auditable, lawful, and reproducible.
