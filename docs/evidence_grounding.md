# Evidence Grounding (Tariff Pack)

This document explains the Week 3 grounding implementation for the tariff pack: the local evidence corpus, deterministic retrieval rules, citation schema, and how to extend the corpus.

## Evidence corpus format
Evidence sources live under:

```
storage/packs/tariff/evidence/sources/
```

Each JSON file contains an array of sources with this schema:

```json
{
  "source_id": "GRI.1",
  "source_type": "gri",
  "title": "General Rule of Interpretation 1",
  "effective_date": "2024-01-01",
  "url": null,
  "text": "..."
}
```

**Source ID conventions**
- GRI text: `GRI.1` .. `GRI.6`
- Headings/subheadings: `HTS.6402`, `HTS.6402.99`
- Chapter notes: `CH64.NOTE4`
- Section notes: `SEC12.NOTE1`

## Deterministic retrieval rules
Retrieval is implemented in `packages/core/src/trustai_core/packs/tariff/evidence/retrieve.py`:

1. **Tokenize** the product description into keywords (case-insensitive).
2. **Score** sources by keyword overlap.
3. **Coverage rules**
   - Always include all GRI sources (GRI.1–GRI.6).
   - If any heading/subheading matches strongly, include all notes for that chapter.
   - If candidate chapters are provided, include the chapter notes and the mapped section notes.
4. **Top‑K selection** is applied after coverage and is deterministic (score desc, `source_id` tie‑break).

## Citation rules enforced by CitationGate
The `CitationGate` (`packages/core/src/trustai_core/packs/tariff/gates/citation_gate.py`) enforces:

- **Critical claims require citations**:
  - `hts_classification`
  - `gri_application` (each GRI step must cite `GRI.*`)
  - `essential_character` (must cite `GRI.3` or a note source)
- **Cited `source_id` must exist** in the evidence bundle.
- **Quoted text must match** a verbatim substring in the cited source text.

Citation objects must follow:

```json
{
  "claim_type": "gri_application",
  "claim": "GRI 3(b) essential character analysis.",
  "source_id": "GRI.3",
  "quote": "material or component which gives them their essential character."
}
```

## Extending the corpus
1. Add a new JSON file or extend an existing one under `storage/packs/tariff/evidence/sources/`.
2. Use **stable, human‑readable `source_id` values**.
3. Include authoritative text in the `text` field.
4. Run tests:

```
python -m pytest -q
python scripts/run_benchmarks.py --suite tariff --mode fixture
```
