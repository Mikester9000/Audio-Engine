# Session Queue

> Canonical next-session controller for AI agents. If a user says **"complete next session"**, execute the top-most session in this file whose status is `ready`.

## How to use this file

1. Read this file before choosing work.
2. Only execute the top-most `ready` session unless the user explicitly overrides the queue.
3. Treat `NEXT_PR_SEQUENCE.md` as the longer-range roadmap and this file as the single-session execution controller.
4. Treat `CURRENT_SESSION.json` as the detailed machine-readable companion to this file for the single active session.
5. Before marking work done, satisfy `SESSION_GATE_RULES.md` and the relevant profile in `VERIFICATION_PROFILES.md`.
6. If the current session becomes blocked or partially completed, update this file, `HANDOFF.md`, `SESSION_STATE.json`, and `CURRENT_SESSION.json` in the same PR.
7. If facts are missing, follow `BLOCKER_PROTOCOL.md` and `FAILSAFE_RULES.md` instead of improvising.

## Recently completed session

### SESSION-001 — Implement audio plan + request loading primitives

- **Status:** `completed`
- **Task type:** `loader_parsing`
- **Result summary:** The committed example audio plan plus music/SFX request fixtures now load into typed runtime structures in `audio_engine/integration/factory_inputs.py`, with tests covering successful ingestion and an invalid-input failure path.

## Current next session

### SESSION-002 — Add request-batch generation command

- **Status:** `ready`
- **Task type:** `batch_generation`
- **Objective:** Execute the committed music and SFX generation-request batches deterministically through an additive CLI/API path that uses the new typed loaders.
- **Why it matters:** This turns the newly loaded factory-input artifacts into practical reproducible output generation for the game-audio workflow.
- **Read first docs/files:**
  1. `docs/AI_FACTORY/SESSION_QUEUE.md`
  2. `docs/AI_FACTORY/CURRENT_STATE.md`
  3. `docs/AI_FACTORY/HANDOFF.md`
  4. `docs/AI_FACTORY/NEXT_PR_SEQUENCE.md`
  5. `docs/AI_FACTORY/CURRENT_SESSION.json`
  6. `docs/AI_FACTORY/SESSION_GATE_RULES.md`
  7. `docs/AI_FACTORY/BLOCKER_PROTOCOL.md`
  8. `docs/AI_FACTORY/VERIFICATION_PROFILES.md`
  9. `docs/AI_FACTORY/NO_DECISION_ZONES.md`
  10. `docs/AI_FACTORY/FAILSAFE_RULES.md`
  11. `docs/AI_FACTORY/MINIMUM_TEST_EXPANSION_RULES.md`
  12. `docs/AI_FACTORY/SCHEMAS/GENERATION_REQUEST_SCHEMA.md`
  13. `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/README.md`
  14. `docs/AI_FACTORY/SUBSYSTEMS/ASSET_PIPELINE.md`
  15. `audio_engine/integration/factory_inputs.py`
  16. `audio_engine/integration/asset_pipeline.py`
  17. `audio_engine/cli.py`
  18. `tests/test_integration.py`
  19. `tests/test_engine_cli.py`
- **Exact or likely files to modify:**
  - `audio_engine/cli.py`
  - `audio_engine/integration/asset_pipeline.py`
  - `audio_engine/integration/factory_inputs.py` only if a small compatibility hook is required
  - `tests/test_integration.py`
  - `tests/test_engine_cli.py`
- **Files not to modify unless absolutely necessary:**
  - `audio_engine/dsp/*`
  - `audio_engine/render/*`
  - `audio_engine/composer/*`
  - `assets/schema/*`
  - `docs/AI_FACTORY/STYLES/*`
- **Verification commands:**
  - `pip install -e ".[dev]"`
  - `python -m pytest`
  - `python tools/validate-assets.py assets/examples/ --verbose`
  - one deterministic `/tmp` smoke run using the committed generation-request fixtures
- **Docs that must be updated:**
  - `docs/AI_FACTORY/CURRENT_STATE.md`
  - `docs/AI_FACTORY/ACTIVE_WORK.md`
  - `docs/AI_FACTORY/HANDOFF.md`
  - `docs/AI_FACTORY/CHANGE_JOURNAL.md`
  - `docs/AI_FACTORY/IMPLEMENTATION_MATRIX.md`
  - `docs/AI_FACTORY/SUBSYSTEMS/ASSET_PIPELINE.md`
  - `docs/AI_FACTORY/SESSION_QUEUE.md`
  - `docs/AI_FACTORY/SESSION_HISTORY.md`
  - `docs/AI_FACTORY/CURRENT_SESSION.json`
  - `docs/AI_FACTORY/SESSION_STATE.json`
- **Explicit done criteria:**
  1. One additive CLI or API path executes at least the committed music and SFX request-batch fixtures.
  2. Deterministic seeds remain explicit and are passed through the execution path.
  3. Tests cover the new request-batch generation path.
  4. Existing one-off CLI behavior remains compatible.
  5. Docs describe the new batch-generation behavior truthfully without overstating provenance or QA automation.
- **Enqueue next session after completion:** `SESSION-003 — Write provenance + review logs per request`
- **If uncertain or blocked:**
  - follow `docs/AI_FACTORY/BLOCKER_PROTOCOL.md`
  - do not invent unsupported schema fields or downstream import guarantees
  - support the committed example request fixtures first before generalizing
  - choose the smallest additive execution path that preserves current CLI behavior
  - record blockers in `HANDOFF.md`, `SESSION_QUEUE.md`, `SESSION_STATE.json`, and `CURRENT_SESSION.json`

## Upcoming queued sessions

### SESSION-003 — Write provenance + review logs per request

- **Status:** `queued-after-SESSION-002`
- **Task type:** `provenance`
- **Short objective:** Persist request ID, seed, output path, and review state in machine-readable logs.

### SESSION-004 — Add batch QA gate command for generated outputs

- **Status:** `queued-after-SESSION-003`
- **Task type:** `qa`
- **Short objective:** Validate generated music/SFX sets with pass/fail reporting and reusable automation.
