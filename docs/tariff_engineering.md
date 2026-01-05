# Tariff Engineering v2

This document describes the Week 6 Tariff Engineering v2 implementation: deterministic mutation operators, **constrained multi‑step beam search**, deduplicated state hashing, and stronger deterministic ranking for verified levers.

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

## Verified Lever Pipeline (v2)

The tariff pack now produces a **lever proof** payload using a constrained multi‑step search:

1. Generate operator candidates from the Product Dossier.
2. **Beam search** up to `max_depth` (default 2, optional 3) with deterministic ordering.
3. Apply early pruning (see below) before verification.
4. Verify the surviving candidates using existing gates:
   - citation gate
   - missing evidence gate
   - GRI sequence validation
5. Rank verified sequences deterministically and return top‑K.

### Search Strategy (Beam Search)

We use **beam search** for deterministic, bounded exploration:

- **Level 0**: baseline Product Dossier.
- **Level 1**: apply each operator once.
- **Level 2/3**: expand only the top `beam_width` candidates by heuristic score.
- Hard cap on `max_expansions` ensures no exponential explosion.

Beam search was chosen over best‑first because it is deterministic and easier to bound under strict depth/expansion limits.

### Deduplication + Canonical Hashing

Every mutated dossier is canonicalized and hashed to ensure deterministic dedup:

- Dictionaries sorted by key.
- Lists sorted only when order is semantically irrelevant:
  - `components` (sorted by name/type/material)
  - `upper_materials` / `outsole_materials` (sorted by material)
- Hash = sha256 of canonical JSON.

Identical states are **never re‑verified**, and dedup stats are recorded in the proof.

### Early Pruning & Conflict Rules

Candidates are pruned before verification if they fail any early checks:

- **Plausibility/Compliance gate** fails.
- **Missing evidence precheck** fails (chapter notes/headings not present).
- **Conflict detection** rules:
  - Same path replaced twice (`touch_paths` overlap).
  - `packaging.sold_as_set` flipped more than once.
  - Multiple component splits/merges in a sequence.
- **Optional proxy prune**: drop candidates with no plausible savings proxy.

Conflict reasons are deterministic and included in proof/debug output.

### Ranking (Deterministic)

Verified sequences are scored deterministically using:

- `duty_savings_pct` (if available)
- `cost_impact` penalty (if available)
- `risk_flags` penalties
- `gate_confidence` + `overall_score` bonuses

Tie‑breakers are deterministic via lexicographic `operator_id` sequences.

## Lever Proof Format

The tariff proof payload includes:

- `baseline_summary`
- `mutation_candidates` (accepted + rejected, with rejection reasons)
- `selected_levers` (top‑K)

Selected levers include:

- `sequence`: list of per‑step operator IDs, diffs, and compliance results
- `baseline_summary` vs `final` mutated summary
- `verification` (final grounded verification)
- `savings_estimate` + score
- `evidence_bundle` + `citations`
- `search_meta` (state hash + parent hashes)

The proof also includes:

- `search_summary` (depth, beam width, expanded/pruned counts)
- `rejected_sequences` (top‑N rejections with reasons)

## Tuning Beam Width/Depth Safely

- Keep `max_depth` at **2** by default; only use **3** for narrowly scoped domains.
- Increase `beam_width` slowly (e.g., 4 → 6) and monitor `max_expansions`.
- Always set `max_expansions` to cap total search work deterministically.

This ensures levers are auditable, lawful, and reproducible.
