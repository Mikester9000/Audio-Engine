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
- **Result summary:** `RequestBatchPipeline` added to `audio_engine/integration/asset_pipeline.py`; `generate-request-batch` CLI command added to `audio_engine/cli.py`. Both committed music (4 requests) and SFX (5 requests) fixtures execute deterministically with per-request seeds captured in `batch_manifest.json`. 13 new tests added; 334 total passed.

## Current next session

### SESSION-003 — Write provenance + review logs per request

- **Status:** `ready`
- **Task type:** `provenance`
- **Objective:** Persist request ID, seed, output path, backend, and review state in a machine-readable per-request provenance log alongside each generated batch output.
- **Why it matters:** Without per-request provenance, regeneration decisions and review continuity rely on `batch_manifest.json` summaries only; a per-request log makes each asset independently traceable.
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
  14. `docs/AI_FACTORY/CANONICAL_OUTPUT_LAYOUT.md`
  15. `audio_engine/integration/factory_inputs.py`
  16. `audio_engine/integration/asset_pipeline.py`
  17. `audio_engine/cli.py`
  18. `tests/test_integration.py`
- **Exact or likely files to modify:**
  - `audio_engine/integration/asset_pipeline.py`
  - `audio_engine/cli.py` (if a `--provenance-dir` flag is appropriate)
  - `tests/test_integration.py`
- **Files not to modify unless absolutely necessary:**
  - `audio_engine/dsp/*`
  - `audio_engine/render/*`
  - `audio_engine/composer/*`
  - `assets/schema/*`
  - `audio_engine/integration/factory_inputs.py` (unless a tiny hook is needed)
- **Verification commands:**
  - `pip install -e ".[dev]"`
  - `python -m pytest`
  - `python tools/validate-assets.py assets/examples/ --verbose`
  - one deterministic `/tmp` smoke run confirming per-request provenance files are written alongside generated audio
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
  1. Every request in a batch produces a machine-readable provenance record alongside its output file.
  2. Provenance records include at minimum: `request_id`, `seed`, `output_path`, `backend`, `review_status`, `generated_at`.
  3. Tests verify provenance file existence and required fields for the committed SFX fixture.
  4. Existing batch generation behavior (file output, `batch_manifest.json`) is preserved.
  5. Docs describe the provenance behavior truthfully without overstating format stability.
- **Enqueue next session after completion:** `SESSION-004 — Add batch QA gate command for generated outputs`
- **If uncertain or blocked:**
  - follow `docs/AI_FACTORY/BLOCKER_PROTOCOL.md`
  - do not invent new schema fields that conflict with `review_log.example.v1.json`
  - emit JSONL or individual JSON sidecar files — do not create a new binary format
  - record blockers in `HANDOFF.md`, `SESSION_QUEUE.md`, `SESSION_STATE.json`, and `CURRENT_SESSION.json`

## Upcoming queued sessions

### SESSION-004 — Add batch QA gate command for generated outputs

- **Status:** `queued-after-SESSION-003`
- **Task type:** `qa`
- **Short objective:** Validate generated music/SFX sets with pass/fail reporting and reusable automation.
