# Jurisdiction Packs

## Rationale for the pack split
The tariff verifier now supports jurisdiction-aware packs so that evidence corpora, duty lookups,
and program eligibility scaffolding can evolve independently. The `tariff_us` and `tariff_ca`
packs share the same verification loop and gates, but load their own evidence sources and
duty calculators.

## Flow-aware input fields
Tariff packs accept flow fields embedded in the `input` JSON payload. The recommended shape is:

```json
{
  "product_dossier": {
    "product_summary": "USB-C insulated charging cable with molded connectors."
  },
  "importing_country": "US",
  "exporting_country": "CN",
  "origin_country": "CN",
  "origin_method": null,
  "preference_program": null
}
```

These fields are recorded in the proof payload under `flow`.

## Evidence corpora layout
Evidence sources are deterministic JSON records shared via the same schema:

```
storage/packs/
  tariff_us/
    evidence/sources/*.json
  tariff_ca/
    evidence/sources/*.json
```

Sources are prefixed to prevent cross-jurisdiction leakage (e.g., `US.GRI.1`, `CA.TAR.6404`).
Retrievers always include GRI sources and automatically pull chapter/section notes when
headings are retrieved.

## Duty calculator interface
The core duty interface lives in `packages/core/src/trustai_core/duty/` and exposes:

```
DutyBreakdown = {
  base_rate_pct,
  preferential_rate_pct?,
  additional_duties[],
  surtaxes[],
  total_rate_pct,
  assumptions[]
}
```

Each jurisdiction pack implements its own calculator:

- `tariff_us`: `USDutyCalculator` reads `storage/packs/tariff_us/rates/*`.
- `tariff_ca`: `CADutyCalculator` reads `storage/packs/tariff_ca/rates/*`.

## Adding a new jurisdiction pack
1. Create a new pack directory under `storage/packs/<pack_id>/` with `axioms.json`, `ontology.json`,
   and `evidence/sources/*.json`.
2. Add jurisdiction-specific rate tables under `storage/packs/<pack_id>/rates/`.
3. Implement a duty calculator in `packages/core/src/trustai_core/packs/<pack_id>/duty/`.
4. Add a pack module in `packages/core/src/trustai_core/packs/<pack_id>/pack.py` that:
   - Loads the evidence store for the new pack.
   - Applies the duty calculator to baseline/optimized classifications.
   - Registers the pack via `register_pack("<pack_id>", ...)`.
5. Duplicate benchmark cases into `storage/benchmarks/<pack_id>/cases` and fixtures into
   `storage/benchmarks/<pack_id>/fixtures`.
6. Add unit tests for routing, duty calculator output, and benchmark fixture runs.
