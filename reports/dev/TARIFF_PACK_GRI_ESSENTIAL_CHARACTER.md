# Tariff Pack: GRI Sequencing, Essential Character, and What-Ifs

## New models
- `GriStep`, `GriStepResult`, `GriTrace` (ordered steps, step_vector, sequence violations).
- `CompositionComponent`, `EssentialCharacter` (weighted composition + GRI 3(b) basis).
- `WhatIfCandidate`, `SavingsEstimate` for lawful what-if prototyping output.

Paths:
- `packages/core/src/trustai_core/packs/tariff/models.py`
- `packages/core/src/trustai_core/packs/tariff/hdc.py`

## New tests
- `apps/api/tests/test_tariff_gri_sequence.py` validates sequence violations and correction in fixture mode.
- `apps/api/tests/test_tariff_essential_character.py` validates mismatch detection and correction.
- `apps/api/tests/test_tariff_whatif.py` validates ranked what-if candidates and savings formula presence.

Fixtures:
- `apps/api/tests/fixtures/tariff_gri_sequence_violation.json`
- `apps/api/tests/fixtures/tariff_essential_character_mismatch.json`
- `apps/api/tests/fixtures/tariff_whatif_threshold_flip.json`

## Verifier enforcement
- `validate_gri_sequence` in `packages/core/src/trustai_core/packs/tariff/pack.py` enforces ordered GRI 1→6,
  requires rejected_because for prior steps, and validates step_vector alignment. Violations trigger
  `gri_sequence_violation` rejection and are fed into the revision loop.
- `build_composition_vector` + `essential_character_score` in `packages/core/src/trustai_core/packs/tariff/hdc.py`
  compare claimed essential character weights to the weighted composition vector. Scores below the
  threshold are flagged as `essential_character_mismatch`, forcing correction in subsequent iterations.

## What-if integration
- The pack enforces a hard cap of 5 what-if candidates and requires compliance notes and lawful
  phrasing. Missing candidates generate feedback via a deterministic perturbation generator.
