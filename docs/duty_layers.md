# Duty Layers & Preference Programs (v0)

This document describes how deterministic duty layers and preference programs are applied for the
US and CA tariff packs. The goal is an auditable total duty rate with dated, local tables and
explicit assumptions.

## Layer data schema

Layer tables live under the jurisdiction pack rates directory:

- `storage/packs/tariff_us/rates/additional_duties.json`
- `storage/packs/tariff_ca/rates/surtaxes.json`

Each file is a JSON array of layer rules:

```json
[
  {
    "layer_id": "US.301.CN.V1",
    "type": "additional_duty",
    "pct": 25.0,
    "match": {
      "origin_countries": ["CN"],
      "line_prefixes": ["84", "85"]
    },
    "effective_from": "2019-09-01",
    "effective_to": null,
    "reason": "Section 301 additional duty (demo subset).",
    "source_id": "US.LAW.301.DEMO"
  }
]
```

Matching rules:

- `origin_countries` must contain the shipment origin country.
- `line_prefixes` may be a chapter (2-digit) or longer prefix; the line ID is normalized by
  removing dots before checking `startswith`.

## Effective date behavior

- `effective_date` is required for deterministic tests/fixtures.
- At runtime, if `effective_date` is not provided, the system defaults to **today**.
- A layer applies only when `effective_from <= effective_date <= effective_to` (if `effective_to`
  is present).

The effective date is recorded in `DutyBreakdown.effective_date`.

## Preference program application (v0)

Preference program rules are table-driven and stored locally:

- `storage/packs/tariff_us/rates/program_rules_usmca.json`
- `storage/packs/tariff_ca/rates/program_rules_cusma.json`

Preference rates are stored in:

- `storage/packs/tariff_us/rates/preferential_rates.json`
- `storage/packs/tariff_ca/rates/preferential_rates.json`

**ProgramResult** reports:

- `status`: `eligible | ineligible | unknown`
- `reason`: human-readable summary
- `missing_inputs`: list of required inputs when status is `unknown`
- `evidence`: rule IDs that triggered eligibility

### v0 rule behavior

Only a small demo subset of rules is implemented:

- **wholly obtained**: checks `origin_country` against program territory.
- **tariff shift**: checks final chapter and component chapters for a specific demo rule.

If required inputs are missing (e.g., BOM chapters or manufacturing steps), the result is
`unknown` and the missing inputs are recorded.

## Total duty formula

The total duty rate is deterministic and auditable:

```
if eligible:
  base = preferential_rate_pct
else:
  base = base_rate_pct

total_rate_pct = base
  + sum(applied_additional_duties.pct)
  + sum(applied_surtaxes.pct)
```

**v0 limitation:** preference eligibility does **not** suppress any additional duty/surtax layers
unless a future rule explicitly states otherwise.

## Extending safely

1. Add a new layer rule to the correct JSON table with a unique `layer_id` and date range.
2. Add/extend program rules by appending a new rule object with a unique `rule_id`.
3. Update or add benchmark cases in fixture mode that set `effective_date` explicitly.
4. Add unit tests for the new rules and expected total rates.

All changes are data-first and deterministic, with no runtime web calls.
