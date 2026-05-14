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

## Recently completed sessions

### SESSION-001 — Implement audio plan + request loading primitives

- **Status:** `completed`
- **Task type:** `loader_parsing`
- **Result summary:** The committed example audio plan plus music/SFX request fixtures now load into typed runtime structures in `audio_engine/integration/factory_inputs.py`, with tests covering successful ingestion and an invalid-input failure path.

### SESSION-002 — Add request-batch generation command

- **Status:** `completed`
- **Task type:** `batch_generation`
- **Result summary:** `AssetPipeline.execute_request_batch()` and the `generate-request-batch` CLI command execute committed factory-input fixtures with per-request seeds explicit. `RequestBatchRecord` + `RequestBatchResult` provide machine-readable result capture. 11 new tests; 332 passed. Smoke run: SFX 5/5 OK, WAV music stinger OK.

## Current next session

### SESSION-003 — Write provenance + review logs per request

- **Status:** `ready`
- **Task type:** `provenance`
- **Objective:** Persist request ID, seed, output path, and review state in machine-readable logs for each generated asset.
- **Why it matters:** Enables deterministic re-generation, AI-readable audit trails, and downstream QA/review workflows.
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
  13. `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/review_log.example.v1.json`
  14. `audio_engine/integration/asset_pipeline.py`
  15. `audio_engine/cli.py`
  16. `tests/test_integration.py`
- **Exact or likely files to modify:**
  - `audio_engine/integration/asset_pipeline.py`
  - `audio_engine/cli.py`
  - `tests/test_integration.py`
- **Files not to modify unless absolutely necessary:**
  - `audio_engine/dsp/*`
  - `audio_engine/render/*`
  - `audio_engine/composer/*`
  - `assets/schema/*`
  - `docs/AI_FACTORY/STYLES/*`
  - `audio_engine/integration/factory_inputs.py` (loader contract is stable)
- **Verification commands:**
  - `pip install -e ".[dev]"`
  - `python -m pytest`
  - `python tools/validate-assets.py assets/examples/ --verbose`
  - one deterministic `/tmp` smoke run: run `generate-request-batch` and verify that a provenance log is written
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
  1. A provenance log (JSON) is written alongside or near each generated asset, containing at minimum: `request_id`, `seed`, `output_path`, `review_status`.
  2. The provenance log is stable across re-runs with the same seed.
  3. Tests cover the provenance log writer with at least one success path and one field-presence check.
  4. Existing CLI behavior for `generate-request-batch` is preserved or improved.
  5. Docs describe the new provenance behavior truthfully.
- **Enqueue next session after completion:** `SESSION-004 — Add batch QA gate command for generated outputs`
- **If uncertain or blocked:**
  - follow `docs/AI_FACTORY/BLOCKER_PROTOCOL.md`
  - use the committed `review_log.example.v1.json` as the schema reference
  - do not invent new schema fields beyond what the existing example specifies

## Upcoming queued sessions

### SESSION-004 — Add batch QA gate command for generated outputs

- **Status:** `queued-after-SESSION-003`
- **Task type:** `qa`
- **Short objective:** Validate generated music/SFX sets with pass/fail reporting and reusable automation.
