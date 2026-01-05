# Evidence Grounding (Tariff Pack)

This document explains the grounding implementation for the tariff pack: the local evidence corpus, deterministic retrieval rules, coverage rules, MissingEvidenceGate, and how to extend the corpus.

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
   - **Atomic bundling:** if any heading/subheading from a chapter is retrieved, include that chapter’s notes and its parent section notes.
   - If candidate chapters are provided (from the proposer or inferred), include the chapter notes and the mapped section notes for each candidate chapter.
   - If a chapter heading appears among the top retrieved headings, always include that chapter’s notes sources too.
4. **Top‑K selection** is applied after coverage and is deterministic (score desc, `source_id` tie‑break).

## MissingEvidenceGate (critical)
The `MissingEvidenceGate` (`packages/core/src/trustai_core/packs/tariff/gates/missing_evidence_gate.py`) rejects outputs that appear grounded but lack the required corpus coverage. It fails deterministically when:

- The final HTS chapter does not appear in any heading source in the evidence bundle.
- The evidence bundle is missing `CH{xx}.*` chapter notes for the final chapter.
- Critical citations (e.g., `hts_classification`, `essential_character`) cite unrelated chapters.
- The proposal claims a chapter note or exclusion without the corresponding note source in the bundle.

On failure, it emits revision guidance:
- `retrieve/attach missing chapter evidence: CHxx notes + headings`, or
- `request missing product facts needed to disambiguate chapters`.

## Candidate chapters in proof artifacts
The proof payload records:
- `candidate_chapters` (from the proposer or inferred)
- `candidate_chapter_evidence` (headings + notes included per candidate chapter)

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
4. Add the parent section notes if applicable (e.g., Section XVI for chapters 84/85).
5. Run tests:

```
python -m pytest -q
python scripts/run_benchmarks.py --suite tariff --mode fixture
```

**Example: adding Chapter 90**
1. Create `chapter_90_headings.json` with `HTS.90xx` headings.
2. Create `chapter_90_notes.json` with `CH90.NOTE*` sources.
3. Add section notes if needed (e.g., `section_xviii_notes.json` for Section XVIII).
4. Add benchmarks tagged `chapter_90` so fixture mode can map to a Chapter 90 fixture.
