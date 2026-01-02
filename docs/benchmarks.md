# Benchmarks

This repo includes an offline-friendly benchmark harness for pack verification, starting with
the **tariff** pack. The suite runs through the existing verification pipeline in either
fixture mode (default, offline) or live mode (optional, requires keys).

## Case schema

Each case is a JSON file with the following schema:

```json
{
  "id": "case_001_usb_cable",
  "pack_id": "tariff",
  "case_type": "positive|negative|adversarial|no_savings",
  "difficulty": "easy|medium|hard|expert",
  "input": { "input": "...", "options": { "max_iters": 4 }, "evidence": [] },
  "expected": {
    "preferred_hts": ["####.##.####"],
    "allowed_hts": ["####.##.####"],
    "must_not_hts": ["####.##.####"],
    "expected_accept": true,
    "expected_refusal_category": "insufficient_info|ambiguous|out_of_scope|null",
    "no_savings_expected": false,
    "duty_delta_range": [-0.01, 0.01]
  },
  "notes": {
    "source": "expert|synthetic|ruling:<id>|internal",
    "tags": ["chapter_85", "composite_good", "gri_3b"]
  }
}
```

Cases live under `storage/benchmarks/<suite>/cases/` and are grouped into subdirectories for
case type. Inputs should match the verify request schema (`input`, optional `options`,
optional `evidence`).

## Running benchmarks

Fixture mode (offline):

```bash
python scripts/run_benchmarks.py --suite tariff --mode fixture
```

Live mode (uses configured keys):

```bash
python scripts/run_benchmarks.py --suite tariff --mode live
```

Reports are written to `reports/benchmarks/`:

- JSON report (machine readable)
- Markdown report (summary)

## Scoring overview

Scoring uses partial credit:

- HTS exact match (preferred) = full credit
- Allowed HTS match = partial credit
- Chapter match (2-digit) = small partial credit
- `must_not_hts` = hard fail
- Refusal correctness for insufficient-info / negative cases
- `no_savings_expected` ensures the dossier does not include savings levers or what-if options
- Process quality bonuses/penalties:
  - bonus when critical gates pass on accepted outputs
  - penalty for GRI sequence violations

Final score is 0–1, with pass thresholds:

- Positive / no-savings cases: ≥ 0.8
- Negative cases: ≥ 0.9

## Comparing runs

Compare two JSON reports:

```bash
python scripts/compare_benchmarks.py --baseline <baseline.json> --current <current.json>
```

This writes a Markdown diff report to `reports/benchmarks/benchmark_diff_<timestamp>.md`
including improved/regressed cases, average score changes, and new failures.
