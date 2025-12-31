# TrustAI Core

This package implements the Week-1 deterministic logic kernel for TrustAI VRP, plus the Week-2
LLM orchestration layer (agents + correction loop + proof traces).

## Math summary

- Dimension `D = 10,000`
- Bipolar vectors in `{ -1, +1 }`
- Binding: elementwise multiplication
- Bundling: `sign(sum(vecs))` with deterministic tie-break (`0 -> +1`)
- Permutation: circular shift via `torch.roll`
- Similarity: cosine

## Week-2 defaults

- similarity_threshold = `0.92`
- max_iters = `5`
- claim_support_threshold = `0.20`
- perceiver model = `gpt-4o-mini`
- reasoner model = `claude-3-5-sonnet-20241022`

## Demo

```bash
python scripts/run_week2_demo.py
```

Use `TRUSTAI_LIVE=1` to enable live OpenAI/Claude calls (requires env keys).

## Running tests

```bash
python -m pytest -q
ruff check .
mypy packages/core/src/trustai_core
```
