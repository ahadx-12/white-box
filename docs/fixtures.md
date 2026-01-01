# Fixtures (Week 1)

## Record a fixture (live mode)

1. Prepare an input payload JSON:

```json
{
  "input": "Describe the product and constraints...",
  "pack": "tariff",
  "options": { "max_iters": 4, "threshold": 0.92, "min_mutations": 8 },
  "evidence": ["optional evidence line"]
}
```

2. Run the recorder (requires live API keys in env):

```bash
python scripts/record_fixture.py --input path/to/input.json
```

The fixture is saved under:

```
storage/fixtures/recordings/<pack>/<case_id>_<timestamp>.json
```

## Replay fixtures (offline by default)

Replay all fixtures in the default directory (fixture mode):

```bash
python scripts/replay_fixtures.py
```

Replay a specific fixture:

```bash
python scripts/replay_fixtures.py --path storage/fixtures/recordings/tariff/example.json
```

Markdown reports are written to:

```
reports/dev/fixture_replay_<timestamp>.md
```

## Golden invariants compared

Replays compare only these invariants:

- Acceptance vs rejection.
- Final HTS code (or `allowed_codes` if present in the fixture).
- Duty rate and/or duty delta within ±0.05 percentage points.
- Critical tariff gates (GRI sequencing, essential character, ontology mutex, bounded what-ifs).
- Refusal category (when rejected).

Iteration counts, rationale text, critiques, and warning order are ignored.
