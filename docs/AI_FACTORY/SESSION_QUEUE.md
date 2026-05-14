# Session Queue

> Canonical next-session controller for AI agents. If a user says **"complete next session"**, execute the top-most session in this file whose status is `ready`.

## How to use this file

1. Read this file before choosing work.
2. Only execute the top-most `ready` session unless the user explicitly overrides the queue.
3. Treat `NEXT_PR_SEQUENCE.md` as the longer-range roadmap and this file as the single-session execution controller.
4. If the current session becomes blocked or partially completed, update this file, `HANDOFF.md`, and `SESSION_STATE.json` in the same PR.
5. If facts are missing, follow `FAILSAFE_RULES.md` instead of improvising.

## Current next session

### SESSION-001 — Implement audio plan + request loading primitives

- **Status:** `ready`
- **Task type:** `loader_parsing`
- **Objective:** Parse the committed example audio-plan and generation-request artifacts into typed runtime structures that future CLI/batch workflows can consume.
- **Why it matters:** This is the first step that turns the current docs/example layer into executable factory behavior.
- **Read first docs/files:**
  1. `docs/AI_FACTORY/SESSION_QUEUE.md`
  2. `docs/AI_FACTORY/CURRENT_STATE.md`
  3. `docs/AI_FACTORY/HANDOFF.md`
  4. `docs/AI_FACTORY/NEXT_PR_SEQUENCE.md`
  5. `docs/AI_FACTORY/NO_DECISION_ZONES.md`
  6. `docs/AI_FACTORY/FAILSAFE_RULES.md`
  7. `docs/AI_FACTORY/SCHEMAS/AUDIO_PLAN_SCHEMA.md`
  8. `docs/AI_FACTORY/SCHEMAS/GENERATION_REQUEST_SCHEMA.md`
  9. `docs/AI_FACTORY/EXAMPLES/gamerewritten_vertical_slice/README.md`
  10. `docs/AI_FACTORY/SUBSYSTEMS/ASSET_PIPELINE.md`
  11. `audio_engine/integration/asset_pipeline.py`
  12. `tests/test_integration.py`
- **Exact or likely files to modify:**
  - `audio_engine/integration/*` (add loader/parser support)
  - `audio_engine/cli.py` only if a validation/listing hook is required
  - `tests/test_integration.py`
  - `tests/test_engine_cli.py` or `tests/test_new_cli.py` only if CLI behavior changes
- **Files not to modify unless absolutely necessary:**
  - `audio_engine/dsp/*`
  - `audio_engine/render/*`
  - `audio_engine/composer/*`
  - `assets/schema/*`
  - `docs/AI_FACTORY/STYLES/*`
- **Verification commands:**
  - `pip install -e ".[dev]"`
  - `pytest`
  - `python tools/validate-assets.py assets/examples/ --verbose`
  - one focused loader smoke check against the committed example artifacts if a new CLI/API entry is added
- **Docs that must be updated:**
  - `docs/AI_FACTORY/CURRENT_STATE.md`
  - `docs/AI_FACTORY/ACTIVE_WORK.md`
  - `docs/AI_FACTORY/HANDOFF.md`
  - `docs/AI_FACTORY/CHANGE_JOURNAL.md`
  - `docs/AI_FACTORY/IMPLEMENTATION_MATRIX.md`
  - `docs/AI_FACTORY/SUBSYSTEMS/ASSET_PIPELINE.md`
  - `docs/AI_FACTORY/SESSION_QUEUE.md`
  - `docs/AI_FACTORY/SESSION_HISTORY.md`
  - `docs/AI_FACTORY/SESSION_STATE.json`
- **Explicit done criteria:**
  1. The committed example audio plan loads into a typed runtime structure.
  2. The committed music and SFX generation request examples load into typed runtime structures.
  3. Tests cover successful example ingestion and at least one invalid-input failure path.
  4. Existing CLI compatibility is preserved unless the session explicitly adds a new additive command.
  5. Docs are updated so implemented behavior is no longer described as docs-only in the affected areas.
- **Enqueue next session after completion:** `SESSION-002 — Add request-batch generation command`
- **If uncertain or blocked:**
  - do not invent unsupported schema fields
  - support the committed example artifacts first before generalizing
  - choose the smallest additive loader design that preserves current CLI behavior
  - record blockers in `HANDOFF.md`, `SESSION_QUEUE.md`, and `SESSION_STATE.json`

## Upcoming queued sessions

### SESSION-002 — Add request-batch generation command

- **Status:** `queued-after-SESSION-001`
- **Task type:** `batch_generation`
- **Short objective:** Execute music and SFX request files deterministically from the new loaders.

### SESSION-003 — Write provenance + review logs per request

- **Status:** `queued-after-SESSION-002`
- **Task type:** `provenance`
- **Short objective:** Persist request ID, seed, output path, and review state in machine-readable logs.

### SESSION-004 — Add batch QA gate command for generated outputs

- **Status:** `queued-after-SESSION-003`
- **Task type:** `qa`
- **Short objective:** Validate generated music/SFX sets with pass/fail reporting and reusable automation.
