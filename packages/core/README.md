# TrustAI Core

This package implements the Week-1 deterministic logic kernel for TrustAI VRP.

## Math summary

- Dimension `D = 10,000`
- Bipolar vectors in `{ -1, +1 }`
- Binding: elementwise multiplication
- Bundling: `sign(sum(vecs))` with deterministic tie-break (`0 -> +1`)
- Permutation: circular shift via `torch.roll`
- Similarity: cosine

## Running tests

```bash
python -m pytest -q
ruff check .
mypy packages/core/src/trustai_core
```
