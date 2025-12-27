# AGENT.md

## What we’re building
A modular **verification + correction** middleware called **TrustAI VRP**.

It sits between a client and LLMs:
- The client calls **our API**
- We call OpenAI/Claude
- We run a **deterministic local verifier**
- We either **accept** the answer (verified) or **force iterations** until it becomes consistent
- We return the final answer **plus a proof/explain payload** (why it was accepted, what changed, what conflicts were found)

LLMs are **untrusted generators**. The verifier is the **trusted judge**.

---

## Your role (how to behave)
You are an implementation agent working inside this repo.

For every task you receive:
1) Implement exactly what’s requested.
2) Keep the repo clean and modular.
3) Add/extend tests so the change is provably correct.
4) Ensure everything is deterministic and replayable.
5) Do not log or print secrets.

Assume you can code anything, but you need explicit math/structure when it matters.

---

## Core principles
- **Deterministic verifier:** same inputs/config → same outputs (ordering, hashes, scores).
- **Correction loop:** verification is useless unless the system can *fix* and retry.
- **Proof-first outputs:** each run produces a structured proof/explain object for debugging and audits.
- **Pack selection:** jurisdiction/domain is selected via a pack name (e.g., “general”, “canada-criminal-code”) which loads axioms + ontology.

---

## Repository expectations
Keep code grouped by responsibility:
- `packages/core` = all deterministic math, encoders, pack loading, arbiter evaluation, loop logic, schemas.
- `apps/api` = FastAPI proxy endpoints + persistence + async jobs (later).
- `apps/dashboard` = chat UI + proof panel that calls our API (later).
- `storage/packs` = domain packs (axioms + ontology).

Do not mix network/LLM code into deterministic core modules unless explicitly requested.

---

## Output expectations
When implementing a task, you must:
- Create/modify the correct files under the correct folders.
- Add tests for new behavior.
- Run the test suite and fix failures.
- End with:
  - a brief file list of what changed
  - the commands to run tests/lint
  - a short “what’s next” note if relevant

---

## Safety and secrets
- Never print environment secrets (OPEN_AI_KEY, CLAUD_AI_KEY).
- Don’t hardcode keys anywhere.
- Don’t add network calls to unit tests.

---

## Definition of done
A task is done only when:
- the requested feature exists,
- tests for it exist and pass,
- code is clean and modular,
- outputs are deterministic/replayable,
- no secrets are exposed.

