# Tariff Pack Implementation Notes

## Repo orientation
- Core verification loop: `packages/core/src/trustai_core/orchestrator/loop.py`.
- Pack loader (ontology/axioms): `packages/core/src/trustai_core/packs/loader.py`.
- API verify endpoint: `apps/api/src/trustai_api/routes/verify.py`.
- Proof persistence: `apps/api/src/trustai_api/services/proof_store.py` + `apps/api/src/trustai_api/routes/proofs.py`.
- Async jobs: `apps/api/src/trustai_api/routes/jobs.py` + `apps/worker/src/trustai_worker/tasks.py`.

## Tariff pack wiring
- Pack registry + context: `packages/core/src/trustai_core/packs/registry.py`.
- Tariff pack module: `packages/core/src/trustai_core/packs/tariff/pack.py`.
- Tariff data models: `packages/core/src/trustai_core/packs/tariff/models.py`.
- HDC scoring: `packages/core/src/trustai_core/packs/tariff/hdc.py`.
- Prompts: `packages/core/src/trustai_core/packs/tariff/prompts.py`.
- API routing uses registry: `apps/api/src/trustai_api/services/verifier_service.py`.

## Pack selection
- `X-TrustAI-Pack: tariff` header or request body `pack: "tariff"`.
- Pack listed via `storage/packs/tariff` (empty ontology/axioms).

## Proof payload additions
- `tariff_dossier`, `critic_outputs`, `model_routing` are stored in `proof`.
- Iterations include `hdc_score` and `mismatch_report`.

## Tests
- Added deterministic fixture-driven tests in `apps/api/tests/test_tariff_pack.py`.
- Fixture used when `FAKE_LLM=1` and `TRUSTAI_TARIFF_FIXTURE` points to JSON.

## Live integration note
- A real LLM integration run was not executed in this environment due to missing API keys.
- When keys are available, set `TRUSTAI_LLM_MODE=live` and call `/v1/verify` with `X-TrustAI-Pack: tariff`.
